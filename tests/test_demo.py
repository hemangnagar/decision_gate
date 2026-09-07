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

    def test_missing_evidence_is_capped(self):
        ch = {c["id"]: c for c in self.run_demo()["challenges"]}["CH-001"]
        self.assertEqual((ch["requested_materiality"], ch["materiality"]), ("BLOCKING", "MATERIAL"))
        self.assertEqual(ch["materiality_rule"], "MISSING_EVIDENCE_CAPPED")
        self.assertEqual(ch["rebuttal"]["response"], "DISPUTED")

    def test_builder_resolves_by_quoting_the_record(self):
        ch = {c["id"]: c for c in self.run_demo()["challenges"]}["CH-002"]
        self.assertEqual(ch["materiality"], "BLOCKING")  # a DEPENDENCY may be blocked by missing evidence
        self.assertEqual(ch["status"], "RESOLVED")
        self.assertEqual(ch["resolution"]["by"], "BUILDER")

    def test_contrary_evidence_keeps_its_rating_and_is_conceded(self):
        ch = {c["id"]: c for c in self.run_demo()["challenges"]}["CH-003"]
        self.assertEqual(ch["basis"], "CONTRARY_EVIDENCE")
        self.assertEqual(ch["materiality_rule"], "CONTRARY_EVIDENCE_AS_REQUESTED")
        self.assertEqual(ch["rebuttal"]["response"], "CONCEDED")

    def test_demo_acts_with_two_named_risks(self):
        ledger = self.run_demo()
        self.assertEqual(ledger["commitment"]["action"], "ACT")
        self.assertEqual(ledger["commitment"]["matched_rule"], "NO_UNRESOLVED_FATAL_OR_BLOCKING")
        self.assertEqual(
            ledger["commitment"]["accepted_risks"],
            ["The bottleneck is asserted, not measured", "A major EHR vendor is building the same thing"],
        )
        self.assertEqual(ledger["review_rounds"][0]["capped_by_rule"], 1)
        self.assertEqual(ledger["review_rounds"][0]["resolved_by_builder"], 1)


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
