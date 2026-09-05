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
    # None = the provider's default. Newer models (e.g. Claude Opus 5) reject
    # sampling parameters outright, so nothing is sent unless explicitly set.
    temperature: float | None = None

    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        try:
            import litellm
            from litellm import completion
        except ImportError as exc:
            raise RuntimeError(
                "LiteLLM is not installed. Install with: pip install 'decision-gate[llm]'"
            ) from exc

        # Provider-neutral means tolerating provider differences: drop any
        # parameter a given model does not support instead of failing the run.
        litellm.drop_params = True

        kwargs: dict[str, Any] = {}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )
        content = response.choices[0].message.content or ""
        return parse_json_object(content)
