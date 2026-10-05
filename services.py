from __future__ import annotations

import time

from config import TOP_K
from llm import GroqClient
from request_budget import fit_context
from retrieval import SearchResult, VectorIndex
from storage import LocalStorage


def citation(item: SearchResult, label: str) -> str:
    meta = item.metadata
    link = f" — {meta['url']}" if meta.get("url") else ""
    return (
        f"[{label}] {meta['source_name']}, {meta['location']}, "
        f"Chunk `{item.chunk_id}`{link}"
    )


class RAGService:
    def __init__(self, storage: LocalStorage, index: VectorIndex, llm: GroqClient):
        self.storage = storage
        self.index = index
        self.llm = llm

    def answer(self, notebook_id: str, question: str, method: str):
        clean = question.strip()
        if not clean:
            raise ValueError("Enter a question.")
        started = time.perf_counter()
        results, retrieval_time = self.index.search(notebook_id, clean, method, TOP_K)
        if not results:
            raise ValueError("This notebook has no indexed source content.")
        context_parts = []
        citations = []
        for index, item in enumerate(results, start=1):
            label = f"S{index}"
            context_parts.append((f"[{label}]", item.text))
            citations.append(citation(item, label))
        prompt = f"""You are a source-grounded research assistant.
Answer ONLY from the context below. If it is insufficient, say exactly that the
notebook sources do not provide enough information. Do not use outside facts.
Cite every substantive claim with one or more source labels such as [S1].

QUESTION:
{clean}

CONTEXT:
"""
        prompt, selected, limited = fit_context(prompt, context_parts)
        answer = self.llm.generate(prompt)
        total_time = time.perf_counter() - started
        history = self.storage.history(notebook_id)
        history.extend([
            {"role": "user", "content": clean},
            {"role": "assistant", "content": answer},
        ])
        self.storage.save_history(notebook_id, history)
        details = "\n\n".join(
            f"### {citation(item, f'S{i}')}\n\n"
            f"Score: `{item.score:.4f}`\n\n> {item.text[:900]}"
            for i, item in enumerate(results, start=1) if i - 1 in selected
        )
        timing = (
            f"Retrieval: {retrieval_time:.3f}s · Total: {total_time:.3f}s · "
            f"Method: {method} · Context chunks: {len(selected)}/{len(results)}"
        )
        if limited:
            timing += " · Context limited to fit API budget; excerpts may be shortened"
        return history, details, timing
