from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TERMINAL = {"ACT", "WAIT", "ABANDON"}
MATERIALITIES = {"FATAL", "BLOCKING", "MATERIAL", "NON_BLOCKING"}
MATERIALITY_RANK = {"NON_BLOCKING": 0, "MATERIAL": 1, "BLOCKING": 2, "FATAL": 3}
BASES = {"MISSING_EVIDENCE", "CONTRARY_EVIDENCE"}


@dataclass(frozen=True)
class MaterialityResult:
    materiality: str
    basis: str
    rule: str
    cap: str | None


def assign_materiality(
    *,
    requested: str,
    basis: str | None,
    claim_kind: str,
    evidence: str | None,
) -> MaterialityResult:
    """Deterministic materiality. The Adversary proposes; this rule disposes.

    A challenge that only says a claim is unproven (MISSING_EVIDENCE) cannot
    block or kill a decision by itself. It caps at MATERIAL, or at BLOCKING
    when the target claim is a DEPENDENCY, since an unmet precondition is a
    legitimate reason to wait. Only a challenge that states contrary evidence
    keeps the materiality it asked for. A challenge that claims contrary
    evidence but states none is treated as missing evidence.
    """
    requested = requested if requested in MATERIALITY_RANK else "MATERIAL"
    basis = basis if basis in BASES else "MISSING_EVIDENCE"
    if basis == "CONTRARY_EVIDENCE" and not (evidence or "").strip():
        basis = "MISSING_EVIDENCE"
    if basis == "CONTRARY_EVIDENCE":
        return MaterialityResult(requested, basis, "CONTRARY_EVIDENCE_AS_REQUESTED", None)
    cap = "BLOCKING" if claim_kind == "DEPENDENCY" else "MATERIAL"
    if MATERIALITY_RANK[requested] > MATERIALITY_RANK[cap]:
        return MaterialityResult(cap, basis, "MISSING_EVIDENCE_CAPPED", cap)
    return MaterialityResult(requested, basis, "MISSING_EVIDENCE_WITHIN_CAP", cap)


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


def evaluate_if_resolved(ledger: dict[str, Any], challenge_ids: list[str]) -> GateResult:
    """Re-run the gate as if the given challenges were resolved.

    Because the gate is a rule rather than a model, the ledger can state exactly
    what would change the action. This is the counterfactual behind that statement.
    """
    ids = set(challenge_ids)
    hypothetical = dict(ledger)
    hypothetical["challenges"] = [
        {**c, "status": "RESOLVED"} if c.get("id") in ids else c
        for c in ledger.get("challenges", [])
    ]
    return evaluate_gate(hypothetical)
