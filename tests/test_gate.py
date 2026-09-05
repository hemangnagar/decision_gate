import unittest
from decision_gate.gate import evaluate_gate, should_stop
from decision_gate.validate import validate_ledger

class GateTests(unittest.TestCase):
    def base(self):
        return {"id":"D","decision":"x","created_at":"now","claims":[{"id":"C1","depends_on":[]}],"challenges":[],"review_rounds":[]}
    def test_act(self): self.assertEqual(evaluate_gate(self.base()).action, "ACT")
    def test_wait(self):
        d=self.base(); d["challenges"]=[{"id":"X","target_claim":"C1","title":"x","materiality":"BLOCKING","status":"UNRESOLVED","resolves_if":"e"}]
        self.assertEqual(evaluate_gate(d).action,"WAIT")
    def test_abandon(self):
        d=self.base(); d["challenges"]=[{"id":"X","target_claim":"C1","title":"x","materiality":"FATAL","status":"UNRESOLVED","resolves_if":"e"}]
        self.assertEqual(evaluate_gate(d).action,"ABANDON")
    def test_stop_no_new_material(self):
        self.assertTrue(should_stop([{"new_material_or_blocking":0}])[0])
    def test_unresolved_requires_recipe(self):
        d=self.base(); d["challenges"]=[{"id":"X","target_claim":"C1","title":"x","materiality":"MATERIAL","status":"UNRESOLVED"}]
        self.assertTrue(any("resolves_if" in x for x in validate_ledger(d)))

if __name__ == '__main__': unittest.main()
