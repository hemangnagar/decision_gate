from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TERMINAL = {"ACT", "WAIT", "ABANDON"}
MATERIALITIES = {"FATAL", "BLOCKING", "MATERIAL", "NON_BLOCKING"}

@dataclass(frozen=True)
class GateResult:
    action: str
    reasons: list[str]
    accepted_risks: list[str]


def evaluate_gate(ledger: dict[str, Any]) -> GateResult:
    challenges = ledger.get("challenges", [])
    unresolved = [c for c in challenges if c.get("status") == "UNRESOLVED"]

    fatal = [c for c in unresolved if c.get("materiality") == "FATAL"]
    if fatal:
        return GateResult(
            "ABANDON",
            [f"Fatal unresolved challenge: {c['title']}" for c in fatal],
            [],
        )

    blocking = [c for c in unresolved if c.get("materiality") == "BLOCKING"]
    if blocking:
        return GateResult(
            "WAIT",
            [f"Blocking unresolved challenge: {c['title']}" for c in blocking],
            [],
        )

    accepted = [
        c["title"] for c in unresolved
        if c.get("materiality") in {"MATERIAL", "NON_BLOCKING"}
    ]
    return GateResult(
        "ACT",
        ["No fatal or blocking unresolved challenges remain."],
        accepted,
    )


def should_stop(review_rounds: list[dict[str, Any]], max_rounds: int = 3) -> tuple[bool, str]:
    if len(review_rounds) >= max_rounds:
        return True, f"Maximum review rounds reached ({max_rounds})."
    if review_rounds:
        latest = review_rounds[-1]
        if latest.get("new_material_or_blocking", 0) == 0:
            return True, "Latest round produced no new MATERIAL, BLOCKING, or FATAL challenge."
    return False, "More adversarial review is permitted by policy."
