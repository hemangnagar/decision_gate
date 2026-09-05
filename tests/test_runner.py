import unittest

from decision_gate.runner import run_review


class StubBuilder:
    def generate_json(self, *, system, prompt):
        return {
            "claims": [
                {"title": "Problem exists", "statement": "The target problem is real", "kind": "ASSUMPTION", "depends_on": []},
                {"title": "Action is feasible", "statement": "The action can be executed", "kind": "ASSUMPTION", "depends_on": []},
            ]
        }


class StubAdversary:
    def __init__(self, materiality="MATERIAL"):
        self.materiality = materiality
        self.calls = 0

    def generate_json(self, *, system, prompt):
        self.calls += 1
        if self.calls > 1:
            return {"challenges": []}
        return {
            "challenges": [
                {
                    "target_claim": "CL-002",
                    "title": "Feasibility unproven",
                    "argument": "No feasibility proof is present",
                    "materiality": self.materiality,
                    "resolves_if": "Run a small feasibility test",
                }
            ]
        }


class RunnerTests(unittest.TestCase):
    def test_material_challenge_can_act_with_accepted_risk(self):
        ledger = run_review(decision="Build it", context="", builder=StubBuilder(), adversary=StubAdversary("MATERIAL"))
        self.assertEqual(ledger["commitment"]["action"], "ACT")
        self.assertEqual(len(ledger["review_rounds"]), 2)
        self.assertIn("Feasibility unproven", ledger["commitment"]["accepted_risks"])

    def test_blocking_challenge_waits(self):
        ledger = run_review(decision="Build it", context="", builder=StubBuilder(), adversary=StubAdversary("BLOCKING"))
        self.assertEqual(ledger["commitment"]["action"], "WAIT")

    def test_fatal_challenge_abandons(self):
        ledger = run_review(decision="Build it", context="", builder=StubBuilder(), adversary=StubAdversary("FATAL"))
        self.assertEqual(ledger["commitment"]["action"], "ABANDON")


if __name__ == "__main__":
    unittest.main()
