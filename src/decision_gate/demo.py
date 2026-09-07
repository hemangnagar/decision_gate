"""Zero-key demo providers.

The demo replays ONE fixed worked example so every mechanism is visible once:

* the Builder states what the decision rests on;
* the Adversary raises three challenges: one that only says a claim is
  unmeasured (capped to MATERIAL by rule), one that misses evidence already
  in the context (the Builder resolves it by quoting the record), and one
  that brings contrary evidence from the context (kept at the rating asked);
* the Builder answers each: dispute, resolve with a verified quote, concede;
* the second round adds nothing, so the review stops;
* the gate returns ACT, carrying the two open challenges as accepted risks.

The canned Adversary is deliberately imperfect: it raises one challenge the
context already answers, which is what real models do often enough that the
rebuttal turn exists. The canned output only makes sense for DEMO_DECISION,
so demo mode always runs that decision and tags the ledger `mode: "demo"`.
It never calls a model.
"""

from __future__ import annotations

from typing import Any

from .prompts import REBUTTAL_SYSTEM

DEMO_DECISION = "Should we build a cardiology-focused procedure operations agent?"
DEMO_CONTEXT = (
    "Small team, six months of runway for a pilot. One community-hospital cardiology "
    "department has expressed interest but has not committed. Its IT director granted "
    "sandbox access to the scheduling system on 2 September. A large EHR vendor announced "
    "a procedure-coordination module last quarter."
)


class DemoBuilder:
    def generate_json(self, *, system: str, prompt: str) -> dict[str, Any]:
        if system == REBUTTAL_SYSTEM:
            return {
                "responses": [
                    {
                        "challenge": "CH-001",
                        "response": "DISPUTED",
                        "evidence": "",
                        "argument": "A two-week time study is cheap and can run alongside the pilot. The measurement gap is a risk to carry, not a reason to wait.",
                    },
                    {
                        "challenge": "CH-002",
                        "response": "RESOLVED",
                        "evidence": "granted sandbox access to the scheduling system on 2 September",
                        "argument": "Access is already on the record.",
                    },
                    {
                        "challenge": "CH-003",
                        "response": "CONCEDED",
                        "evidence": "",
                        "argument": "The announcement is real. Differentiation will have to come from cardiology-specific workflow, and that is a risk we carry.",
                    },
                ]
            }
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
                    "statement": "A pilot site will give us sandbox access to its scheduling system.",
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
            # Round 2: the dispute on CH-001 is about acceptable risk, not about
            # whether the challenge is right, so it stands. Nothing new. Stop.
            return {"withdraw": [], "challenges": []}
        return {
            "challenges": [
                {
                    "target_claim": "CL-001",
                    "title": "The bottleneck is asserted, not measured",
                    "argument": "Nobody has measured the hours lost to coordination. If the number is small, the agent solves a minor problem.",
                    "basis": "MISSING_EVIDENCE",
                    "evidence": "",
                    "materiality": "BLOCKING",
                    "resolves_if": "A two-week time study in one department showing hours per week spent on coordination tasks.",
                },
                {
                    "target_claim": "CL-003",
                    "title": "No site has granted scheduling access",
                    "argument": "An expression of interest is not access. Until a site grants it, the agent cannot run anywhere.",
                    "basis": "MISSING_EVIDENCE",
                    "evidence": "",
                    "materiality": "BLOCKING",
                    "resolves_if": "Sandbox or integration access granted by a pilot site's IT team.",
                },
                {
                    "target_claim": "CL-005",
                    "title": "A major EHR vendor is building the same thing",
                    "argument": "If the dominant EHR ships procedure coordination inside the system clinicians already use, a standalone agent has to be much better to be adopted at all.",
                    "basis": "CONTRARY_EVIDENCE",
                    "evidence": "A large EHR vendor announced a procedure-coordination module last quarter.",
                    "materiality": "MATERIAL",
                    "resolves_if": "The vendor's shipped module reviewed against the cardiology workflow; a written list of what it does not cover.",
                },
            ]
        }
