import unittest
from decision_gate.gate import evaluate_gate, should_stop
from decision_gate.validate import validate_ledger


class GateTests(unittest.TestCase):
    def base(self):
        return {"id":"D","decision":"x","created_at":"now","claims":[{"id":"C1","depends_on":[]}],"challenges":[],"review_rounds":[]}

    def test_act(self):
        result = evaluate_gate(self.base())
        self.assertEqual(result.action, "ACT")
        self.assertEqual(result.matched_rule, "NO_UNRESOLVED_FATAL_OR_BLOCKING")
        self.assertEqual(result.triggering_challenges, [])

    def test_wait(self):
        d=self.base(); d["challenges"]=[{"id":"X","target_claim":"C1","title":"x","materiality":"BLOCKING","status":"UNRESOLVED","resolves_if":"e"}]
        result = evaluate_gate(d)
        self.assertEqual(result.action,"WAIT")
        self.assertEqual(result.matched_rule,"UNRESOLVED_BLOCKING")
        self.assertEqual(result.triggering_challenges,["X"])

    def test_abandon(self):
        d=self.base(); d["challenges"]=[{"id":"X","target_claim":"C1","title":"x","materiality":"FATAL","status":"UNRESOLVED","resolves_if":"e"}]
        result = evaluate_gate(d)
        self.assertEqual(result.action,"ABANDON")
        self.assertEqual(result.matched_rule,"UNRESOLVED_FATAL")
        self.assertEqual(result.triggering_challenges,["X"])

    def test_stop_no_new_material(self):
        stop, reason = should_stop([{"new_material_or_blocking":0}])
        self.assertTrue(stop)
        self.assertIn("no new MATERIAL", reason)

    def test_no_new_material_reason_beats_max_round_reason(self):
        rounds = [
            {"new_material_or_blocking":2},
            {"new_material_or_blocking":1},
            {"new_material_or_blocking":0},
        ]
        stop, reason = should_stop(rounds, max_rounds=3)
        self.assertTrue(stop)
        self.assertIn("no new MATERIAL", reason)

    def test_unresolved_requires_recipe(self):
        d=self.base(); d["challenges"]=[{"id":"X","target_claim":"C1","title":"x","materiality":"MATERIAL","status":"UNRESOLVED"}]
        self.assertTrue(any("resolves_if" in x for x in validate_ledger(d)))


if __name__ == '__main__':
    unittest.main()
