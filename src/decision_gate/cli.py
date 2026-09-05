from __future__ import annotations

import argparse
import json
from pathlib import Path

from .gate import evaluate_gate, should_stop
from .providers import LiteLLMProvider
from .runner import run_review
from .validate import validate_ledger


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> None:
    p = argparse.ArgumentParser(prog="decision-gate")
    s = p.add_subparsers(dest="cmd", required=True)
    v = s.add_parser("validate"); v.add_argument("ledger")
    g = s.add_parser("gate"); g.add_argument("ledger")
    st = s.add_parser("stop"); st.add_argument("ledger"); st.add_argument("--max-rounds", type=int, default=3)
    r = s.add_parser("review")
    r.add_argument("decision")
    r.add_argument("--context", default="")
    r.add_argument("--builder-model", required=True)
    r.add_argument("--adversary-model", required=True)
    r.add_argument("--max-rounds", type=int, default=3)
    r.add_argument("--out")
    args = p.parse_args()

    if args.cmd == "review":
        ledger = run_review(
            decision=args.decision,
            context=args.context,
            builder=LiteLLMProvider(args.builder_model),
            adversary=LiteLLMProvider(args.adversary_model),
            max_rounds=args.max_rounds,
        )
        text = json.dumps(ledger, indent=2)
        if args.out:
            Path(args.out).write_text(text)
            print(args.out)
        else:
            print(text)
        return

    ledger = load(args.ledger)
    if args.cmd == "validate":
        errors = validate_ledger(ledger)
        print("VALID" if not errors else "INVALID")
        for e in errors:
            print(f"- {e}")
    elif args.cmd == "gate":
        result = evaluate_gate(ledger)
        print(result.action)
        for reason in result.reasons:
            print(f"- {reason}")
        if result.accepted_risks:
            print("Accepted risks:")
            for risk in result.accepted_risks:
                print(f"- {risk}")
    elif args.cmd == "stop":
        stop, reason = should_stop(ledger.get("review_rounds", []), args.max_rounds)
        print("STOP" if stop else "CONTINUE")
        print(reason)


if __name__ == "__main__":
    main()
