"""Summaries for comparing ledgers: what the Adversary asked for, what stood.

Used by ``decision-gate compare``. A ledger written before the materiality
rule carries no ``requested_materiality``; for those the Adversary's own
rating is both what was asked and what stood, and the summary says so.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ORDER = ("FATAL", "BLOCKING", "MATERIAL", "NON_BLOCKING")


def summarize_ledger(ledger: dict[str, Any], name: str = "") -> dict[str, Any]:
    challenges = ledger.get("challenges", [])
    asked = {m: 0 for m in ORDER}
    standing = {m: 0 for m in ORDER}
    for c in challenges:
        requested = c.get("requested_materiality", c.get("materiality"))
        if requested in asked:
            asked[requested] += 1
        if c.get("status") == "UNRESOLVED" and c.get("materiality") in standing:
            standing[c["materiality"]] += 1
    commitment = ledger.get("commitment") or {}
    by = lambda who: sum(
        c.get("status") == "RESOLVED" and (c.get("resolution") or {}).get("by") == who for c in challenges
    )
    return {
        "name": name or str(ledger.get("id", "")),
        "decision": ledger.get("decision", ""),
        "context_supplied": bool(str(ledger.get("context") or "").strip()),
        "predates_rule": bool(challenges) and not any("requested_materiality" in c for c in challenges),
        "rounds": len(ledger.get("review_rounds", [])),
        "challenges": len(challenges),
        "asked": asked,
        "standing": standing,
        "capped": sum(c.get("materiality_rule") == "MISSING_EVIDENCE_CAPPED" for c in challenges),
        "contrary_evidence": sum(c.get("basis") == "CONTRARY_EVIDENCE" for c in challenges),
        "resolved_by_builder": by("BUILDER"),
        "resolved_by_human": by("HUMAN"),
        "withdrawn": sum(c.get("status") == "WITHDRAWN" for c in challenges),
        "disputed": sum((c.get("rebuttal") or {}).get("response") == "DISPUTED" for c in challenges),
        "conceded": sum((c.get("rebuttal") or {}).get("response") == "CONCEDED" for c in challenges),
        "action": commitment.get("action"),
        "matched_rule": commitment.get("matched_rule"),
        "triggers": len(commitment.get("triggering_challenges") or []),
        "if_triggers_resolved": (commitment.get("if_triggers_resolved") or {}).get("action"),
        "accepted_risks": len(commitment.get("accepted_risks") or []),
    }


def _counts(d: dict[str, int]) -> str:
    return "/".join(str(d[m]) for m in ORDER)


def format_comparison(summaries: list[dict[str, Any]]) -> str:
    """One row per ledger. Counts are FATAL/BLOCKING/MATERIAL/NON_BLOCKING."""
    headers = ("ledger", "ctx", "chal", "asked F/B/M/N", "open F/B/M/N", "capped", "resolved", "withdrawn", "gate", "if resolved")
    rows = []
    for s in summaries:
        rows.append((
            s["name"] + ("*" if s["predates_rule"] else ""),
            "yes" if s["context_supplied"] else "no",
            str(s["challenges"]),
            _counts(s["asked"]),
            _counts(s["standing"]),
            str(s["capped"]),
            f"{s['resolved_by_builder']}b {s['resolved_by_human']}h",
            str(s["withdrawn"]),
            f"{s['action']} ({s['triggers']})" if s["action"] else "-",
            s["if_triggers_resolved"] or "-",
        ))
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    line = lambda cells: "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()
    out = [line(headers), line(tuple("-" * w for w in widths))]
    out.extend(line(r) for r in rows)
    out.append("")
    for s in summaries:
        out.append(f"{s['name']}: {s['decision']}")
    if any(s["predates_rule"] for s in summaries):
        out.append("")
        out.append("* predates the materiality rule: the Adversary's own ratings are both what was asked and what stood.")
    out.append("gate: action (number of triggering challenges). resolved: by the Builder (b) and by a human (h).")
    return "\n".join(out)


def summarize_file(path: str) -> dict[str, Any]:
    import json

    p = Path(path)
    return summarize_ledger(json.loads(p.read_text()), name=p.name)
