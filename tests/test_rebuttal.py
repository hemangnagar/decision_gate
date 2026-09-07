import unittest

from decision_gate.prompts import REBUTTAL_SYSTEM
from decision_gate.rebuttal import apply_rebuttals, apply_withdrawals, evidence_on_record
from decision_gate.runner import run_review
from decision_gate.validate import validate_ledger

CONTEXT = "Small team. The IT director granted sandbox access to the scheduling system on 2 September."


class EvidenceOnRecordTests(unittest.TestCase):
    def test_verbatim_quote_is_found(self):
        self.assertTrue(evidence_on_record("granted sandbox access to the scheduling system", CONTEXT))

    def test_case_whitespace_and_surrounding_quotes_are_ignored(self):
        self.assertTrue(evidence_on_record('  "Granted   SANDBOX access to the scheduling system."  ', CONTEXT))

    def test_paraphrase_is_rejected(self):
        self.assertFalse(evidence_on_record("IT gave us sandbox access", CONTEXT))

    def test_too_short_is_rejected(self):
        self.assertFalse(evidence_on_record("IT", CONTEXT))
        self.assertFalse(evidence_on_record("", CONTEXT))


def _ledger():
    return {
        "context": CONTEXT,
        "challenges": [
            {"id": "CH-001", "status": "UNRESOLVED", "materiality": "BLOCKING", "title": "a"},
            {"id": "CH-002", "status": "UNRESOLVED", "materiality": "MATERIAL", "title": "b"},
            {"id": "CH-003", "status": "UNRESOLVED", "materiality": "MATERIAL", "title": "c"},
            {"id": "CH-004", "status": "UNRESOLVED", "materiality": "MATERIAL", "title": "d"},
        ],
    }


class ApplyRebuttalsTests(unittest.TestCase):
    def test_each_response_kind_and_the_unanswered_marker(self):
        ledger = _ledger()
        counts = apply_rebuttals(ledger, [
            {"challenge": "CH-001", "response": "RESOLVED", "evidence": "granted sandbox access to the scheduling system"},
            {"challenge": "CH-002", "response": "RESOLVED", "evidence": "we definitely have access"},
            {"challenge": "CH-003", "response": "DISPUTED", "argument": "Overstated."},
        ], round_no=1)
        by_id = {c["id"]: c for c in ledger["challenges"]}
        self.assertEqual(by_id["CH-001"]["status"], "RESOLVED")
        self.assertEqual(by_id["CH-001"]["resolution"]["by"], "BUILDER")
        self.assertEqual(by_id["CH-002"]["status"], "UNRESOLVED")
        self.assertEqual(by_id["CH-002"]["rebuttal"]["response"], "DISPUTED")
        self.assertIn("not in the context", by_id["CH-002"]["rebuttal"]["note"])
        self.assertEqual(by_id["CH-003"]["rebuttal"]["response"], "DISPUTED")
        self.assertEqual(by_id["CH-004"]["rebuttal"]["response"], "UNANSWERED")
        self.assertEqual(counts, {"resolved": 1, "disputed": 2, "conceded": 0, "unverified": 1, "unanswered": 1})

    def test_a_challenge_gets_one_builder_turn(self):
        ledger = _ledger()
        apply_rebuttals(ledger, [{"challenge": "CH-001", "response": "CONCEDED"}], round_no=1)
        apply_rebuttals(ledger, [{"challenge": "CH-001", "response": "RESOLVED",
                                  "evidence": "granted sandbox access to the scheduling system"}], round_no=2)
        self.assertEqual(ledger["challenges"][0]["status"], "UNRESOLVED")
        self.assertEqual(ledger["challenges"][0]["rebuttal"]["response"], "CONCEDED")

    def test_withdrawal_only_of_disputed_challenges(self):
        ledger = _ledger()
        apply_rebuttals(ledger, [
            {"challenge": "CH-001", "response": "DISPUTED", "argument": "x"},
            {"challenge": "CH-002", "response": "CONCEDED"},
        ], round_no=1)
        n = apply_withdrawals(ledger, [
            {"challenge": "CH-001", "reason": "The Builder is right."},
            {"challenge": "CH-002", "reason": "Feeling generous."},
            {"challenge": "CH-003", "reason": "Never disputed."},
        ], round_no=2)
        self.assertEqual(n, 1)
        by_id = {c["id"]: c for c in ledger["challenges"]}
        self.assertEqual(by_id["CH-001"]["status"], "WITHDRAWN")
        self.assertEqual(by_id["CH-002"]["status"], "UNRESOLVED")
        self.assertEqual(by_id["CH-003"]["status"], "UNRESOLVED")


class _Builder:
    def __init__(self, evidence):
        self.evidence = evidence

    def generate_json(self, *, system, prompt):
        if system == REBUTTAL_SYSTEM:
            return {"responses": [{"challenge": "CH-001", "response": "RESOLVED", "evidence": self.evidence}]}
        return {"claims": [{"title": "We can get the data", "statement": "A pilot site grants sandbox access.", "kind": "DEPENDENCY"}]}


class _Adversary:
    def __init__(self, withdraw_on_round_two=False):
        self.calls = 0
        self.withdraw = withdraw_on_round_two

    def generate_json(self, *, system, prompt):
        self.calls += 1
        if self.calls > 1:
            return {"withdraw": [{"challenge": "CH-001", "reason": "Fair."}] if self.withdraw else [], "challenges": []}
        return {"challenges": [{"target_claim": "CL-001", "title": "No access granted", "argument": "Nothing shows access.",
                                "basis": "MISSING_EVIDENCE", "materiality": "BLOCKING", "resolves_if": "Written access."}]}


class RebuttalInRunnerTests(unittest.TestCase):
    def test_verified_resolution_lets_the_claim_win(self):
        ledger = run_review(decision="Build it", context=CONTEXT,
                            builder=_Builder("granted sandbox access to the scheduling system"), adversary=_Adversary())
        self.assertEqual(validate_ledger(ledger), [])
        self.assertEqual(ledger["challenges"][0]["status"], "RESOLVED")
        self.assertEqual(ledger["review_rounds"][0]["resolved_by_builder"], 1)
        self.assertEqual(ledger["commitment"]["action"], "ACT")
        self.assertEqual(ledger["commitment"]["accepted_risks"], [])

    def test_invented_evidence_does_not_resolve(self):
        ledger = run_review(decision="Build it", context=CONTEXT,
                            builder=_Builder("the CTO signed the integration agreement"), adversary=_Adversary())
        self.assertEqual(ledger["challenges"][0]["status"], "UNRESOLVED")
        self.assertEqual(ledger["challenges"][0]["rebuttal"]["response"], "DISPUTED")
        self.assertEqual(ledger["commitment"]["action"], "WAIT")

    def test_adversary_can_withdraw_a_disputed_challenge(self):
        ledger = run_review(decision="Build it", context=CONTEXT,
                            builder=_Builder("the CTO signed the integration agreement"),
                            adversary=_Adversary(withdraw_on_round_two=True))
        self.assertEqual(ledger["challenges"][0]["status"], "WITHDRAWN")
        self.assertEqual(ledger["review_rounds"][1]["withdrawn"], 1)
        self.assertEqual(ledger["commitment"]["action"], "ACT")


if __name__ == "__main__":
    unittest.main()
