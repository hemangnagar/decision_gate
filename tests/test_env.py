import os
import tempfile
import unittest
from pathlib import Path

from decision_gate.env import load_dotenv


class DotenvTests(unittest.TestCase):
    def test_loads_without_overriding_and_strips_quotes(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, ".env").write_text(
                '# comment\nDG_TEST_A="quoted value"\nexport DG_TEST_B=plain\nDG_TEST_C=already\n\n', encoding="utf-8"
            )
            os.environ["DG_TEST_C"] = "kept"
            cwd = os.getcwd()
            try:
                os.chdir(d)
                self.assertIsNotNone(load_dotenv())
            finally:
                os.chdir(cwd)
            self.assertEqual(os.environ.get("DG_TEST_A"), "quoted value")
            self.assertEqual(os.environ.get("DG_TEST_B"), "plain")
            self.assertEqual(os.environ.get("DG_TEST_C"), "kept")
            for k in ("DG_TEST_A", "DG_TEST_B", "DG_TEST_C"):
                os.environ.pop(k, None)


if __name__ == "__main__":
    unittest.main()
