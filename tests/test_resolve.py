import copy
import unittest

from decision_gate.lifecycle import resolve_challenge, score_outcomes


def _ledger():
    return {
        "id": "D", "decision": "Build it", "created_at": "now", "context": "",
        "claims": [{"id": "CL-001", "depends_on": []}],
        "challenges": [
            {"id": "CH-001", "target_claim": "CL-001", "title": "No access", "materiality": "BLOCKING",
             "status": "UNRESOLVED", "resolves_if": "Written access."},
            {"id": "CH-002", "target_claim": "CL-001", "title": "Unmeasured", "materiality": "MATERIAL",
             "status": "UNRESOLVED", "resolves_if": "A time study."},
        ],
        "review_rounds": [{"round": 1, "new_challenges": 2, "new_material_or_blocking": 2}],
        "termination": {"reason": "closed", "round": 1},
        "commitment": {"action": "WAIT", "matched_rule": "UNRESOLVED_BLOCKING", "triggering_challenges": ["CH-001"]},
    }


class ResolveChallengeTests(unittest.TestCase):
    def test_human_evidence_flips_wait_to_act_and_is_recorded(self):
        ledger = resolve_challenge(_ledger(), challenge_id="CH-001", evidence="Signed access agreement dated 3 Sept.")
        ch = ledger["challenges"][0]
        self.assertEqual(ch["status"], "RESOLVED")
        self.assertEqual(ch["resolution"]["by"], "HUMAN")
        self.assertEqual(ledger["evidence"][0]["id"], "EV-001")
        self.assertEqual(ledger["evidence"][0]["challenge"], "CH-001")
        self.assertEqual(ledger["commitment"]["action"], "ACT")
        self.assertEqual(ledger["commitment"]["accepted_risks"], ["Unmeasured"])
        self.assertEqual(ledger["commitment_history"][0]["action"], "WAIT")

    def test_requires_evidence(self):
        with self.assertRaises(ValueError):
            resolve_challenge(_ledger(), challenge_id="CH-001", evidence="   ")

    def test_rejects_unknown_and_already_resolved_targets(self):
        with self.assertRaises(ValueError):
            resolve_challenge(_ledger(), challenge_id="CH-999", evidence="x y z evidence")
        ledger = resolve_challenge(_ledger(), challenge_id="CH-001", evidence="Signed access agreement.")
        with self.assertRaises(ValueError):
            resolve_challenge(ledger, challenge_id="CH-001", evidence="Again.")

    def test_requires_a_closed_review(self):
        ledger = _ledger()
        del ledger["termination"]
        with self.assertRaises(ValueError):
            resolve_challenge(ledger, challenge_id="CH-001", evidence="Signed access agreement.")


class TwoSidedScoringTests(unittest.TestCase):
    def test_scorer_flags_harsh_ratings_as_well_as_lenient_ones(self):
        ledger = _ledger()
        result = score_outcomes(ledger, {
            "claims": {"CL-001": "HELD"},
            "risks": {"CH-001": "NOT_REALIZED", "CH-002": "REALIZED"},
        })
        self.assertEqual(result["possibly_overestimated_challenges"], ["CH-001"])
        self.assertEqual(result["possibly_underestimated_challenges"], ["CH-002"])
        self.assertEqual(result["risks_not_realized"], 1)


if __name__ == "__main__":
    unittest.main()
