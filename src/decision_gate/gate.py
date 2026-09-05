from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TERMINAL = {"ACT", "WAIT", "ABANDON"}
MATERIALITIES = {"FATAL", "BLOCKING", "MATERIAL", "NON_BLOCKING"}


@dataclass(frozen=True)
class GateResult:
    action: str
    matched_rule: str
    triggering_challenges: list[str]
    reasons: list[str]
    accepted_risks: list[str]


def evaluate_gate(ledger: dict[str, Any]) -> GateResult:
    challenges = ledger.get("challenges", [])
    unresolved = [c for c in challenges if c.get("status") == "UNRESOLVED"]

    fatal = [c for c in unresolved if c.get("materiality") == "FATAL"]
    if fatal:
        return GateResult(
            action="ABANDON",
            matched_rule="UNRESOLVED_FATAL",
            triggering_challenges=[str(c.get("id")) for c in fatal],
            reasons=[f"Fatal unresolved challenge: {c['title']}" for c in fatal],
            accepted_risks=[],
        )

    blocking = [c for c in unresolved if c.get("materiality") == "BLOCKING"]
    if blocking:
        return GateResult(
            action="WAIT",
            matched_rule="UNRESOLVED_BLOCKING",
            triggering_challenges=[str(c.get("id")) for c in blocking],
            reasons=[f"Blocking unresolved challenge: {c['title']}" for c in blocking],
            accepted_risks=[],
        )

    accepted = [
        c["title"] for c in unresolved
        if c.get("materiality") in {"MATERIAL", "NON_BLOCKING"}
    ]
    return GateResult(
        action="ACT",
        matched_rule="NO_UNRESOLVED_FATAL_OR_BLOCKING",
        triggering_challenges=[],
        reasons=["No fatal or blocking unresolved challenges remain."],
        accepted_risks=accepted,
    )


def should_stop(review_rounds: list[dict[str, Any]], max_rounds: int = 3) -> tuple[bool, str]:
    if review_rounds:
        latest = review_rounds[-1]
        if latest.get("new_material_or_blocking", 0) == 0:
            return True, "Latest round produced no new MATERIAL, BLOCKING, or FATAL challenge."
    if len(review_rounds) >= max_rounds:
        return True, f"Maximum review rounds reached ({max_rounds})."
    return False, "More adversarial review is permitted by policy."
