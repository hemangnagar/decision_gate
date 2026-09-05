import unittest

from decision_gate.runner import run_review


class _Builder:
    model = "fake/builder"

    def generate_json(self, *, system, prompt):
        return {"claims": [
            {"title": "Demand exists", "statement": "There is demand.", "kind": "ASSUMPTION"},
            {"title": "Cost is known", "statement": "Cost is $1.", "kind": "FACT"},
        ]}


class _Adversary:
    model = "fake/adversary"

    def __init__(self):
        self.calls = 0

    def generate_json(self, *, system, prompt):
        self.calls += 1
        if self.calls == 1:
            return {"challenges": [
                {"target_claim": "CL-001", "title": "No survey", "argument": "x", "materiality": "BLOCKING"},
                {"target_claim": "CL-002", "title": "Typo", "argument": "y", "materiality": "NON_BLOCKING"},
            ]}
        return {"challenges": []}


class ProgressTests(unittest.TestCase):
    def test_progress_lines_are_emitted_in_order_and_do_not_touch_ledger(self):
        lines = []
        with_progress = run_review(
            decision="Open a store", context="", builder=_Builder(), adversary=_Adversary(),
            max_rounds=3, progress=lines.append,
        )
        silent = run_review(
            decision="Open a store", context="", builder=_Builder(), adversary=_Adversary(), max_rounds=3,
        )
        self.assertEqual(lines[0], "builder (fake/builder): drafting claims...")
        self.assertEqual(lines[1], "builder: 2 claims")
        self.assertEqual(lines[2], "round 1/3 (fake/adversary): adversary reviewing...")
        self.assertEqual(lines[3], "round 1: 2 new challenges (1 BLOCKING, 1 NON_BLOCKING)")
        self.assertEqual(lines[4], "round 2/3 (fake/adversary): adversary reviewing...")
        self.assertEqual(lines[5], "round 2: 0 new challenges (nothing new)")
        self.assertTrue(lines[6].startswith("stopping: "))
        self.assertTrue(lines[7].startswith("gate: WAIT"))
        self.assertEqual(len(lines), 8)
        # The callback is observational only: same claims, challenges and verdict either way.
        strip = lambda rows: [{k: v for k, v in r.items() if k != "completed_at"} for r in rows]
        for key in ("claims", "challenges", "review_rounds"):
            self.assertEqual(strip(with_progress[key]), strip(silent[key]))
        self.assertEqual(with_progress["commitment"]["action"], silent["commitment"]["action"])


if __name__ == "__main__":
    unittest.main()
