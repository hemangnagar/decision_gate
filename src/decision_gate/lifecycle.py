from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .gate import evaluate_gate, evaluate_if_resolved

REOPEN_TRIGGERS = {"NEW_EVIDENCE", "DEPENDENCY_CHANGED", "OUTCOME_CONTRADICTION", "USER_EXPLICIT"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_commitment(ledger: dict[str, Any]) -> dict[str, Any]:
    """Run the gate on the ledger as it stands and return the commitment record."""
    gate = evaluate_gate(ledger)
    commitment: dict[str, Any] = {
        "action": gate.action,
        "matched_rule": gate.matched_rule,
        "triggering_challenges": gate.triggering_challenges,
        "reasons": gate.reasons,
        "accepted_risks": gate.accepted_risks,
        "committed_at": _now(),
        "gate": "deterministic-v1",
    }
    if gate.triggering_challenges:
        after = evaluate_if_resolved(ledger, gate.triggering_challenges)
        commitment["if_triggers_resolved"] = {
            "action": after.action,
            "matched_rule": after.matched_rule,
            "triggering_challenges": after.triggering_challenges,
            "accepted_risks": after.accepted_risks,
        }
    return commitment


def resolve_challenge(ledger: dict[str, Any], *, challenge_id: str, evidence: str) -> dict[str, Any]:
    """A human closes a challenge with evidence and the gate runs again.

    The evidence is appended to the ledger's evidence list, the challenge is
    marked RESOLVED by HUMAN, the previous commitment moves to
    commitment_history, and a fresh commitment is computed. Only a closed
    review with an unresolved target accepts this; check_reopen decides.
    """
    evidence = str(evidence or "").strip()
    if not evidence:
        raise ValueError("evidence is required to resolve a challenge")
    ok, reason = check_reopen(ledger, trigger="NEW_EVIDENCE", challenge_id=challenge_id)
    if not ok:
        raise ValueError(reason)
    challenge = next(c for c in ledger["challenges"] if c.get("id") == challenge_id)

    record = ledger.setdefault("evidence", [])
    entry = {
        "id": f"EV-{len(record) + 1:03d}",
        "challenge": challenge_id,
        "text": evidence,
        "submitted_by": "HUMAN",
        "submitted_at": _now(),
    }
    record.append(entry)
    challenge["status"] = "RESOLVED"
    challenge["resolution"] = {"by": "HUMAN", "evidence_id": entry["id"], "evidence": evidence, "at": entry["submitted_at"]}

    if "commitment" in ledger:
        ledger.setdefault("commitment_history", []).append(ledger["commitment"])
    ledger["commitment"] = build_commitment(ledger)
    return ledger


def check_reopen(
    ledger: dict[str, Any],
    *,
    trigger: str,
    challenge_id: str | None = None,
) -> tuple[bool, str]:
    trigger = trigger.upper()
    if trigger not in REOPEN_TRIGGERS:
        return False, f"Unknown reopen trigger: {trigger}"
    if "termination" not in ledger:
        return False, "Review is not closed."
    if trigger == "NEW_EVIDENCE":
        if not challenge_id:
            return False, "NEW_EVIDENCE must target a challenge."
        challenge = next((c for c in ledger.get("challenges", []) if c.get("id") == challenge_id), None)
        if not challenge:
            return False, f"Unknown challenge: {challenge_id}"
        if challenge.get("status") != "UNRESOLVED":
            return False, f"Challenge {challenge_id} is already resolved."
        return True, f"New evidence may reopen unresolved challenge {challenge_id} only."
    return True, f"Reopen permitted by declared trigger {trigger}."


def score_outcomes(ledger: dict[str, Any], outcomes: dict[str, Any]) -> dict[str, Any]:
    """Score a committed decision against human-recorded observable outcomes.

    outcomes.claims maps claim IDs to HELD / FAILED / UNKNOWN.
    outcomes.risks maps challenge IDs to REALIZED / NOT_REALIZED / UNKNOWN.
    """
    claim_results = outcomes.get("claims", {})
    risk_results = outcomes.get("risks", {})
    known_claims = {c.get("id") for c in ledger.get("claims", [])}
    known_challenges = {c.get("id") for c in ledger.get("challenges", [])}

    invalid_claims = sorted(set(claim_results) - known_claims)
    invalid_risks = sorted(set(risk_results) - known_challenges)
    if invalid_claims or invalid_risks:
        raise ValueError(f"Unknown outcome IDs: claims={invalid_claims}, risks={invalid_risks}")

    held = sum(v == "HELD" for v in claim_results.values())
    failed = sum(v == "FAILED" for v in claim_results.values())
    unknown = sum(v == "UNKNOWN" for v in claim_results.values())
    realized = sum(v == "REALIZED" for v in risk_results.values())
    not_realized = sum(v == "NOT_REALIZED" for v in risk_results.values())

    # Scored in both directions: an Adversary can be too lenient (a risk it
    # waved through came true) or too harsh (a challenge it used to block or
    # kill the decision never materialised). Only the first was counted before.
    underestimated = []
    overestimated = []
    for challenge in ledger.get("challenges", []):
        outcome = risk_results.get(challenge.get("id"))
        if outcome == "REALIZED" and challenge.get("materiality") in {"MATERIAL", "NON_BLOCKING"}:
            underestimated.append(challenge.get("id"))
        if outcome == "NOT_REALIZED" and challenge.get("materiality") in {"BLOCKING", "FATAL"}:
            overestimated.append(challenge.get("id"))

    return {
        "decision": ledger.get("decision"),
        "committed_action": ledger.get("commitment", {}).get("action"),
        "claims_scored": len(claim_results),
        "claims_held": held,
        "claims_failed": failed,
        "claims_unknown": unknown,
        "risks_realized": realized,
        "risks_not_realized": not_realized,
        "possibly_underestimated_challenges": underestimated,
        "possibly_overestimated_challenges": overestimated,
    }
