import unittest

from decision_gate.lifecycle import check_reopen, score_outcomes


class LifecycleTests(unittest.TestCase):
    def ledger(self):
        return {
            "decision": "Build it",
            "claims": [{"id": "CL-001"}, {"id": "CL-002"}],
            "challenges": [
                {"id": "CH-001", "status": "UNRESOLVED", "materiality": "BLOCKING"},
                {"id": "CH-002", "status": "UNRESOLVED", "materiality": "MATERIAL"},
            ],
            "termination": {"reason": "closed"},
            "commitment": {"action": "WAIT"},
        }

    def test_new_evidence_reopens_target_only(self):
        ok, reason = check_reopen(self.ledger(), trigger="NEW_EVIDENCE", challenge_id="CH-001")
        self.assertTrue(ok)
        self.assertIn("CH-001", reason)

    def test_new_evidence_requires_target(self):
        ok, _ = check_reopen(self.ledger(), trigger="NEW_EVIDENCE")
        self.assertFalse(ok)

    def test_outcome_score_flags_underestimated_material_risk(self):
        result = score_outcomes(
            self.ledger(),
            {"claims": {"CL-001": "HELD", "CL-002": "FAILED"}, "risks": {"CH-002": "REALIZED"}},
        )
        self.assertEqual(result["claims_failed"], 1)
        self.assertEqual(result["possibly_underestimated_challenges"], ["CH-002"])


if __name__ == "__main__":
    unittest.main()
