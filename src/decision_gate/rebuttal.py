from __future__ import annotations

import re
from typing import Any

RESPONSES = {"RESOLVED", "DISPUTED", "CONCEDED"}
MIN_QUOTE_CHARS = 12


def _normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return text.strip("\"'“”‘’.,;:!?()[] ")


def evidence_on_record(quote: str, context: str) -> bool:
    """True if ``quote`` appears verbatim in ``context`` (case and whitespace insensitive).

    This is the whole check that stands between a model and "resolved". It is
    deliberately dumb: a resolution must point at words the human put on the
    record, not at words the model wishes were there.
    """
    q = _normalize(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in _normalize(context)


def apply_rebuttals(ledger: dict[str, Any], responses: list[dict[str, Any]], round_no: int) -> dict[str, int]:
    """Apply the Builder's answers to open challenges. Returns counts by outcome.

    RESOLVED needs a verified quote from the context and flips the challenge
    to status RESOLVED. A RESOLVED response whose quote is not on the record
    is recorded as DISPUTED with the rejection noted. DISPUTED and CONCEDED
    change nothing the gate reads; they are the Builder's position on the
    record, and a DISPUTED challenge is the only kind the Adversary may
    withdraw next round. Open challenges the Builder did not answer are
    marked UNANSWERED so each challenge gets exactly one Builder turn.
    """
    counts = {"resolved": 0, "disputed": 0, "conceded": 0, "unverified": 0, "unanswered": 0}
    by_id = {c.get("id"): c for c in ledger.get("challenges", [])}
    context = ledger.get("context", "")

    for raw in responses:
        challenge = by_id.get(raw.get("challenge"))
        if not challenge or challenge.get("status") != "UNRESOLVED" or "rebuttal" in challenge:
            continue
        response = str(raw.get("response") or "").upper()
        argument = str(raw.get("argument") or "").strip()
        quote = str(raw.get("evidence") or "").strip()
        if response not in RESPONSES:
            continue
        if response == "RESOLVED":
            if evidence_on_record(quote, context):
                challenge["rebuttal"] = {"response": "RESOLVED", "evidence": quote, "argument": argument, "round": round_no}
                challenge["status"] = "RESOLVED"
                challenge["resolution"] = {"by": "BUILDER", "evidence": quote, "round": round_no}
                counts["resolved"] += 1
            else:
                challenge["rebuttal"] = {
                    "response": "DISPUTED",
                    "argument": argument,
                    "round": round_no,
                    "rejected_evidence": quote,
                    "note": "Builder claimed RESOLVED but the quoted evidence is not in the context; treated as DISPUTED.",
                }
                counts["unverified"] += 1
                counts["disputed"] += 1
        else:
            challenge["rebuttal"] = {"response": response, "argument": argument, "round": round_no}
            counts[response.lower()] += 1

    for challenge in ledger.get("challenges", []):
        if challenge.get("status") == "UNRESOLVED" and "rebuttal" not in challenge:
            challenge["rebuttal"] = {"response": "UNANSWERED", "round": round_no}
            counts["unanswered"] += 1
    return counts


def apply_withdrawals(ledger: dict[str, Any], withdrawals: list[dict[str, Any]], round_no: int) -> int:
    """Let the Adversary retract a challenge the Builder disputed. Returns the count."""
    by_id = {c.get("id"): c for c in ledger.get("challenges", [])}
    withdrawn = 0
    for raw in withdrawals:
        challenge = by_id.get(raw.get("challenge"))
        if not challenge or challenge.get("status") != "UNRESOLVED":
            continue
        if (challenge.get("rebuttal") or {}).get("response") != "DISPUTED":
            continue
        challenge["status"] = "WITHDRAWN"
        challenge["withdrawal"] = {"reason": str(raw.get("reason") or "").strip(), "round": round_no}
        withdrawn += 1
    return withdrawn
