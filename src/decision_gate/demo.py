from __future__ import annotations

from typing import Any


class DemoBuilder:
    """Zero-key provider for trying the UX. It is intentionally labeled as demo output."""

    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        return {
            "claims": [
                {"title": "The problem is real", "statement": "The decision addresses a real and meaningful problem.", "kind": "ASSUMPTION", "depends_on": []},
                {"title": "The proposed action can change the outcome", "statement": "Taking the proposed action can materially improve the situation.", "kind": "ASSUMPTION", "depends_on": []},
                {"title": "The action is feasible", "statement": "The proposed action is feasible with the available time, resources, and constraints.", "kind": "ASSUMPTION", "depends_on": []},
                {"title": "Alternatives are not clearly superior", "statement": "No known alternative dominates the proposed action on the decision's important criteria.", "kind": "ASSUMPTION", "depends_on": []},
            ]
        }


class DemoAdversary:
    def __init__(self) -> None:
        self.calls = 0

    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        self.calls += 1
        if self.calls > 1:
            return {"challenges": []}
        return {
            "challenges": [
                {
                    "target_claim": "CL-004",
                    "title": "Alternatives have not been compared explicitly",
                    "argument": "The decision may be premature if realistic alternatives have not been compared against the same criteria.",
                    "materiality": "BLOCKING",
                    "resolves_if": "Compare at least the strongest alternative against the proposed action using explicit decision criteria.",
                },
                {
                    "target_claim": "CL-003",
                    "title": "Feasibility assumptions are not yet evidenced",
                    "argument": "Available resources and constraints have not been demonstrated in the current record.",
                    "materiality": "MATERIAL",
                    "resolves_if": "Record a concrete resource/time feasibility check or a small proof of feasibility.",
                },
            ]
        }
