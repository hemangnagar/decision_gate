import unittest

from decision_gate.gate import assign_materiality
from decision_gate.runner import run_review
from decision_gate.validate import validate_ledger


class MaterialityRuleTests(unittest.TestCase):
    def test_missing_evidence_caps_at_material_on_an_assumption(self):
        r = assign_materiality(requested="BLOCKING", basis="MISSING_EVIDENCE", claim_kind="ASSUMPTION", evidence="")
        self.assertEqual((r.materiality, r.rule, r.cap), ("MATERIAL", "MISSING_EVIDENCE_CAPPED", "MATERIAL"))

    def test_missing_evidence_cannot_be_fatal_even_on_a_dependency(self):
        r = assign_materiality(requested="FATAL", basis="MISSING_EVIDENCE", claim_kind="DEPENDENCY", evidence="")
        self.assertEqual((r.materiality, r.cap), ("BLOCKING", "BLOCKING"))

    def test_missing_evidence_can_block_a_dependency(self):
        r = assign_materiality(requested="BLOCKING", basis="MISSING_EVIDENCE", claim_kind="DEPENDENCY", evidence="")
        self.assertEqual((r.materiality, r.rule), ("BLOCKING", "MISSING_EVIDENCE_WITHIN_CAP"))

    def test_contrary_evidence_keeps_the_requested_materiality(self):
        r = assign_materiality(requested="FATAL", basis="CONTRARY_EVIDENCE", claim_kind="ASSUMPTION", evidence="Prior art covers it")
        self.assertEqual((r.materiality, r.rule), ("FATAL", "CONTRARY_EVIDENCE_AS_REQUESTED"))

    def test_contrary_evidence_with_nothing_stated_is_missing_evidence(self):
        r = assign_materiality(requested="FATAL", basis="CONTRARY_EVIDENCE", claim_kind="ASSUMPTION", evidence="  ")
        self.assertEqual((r.materiality, r.basis), ("MATERIAL", "MISSING_EVIDENCE"))

    def test_unknown_or_absent_basis_is_missing_evidence(self):
        for basis in (None, "", "VIBES"):
            r = assign_materiality(requested="BLOCKING", basis=basis, claim_kind="FACT", evidence="")
            self.assertEqual(r.materiality, "MATERIAL", basis)

    def test_within_cap_is_left_alone(self):
        r = assign_materiality(requested="NON_BLOCKING", basis="MISSING_EVIDENCE", claim_kind="ASSUMPTION", evidence="")
        self.assertEqual(r.materiality, "NON_BLOCKING")


class _Builder:
    def generate_json(self, *, system, prompt):
        return {"claims": [
            {"title": "Demand exists", "statement": "There is demand.", "kind": "ASSUMPTION"},
            {"title": "Landlord will sign", "statement": "The landlord signs a lease.", "kind": "DEPENDENCY"},
        ]}


class _Adversary:
    def __init__(self):
        self.calls = 0

    def generate_json(self, *, system, prompt):
        self.calls += 1
        if self.calls > 1:
            return {"challenges": []}
        return {"challenges": [
            {"target_claim": "CL-001", "title": "No demand study", "argument": "Nothing shows demand.",
             "basis": "MISSING_EVIDENCE", "materiality": "BLOCKING", "resolves_if": "A demand study."},
            {"target_claim": "CL-002", "title": "No lease yet", "argument": "No lease is signed.",
             "basis": "MISSING_EVIDENCE", "materiality": "BLOCKING", "resolves_if": "A signed lease."},
            {"target_claim": "CL-001", "title": "Footfall fell 30%", "argument": "The street lost its anchor tenant.",
             "basis": "CONTRARY_EVIDENCE", "evidence": "Footfall counts fell 30% after the anchor tenant left.",
             "materiality": "BLOCKING", "resolves_if": "New footfall counts."},
        ]}


class MaterialityInRunnerTests(unittest.TestCase):
    def test_runner_records_requested_versus_assigned(self):
        ledger = run_review(decision="Open a store", context="", builder=_Builder(), adversary=_Adversary())
        self.assertEqual(validate_ledger(ledger), [])
        by_id = {c["id"]: c for c in ledger["challenges"]}
        capped = by_id["CH-001"]
        self.assertEqual((capped["requested_materiality"], capped["materiality"]), ("BLOCKING", "MATERIAL"))
        self.assertEqual(capped["materiality_rule"], "MISSING_EVIDENCE_CAPPED")
        dependency = by_id["CH-002"]
        self.assertEqual(dependency["materiality"], "BLOCKING")
        contrary = by_id["CH-003"]
        self.assertEqual(contrary["materiality"], "BLOCKING")
        self.assertIn("30%", contrary["evidence"])
        self.assertEqual(ledger["review_rounds"][0]["capped_by_rule"], 1)
        self.assertEqual(ledger["commitment"]["triggering_challenges"], ["CH-002", "CH-003"])

    def test_a_bare_allegation_cannot_block(self):
        class Bare:
            calls = 0
            def generate_json(self, *, system, prompt):
                self.calls += 1
                if self.calls > 1:
                    return {"challenges": []}
                return {"challenges": [{"target_claim": "CL-001", "title": "Unproven", "argument": "x",
                                        "materiality": "FATAL", "resolves_if": "Prove it."}]}
        ledger = run_review(decision="Open a store", context="", builder=_Builder(), adversary=Bare())
        self.assertEqual(ledger["commitment"]["action"], "ACT")
        self.assertEqual(ledger["commitment"]["accepted_risks"], ["Unproven"])


if __name__ == "__main__":
    unittest.main()
