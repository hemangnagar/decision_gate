from __future__ import annotations

from typing import Any

REOPEN_TRIGGERS = {"NEW_EVIDENCE", "DEPENDENCY_CHANGED", "OUTCOME_CONTRADICTION", "USER_EXPLICIT"}


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

    underestimated = []
    for challenge in ledger.get("challenges", []):
        if risk_results.get(challenge.get("id")) == "REALIZED" and challenge.get("materiality") in {"MATERIAL", "NON_BLOCKING"}:
            underestimated.append(challenge.get("id"))

    return {
        "decision": ledger.get("decision"),
        "committed_action": ledger.get("commitment", {}).get("action"),
        "claims_scored": len(claim_results),
        "claims_held": held,
        "claims_failed": failed,
        "claims_unknown": unknown,
        "risks_realized": realized,
        "possibly_underestimated_challenges": underestimated,
    }
