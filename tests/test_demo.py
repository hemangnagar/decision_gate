import unittest

from decision_gate.demo import DEMO_CONTEXT, DEMO_DECISION, DemoAdversary, DemoBuilder
from decision_gate.gate import evaluate_if_resolved
from decision_gate.runner import run_review
from decision_gate.validate import validate_ledger


class DemoScenarioTests(unittest.TestCase):
    def run_demo(self):
        return run_review(decision=DEMO_DECISION, context=DEMO_CONTEXT, builder=DemoBuilder(), adversary=DemoAdversary())

    def test_demo_ledger_is_valid(self):
        self.assertEqual(validate_ledger(self.run_demo()), [])

    def test_demo_stops_after_an_empty_round(self):
        ledger = self.run_demo()
        self.assertEqual([r["new_challenges"] for r in ledger["review_rounds"]], [3, 0])
        self.assertIn("no new MATERIAL", ledger["termination"]["reason"])

    def test_demo_waits_on_the_single_blocking_challenge(self):
        ledger = self.run_demo()
        self.assertEqual(ledger["commitment"]["action"], "WAIT")
        self.assertEqual(ledger["commitment"]["matched_rule"], "UNRESOLVED_BLOCKING")
        self.assertEqual(ledger["commitment"]["triggering_challenges"], ["CH-001"])
        self.assertEqual(ledger["challenges"][0]["materiality"], "BLOCKING")

    def test_demo_states_what_flips_the_gate(self):
        after = self.run_demo()["commitment"]["if_triggers_resolved"]
        self.assertEqual(after["action"], "ACT")
        self.assertEqual(
            after["accepted_risks"],
            ["The bottleneck is asserted, not measured", "EHR vendor roadmaps are unknown"],
        )


class CounterfactualGateTests(unittest.TestCase):
    def test_resolving_fatal_can_still_leave_wait(self):
        ledger = {
            "challenges": [
                {"id": "A", "materiality": "FATAL", "status": "UNRESOLVED", "title": "a"},
                {"id": "B", "materiality": "BLOCKING", "status": "UNRESOLVED", "title": "b"},
            ]
        }
        result = evaluate_if_resolved(ledger, ["A"])
        self.assertEqual(result.action, "WAIT")
        self.assertEqual(result.triggering_challenges, ["B"])
        # The original ledger is untouched.
        self.assertEqual(ledger["challenges"][0]["status"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
