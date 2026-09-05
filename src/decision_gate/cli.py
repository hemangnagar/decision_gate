from __future__ import annotations
import argparse, json
from pathlib import Path
from .gate import evaluate_gate, should_stop
from .validate import validate_ledger


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> None:
    p = argparse.ArgumentParser(prog="decision-gate")
    s = p.add_subparsers(dest="cmd", required=True)
    v = s.add_parser("validate"); v.add_argument("ledger")
    g = s.add_parser("gate"); g.add_argument("ledger")
    st = s.add_parser("stop"); st.add_argument("ledger"); st.add_argument("--max-rounds", type=int, default=3)
    args = p.parse_args()
    ledger = load(args.ledger)
    if args.cmd == "validate":
        errors = validate_ledger(ledger)
        print("VALID" if not errors else "INVALID")
        for e in errors: print(f"- {e}")
    elif args.cmd == "gate":
        r = evaluate_gate(ledger)
        print(r.action)
        for reason in r.reasons: print(f"- {reason}")
        if r.accepted_risks:
            print("Accepted risks:")
            for risk in r.accepted_risks: print(f"- {risk}")
    elif args.cmd == "stop":
        stop, reason = should_stop(ledger.get("review_rounds", []), args.max_rounds)
        print("STOP" if stop else "CONTINUE")
        print(reason)

if __name__ == "__main__": main()
