from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol


class Provider(Protocol):
    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]: ...


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a model response that may contain a fenced JSON object."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Model output must be a JSON object")
    return value


@dataclass
class LiteLLMProvider:
    """Thin adapter over LiteLLM so Decision Gate stays provider-neutral."""

    model: str
    temperature: float = 0.1

    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        try:
            from litellm import completion
        except ImportError as exc:
            raise RuntimeError(
                "LiteLLM is not installed. Install with: pip install 'decision-gate[llm]'"
            ) from exc

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content or ""
        return parse_json_object(content)
