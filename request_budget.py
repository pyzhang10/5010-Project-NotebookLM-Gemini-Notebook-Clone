"""Conservative UTF-8 byte budgeting; no downloaded tokenizer required.

For GPT-OSS's byte-based tokenizer, byte count is a conservative text-token
bound. Reserve additional space for chat framing and the completion.
"""
import os
from collections import deque


def limits():
    total = int(os.getenv('GROQ_REQUEST_TOKEN_BUDGET', '7500'))
    output = int(os.getenv('GROQ_MAX_COMPLETION_TOKENS', '2000'))
    prompt = total - output - 500
    if output < 256 or prompt < 1024:
        raise ValueError('Groq budget must leave at least 1024 input bytes, 256 output tokens and 500 framing tokens.')
    return prompt, output


def size(text):
    return len(text.encode('utf-8'))


def fit_context(prefix, sections):
    """Return prompt, selected indices and whether any source was shortened."""
    budget, _ = limits()
    remaining = budget - size(prefix)
    if remaining < 256:
        raise ValueError('The question/instructions are too long. Please shorten them and try again.')
    selected = []
    parts = []
    shortened = False
    for i, (label, body) in enumerate(sections):
        header = label + '\n'
        available = remaining - size(header) - 2
        if available < 128:
            shortened = True
            continue
        text = body
        if size(text) > available:
            marker = '\n[Excerpt shortened]'
            text = text.encode('utf-8')[:available-size(marker)].decode('utf-8', errors='ignore') + marker
            shortened = True
        part = header + text + '\n\n'
        parts.append(part)
        selected.append(i)
        remaining -= size(part)
    if not selected:
        raise ValueError('No source excerpt fits the request budget. Shorten the question or source names.')
    return prefix + ''.join(parts), selected, shortened or len(selected) < len(sections)


def interleave_sources(items):
    """Give each source a turn before selecting another chunk of that source."""
    groups = {}
    for item in items:
        key = item.metadata.get('source_id', item.metadata['source_name'])
        groups.setdefault(key, deque()).append(item)
    result = []
    while groups:
        for key in list(groups):
            result.append(groups[key].popleft())
            if not groups[key]:
                del groups[key]
    return result
