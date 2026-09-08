import json
import unittest
from pathlib import Path

from decision_gate.demo import DEMO_CONTEXT, DEMO_DECISION, DemoAdversary, DemoBuilder
from decision_gate.report import format_comparison, summarize_ledger
from decision_gate.runner import run_review

ROOT = Path(__file__).resolve().parents[1]


class SummarizeTests(unittest.TestCase):
    def test_demo_summary_shows_the_defence_working(self):
        ledger = run_review(decision=DEMO_DECISION, context=DEMO_CONTEXT, builder=DemoBuilder(), adversary=DemoAdversary())
        s = summarize_ledger(ledger, name="demo")
        self.assertFalse(s["predates_rule"])
        self.assertTrue(s["context_supplied"])
        self.assertEqual(s["asked"], {"FATAL": 0, "BLOCKING": 2, "MATERIAL": 1, "NON_BLOCKING": 0})
        self.assertEqual(s["standing"], {"FATAL": 0, "BLOCKING": 0, "MATERIAL": 2, "NON_BLOCKING": 0})
        self.assertEqual((s["capped"], s["resolved_by_builder"], s["conceded"], s["disputed"]), (1, 1, 1, 1))
        self.assertEqual((s["action"], s["accepted_risks"]), ("ACT", 2))

    def test_legacy_ledger_is_flagged_and_counts_its_own_ratings(self):
        ledger = json.loads((ROOT / "data/decisions/004-spark-to-duckdb.json").read_text())
        s = summarize_ledger(ledger, name="004")
        self.assertTrue(s["predates_rule"])
        self.assertFalse(s["context_supplied"])
        self.assertEqual(s["asked"], s["standing"])
        self.assertEqual(s["asked"]["BLOCKING"], 9)
        self.assertEqual((s["action"], s["triggers"], s["if_triggers_resolved"]), ("WAIT", 9, "ACT"))

    def test_table_has_one_row_per_ledger_and_marks_legacy(self):
        new = summarize_ledger(run_review(decision=DEMO_DECISION, context=DEMO_CONTEXT, builder=DemoBuilder(), adversary=DemoAdversary()), name="new.json")
        old = summarize_ledger(json.loads((ROOT / "data/decisions/004-spark-to-duckdb.json").read_text()), name="old.json")
        text = format_comparison([old, new])
        lines = text.splitlines()
        self.assertTrue(lines[2].startswith("old.json*"))
        self.assertTrue(lines[3].startswith("new.json "))
        self.assertIn("0/9/13/0", lines[2])
        self.assertIn("0/2/1/0", lines[3])   # asked
        self.assertIn("0/0/2/0", lines[3])   # standing
        self.assertIn("predates the materiality rule", text)


if __name__ == "__main__":
    unittest.main()
