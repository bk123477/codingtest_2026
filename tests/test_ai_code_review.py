import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "scripts"
    / "ai_code_review.py"
)
SPEC = importlib.util.spec_from_file_location("ai_code_review", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AiCodeReviewTests(unittest.TestCase):
    def test_reviewable_problem_files_are_kept(self):
        self.assertTrue(
            MODULE.is_reviewable_path(
                "records/2026/09/07/alice/programmers-1/solution.py"
            )
        )
        self.assertTrue(
            MODULE.is_reviewable_path(
                "records/2026/09/07/alice/programmers-1/README.md"
            )
        )

    def test_generated_and_binary_files_are_skipped(self):
        self.assertFalse(MODULE.is_reviewable_path("dist/bundle.min.js"))
        self.assertFalse(MODULE.is_reviewable_path("records/x/programmers-1/meta.json"))
        self.assertFalse(MODULE.is_reviewable_path("assets/example.png"))

    def test_secrets_are_redacted(self):
        secret = "sk-or-v1-" + "example-secret"
        text = "OPENROUTER_API_KEY=" + secret
        redacted = MODULE.redact_secrets(text)
        self.assertNotIn(secret, redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_clip_marks_truncation(self):
        value, truncated = MODULE.clip("abcdef", 3)
        self.assertTrue(truncated)
        self.assertTrue(value.startswith("abc"))


if __name__ == "__main__":
    unittest.main()
