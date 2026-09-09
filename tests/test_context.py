import unittest

from decision_gate.runner import run_review


class _Builder:
    def generate_json(self, *, system, prompt):
        return {"claims": [{"title": "Access granted", "statement": "We have sandbox access.", "kind": "DEPENDENCY"}]}


class _RecordingAdversary:
    def __init__(self):
        self.prompts = []

    def generate_json(self, *, system, prompt):
        self.prompts.append(prompt)
        return {"challenges": []}


class AdversaryContextTests(unittest.TestCase):
    def test_adversary_sees_the_context(self):
        adversary = _RecordingAdversary()
        run_review(
            decision="Build it",
            context="The IT director granted sandbox access on 2 September.",
            builder=_Builder(),
            adversary=adversary,
        )
        self.assertIn("granted sandbox access on 2 September", adversary.prompts[0])
        self.assertIn("Do not raise a challenge the context already answers", adversary.prompts[0])

    def test_empty_context_is_shown_as_none(self):
        adversary = _RecordingAdversary()
        run_review(decision="Build it", context="", builder=_Builder(), adversary=adversary)
        self.assertIn("Context (evidence already on the record):\n(none)", adversary.prompts[0])


if __name__ == "__main__":
    unittest.main()
