from __future__ import annotations
from typing import Any

VALID_ACTIONS = {"ACT", "WAIT", "ABANDON"}
VALID_MATERIALITY = {"FATAL", "BLOCKING", "MATERIAL", "NON_BLOCKING"}
VALID_STATUS = {"SUPPORTED", "REFUTED", "REVISED", "CONTESTED", "INSUFFICIENT_EVIDENCE", "UNRESOLVED", "RESOLVED"}


def validate_ledger(ledger: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("id", "decision", "created_at", "claims", "challenges", "review_rounds"):
        if key not in ledger:
            errors.append(f"Missing required field: {key}")

    claim_ids = {c.get("id") for c in ledger.get("claims", [])}
    for claim in ledger.get("claims", []):
        for dep in claim.get("depends_on", []):
            if dep not in claim_ids:
                errors.append(f"Claim {claim.get('id')} depends on unknown claim {dep}")

    for challenge in ledger.get("challenges", []):
        if challenge.get("target_claim") not in claim_ids:
            errors.append(f"Challenge {challenge.get('id')} targets unknown claim")
        if challenge.get("materiality") not in VALID_MATERIALITY:
            errors.append(f"Challenge {challenge.get('id')} has invalid materiality")
        if challenge.get("status") not in VALID_STATUS:
            errors.append(f"Challenge {challenge.get('id')} has invalid status")
        if challenge.get("status") == "UNRESOLVED" and not challenge.get("resolves_if"):
            errors.append(f"Unresolved challenge {challenge.get('id')} must include resolves_if")

    action = ledger.get("commitment", {}).get("action")
    if action is not None and action not in VALID_ACTIONS:
        errors.append(f"Invalid committed action: {action}")
    return errors
