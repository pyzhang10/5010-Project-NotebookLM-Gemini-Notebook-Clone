from __future__ import annotations

import os

from openai import OpenAI, APIStatusError
from request_budget import limits, size


class GroqClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Add it to .env locally or "
                "Hugging Face Space Secrets."
            )
        prompt_budget, completion_budget = limits()
        if size(prompt) > prompt_budget:
            raise ValueError("Request exceeds the safe input budget. Reduce source context or question length.")
        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=120.0,
        )
        options = {}
        if self.model.startswith("openai/gpt-oss-"):
            options["reasoning_effort"] = "low"
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_completion_tokens=completion_budget,
                **options,
            )
        except APIStatusError as exc:
            if exc.status_code == 413:
                raise RuntimeError("Groq rejected the request size. Lower GROQ_REQUEST_TOKEN_BUDGET in .env and restart.") from exc
            if exc.status_code == 429:
                raise RuntimeError("Groq rate limit reached. Wait for the quota to reset before trying again; avoid simultaneous requests.") from exc
            raise
        if response.choices[0].finish_reason == "length":
            raise RuntimeError("The response reached its output limit and was not saved. Ask for a shorter answer or a narrower report/quiz.")
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty response.")
        return content.strip()
