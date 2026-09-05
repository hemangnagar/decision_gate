"""Zero-key demo providers.

The demo replays ONE fixed worked example so the mechanism is visible end to end:
the Builder states what the decision rests on, the Adversary attacks it once and
finds nothing new the second time, the review stops, and the deterministic gate
returns WAIT because exactly one unresolved challenge is BLOCKING.

The canned output only makes sense for DEMO_DECISION, so demo mode always runs
that decision and tags the ledger `mode: "demo"`. It never calls a model.
"""

from __future__ import annotations

from typing import Any

DEMO_DECISION = "Should we build a cardiology-focused procedure operations agent?"
DEMO_CONTEXT = (
    "Small team, six months of runway for a pilot. One community-hospital cardiology "
    "department has expressed interest but has not committed."
)


class DemoBuilder:
    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        return {
            "claims": [
                {
                    "title": "Coordination work is a real bottleneck",
                    "statement": "Cardiology procedure teams lose meaningful staff hours each week to scheduling, pre-procedure checklists, and handoffs.",
                    "kind": "ASSUMPTION",
                    "depends_on": [],
                },
                {
                    "title": "That work needs no clinical judgment",
                    "statement": "Those coordination tasks can be handled by an agent that never makes a clinical decision.",
                    "kind": "ASSUMPTION",
                    "depends_on": ["CL-001"],
                },
                {
                    "title": "We can get the data",
                    "statement": "A pilot site will grant integration access to its scheduling and EHR systems.",
                    "kind": "DEPENDENCY",
                    "depends_on": [],
                },
                {
                    "title": "A pilot site will commit",
                    "statement": "At least one cardiology department will run a paid pilot within the six-month runway.",
                    "kind": "ASSUMPTION",
                    "depends_on": ["CL-003"],
                },
                {
                    "title": "Nothing off the shelf already does this",
                    "statement": "Existing scheduling and EHR-vendor tools do not already cover this workflow well enough to make a new agent redundant.",
                    "kind": "ASSUMPTION",
                    "depends_on": [],
                },
            ]
        }


class DemoAdversary:
    def __init__(self) -> None:
        self.calls = 0

    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        self.calls += 1
        if self.calls > 1:
            # Round 2: nothing new. This is what stops the review.
            return {"challenges": []}
        return {
            "challenges": [
                {
                    "target_claim": "CL-003",
                    "title": "Integration access is not confirmed",
                    "argument": "The interested department has not committed, and no IT or integration team has agreed to grant scheduling or EHR access. Without that access the agent cannot run anywhere, so this is a precondition, not a risk to carry.",
                    "materiality": "BLOCKING",
                    "resolves_if": "Written sandbox or integration access from at least one pilot site's IT team.",
                },
                {
                    "target_claim": "CL-001",
                    "title": "The bottleneck is asserted, not measured",
                    "argument": "Nobody has measured the hours lost to coordination. If the number is small, the agent solves a minor problem. Building can start while this is measured.",
                    "materiality": "MATERIAL",
                    "resolves_if": "A two-week time study in one department showing hours per week spent on coordination tasks.",
                },
                {
                    "target_claim": "CL-005",
                    "title": "EHR vendor roadmaps are unknown",
                    "argument": "A major EHR vendor could ship similar workflow features. That affects long-term differentiation, not whether to run a pilot.",
                    "materiality": "NON_BLOCKING",
                    "resolves_if": "Review of the two dominant EHR vendors' published workflow roadmaps.",
                },
            ]
        }
