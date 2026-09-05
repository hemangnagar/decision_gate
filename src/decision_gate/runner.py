from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from .gate import evaluate_gate, evaluate_if_resolved, should_stop
from .prompts import ADVERSARY_PROMPT, ADVERSARY_SYSTEM, BUILDER_PROMPT, BUILDER_SYSTEM
from .providers import Provider
from .validate import VALID_MATERIALITY


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_claims(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for i, claim in enumerate(raw[:8], start=1):
        claims.append(
            {
                "id": f"CL-{i:03d}",
                "title": str(claim.get("title") or f"Claim {i}"),
                "statement": str(claim.get("statement") or claim.get("title") or ""),
                "kind": str(claim.get("kind") or "ASSUMPTION"),
                "depends_on": list(claim.get("depends_on") or []),
            }
        )
    ids = {c["id"] for c in claims}
    for claim in claims:
        claim["depends_on"] = [d for d in claim["depends_on"] if d in ids]
    return claims


def run_review(
    *,
    decision: str,
    context: str,
    builder: Provider,
    adversary: Provider,
    max_rounds: int = 3,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run a Builder/Adversary review and return the ledger.

    ``progress`` (optional) receives one short line per stage - builder claim
    count, each round's challenge tally, the stop reason and the gate action -
    so a live run is not silent for minutes. It never affects the ledger.
    """
    if not decision.strip():
        raise ValueError("decision is required")
    say = progress or (lambda _msg: None)

    say(f"builder ({getattr(builder, 'model', '?')}): drafting claims...")
    built = builder.generate_json(
        system=BUILDER_SYSTEM,
        prompt=BUILDER_PROMPT.format(decision=decision.strip(), context=context.strip() or "(none)"),
    )
    claims = _normalize_claims(list(built.get("claims") or []))
    if not claims:
        raise ValueError("builder returned no claims")
    say(f"builder: {len(claims)} claims")

    ledger: dict[str, Any] = {
        "id": f"DG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "decision": decision.strip(),
        "context": context.strip(),
        "created_at": _now(),
        "claims": claims,
        "challenges": [],
        "review_rounds": [],
        "review_policy": {"max_rounds": max_rounds, "stop_on_no_new_material": True},
    }

    challenge_counter = 0
    for round_no in range(1, max_rounds + 1):
        say(f"round {round_no}/{max_rounds} ({getattr(adversary, 'model', '?')}): adversary reviewing...")
        result = adversary.generate_json(
            system=ADVERSARY_SYSTEM,
            prompt=ADVERSARY_PROMPT.format(
                decision=ledger["decision"],
                claims_json=json.dumps(ledger["claims"], indent=2),
                challenges_json=json.dumps(ledger["challenges"], indent=2),
            ),
        )
        new_challenges: list[dict[str, Any]] = []
        seen = {(c.get("target_claim"), str(c.get("title", "")).lower()) for c in ledger["challenges"]}
        claim_ids = {c["id"] for c in ledger["claims"]}

        for raw in list(result.get("challenges") or []):
            target = raw.get("target_claim")
            title = str(raw.get("title") or "Untitled challenge").strip()
            materiality = str(raw.get("materiality") or "MATERIAL").upper()
            key = (target, title.lower())
            if target not in claim_ids or key in seen:
                continue
            if materiality not in VALID_MATERIALITY:
                materiality = "MATERIAL"
            challenge_counter += 1
            challenge = {
                "id": f"CH-{challenge_counter:03d}",
                "target_claim": target,
                "title": title,
                "argument": str(raw.get("argument") or ""),
                "materiality": materiality,
                "status": "UNRESOLVED",
                "resolves_if": str(raw.get("resolves_if") or "Provide evidence sufficient to resolve this challenge."),
                "raised_in_round": round_no,
            }
            new_challenges.append(challenge)
            seen.add(key)

        ledger["challenges"].extend(new_challenges)
        consequential = sum(c["materiality"] in {"FATAL", "BLOCKING", "MATERIAL"} for c in new_challenges)
        ledger["review_rounds"].append(
            {
                "round": round_no,
                "new_challenges": len(new_challenges),
                "new_material_or_blocking": consequential,
                "completed_at": _now(),
            }
        )
        tally = ", ".join(
            f"{n} {m}" for m in ("FATAL", "BLOCKING", "MATERIAL", "NON_BLOCKING")
            if (n := sum(c["materiality"] == m for c in new_challenges))
        ) or "nothing new"
        say(f"round {round_no}: {len(new_challenges)} new challenges ({tally})")
        stop, reason = should_stop(ledger["review_rounds"], max_rounds=max_rounds)
        if stop:
            ledger["termination"] = {"reason": reason, "round": round_no, "closed_at": _now()}
            say(f"stopping: {reason}")
            break

    if "termination" not in ledger:
        ledger["termination"] = {"reason": "Review policy completed.", "round": len(ledger["review_rounds"]), "closed_at": _now()}

    gate = evaluate_gate(ledger)
    ledger["commitment"] = {
        "action": gate.action,
        "matched_rule": gate.matched_rule,
        "triggering_challenges": gate.triggering_challenges,
        "reasons": gate.reasons,
        "accepted_risks": gate.accepted_risks,
        "committed_at": _now(),
        "gate": "deterministic-v1",
    }
    say(f"gate: {gate.action} ({gate.matched_rule})")
    if gate.triggering_challenges:
        after = evaluate_if_resolved(ledger, gate.triggering_challenges)
        ledger["commitment"]["if_triggers_resolved"] = {
            "action": after.action,
            "matched_rule": after.matched_rule,
            "triggering_challenges": after.triggering_challenges,
            "accepted_risks": after.accepted_risks,
        }
    return ledger
