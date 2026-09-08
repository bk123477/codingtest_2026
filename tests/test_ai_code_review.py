import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


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

    def test_record_groups_separate_problem_and_learning_note_records(self):
        paths = [
            "records/2026/09/08/alice/programmers-12922/solution.py",
            "records/2026/09/08/alice/programmers-12922/README.md",
            "records/2026/09/08/alice/note-git/README.md",
            "records/2026/09/08/alice/note-git/notes.md",
            "records/2026/09/08/alice/codetree-street-light/solution.py",
            "members/alice.json",
        ]

        self.assertEqual(
            MODULE.review_groups(paths),
            [
                "records/2026/09/08/alice/programmers-12922",
                "records/2026/09/08/alice/note-git",
                "records/2026/09/08/alice/codetree-street-light",
                "기타 변경 파일",
            ],
        )

    def test_group_descriptions_use_metadata_not_folder_prefix(self):
        paths = [
            "records/2026/09/08/alice/codetree-street-light/solution.py",
            "records/2026/09/08/alice/algorithm-note/README.md",
        ]
        with patch.object(
            MODULE,
            "run_git",
            side_effect=[
                '{"type":"problem","platform":"codetree","solution":"solution.py"}',
                '{"type":"note"}',
            ],
        ):
            descriptions = MODULE.review_group_descriptions("head", paths)

        self.assertEqual(
            descriptions,
            [
                ("records/2026/09/08/alice/codetree-street-light", "코딩 문제 · codetree"),
                ("records/2026/09/08/alice/algorithm-note", "학습 정리"),
            ],
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

    def test_diff_contains_separate_record_group_headers(self):
        paths = [
            "records/2026/09/08/alice/programmers-12922/solution.py",
            "records/2026/09/08/alice/note-git/README.md",
        ]
        with patch.object(MODULE, "run_git", side_effect=["problem diff", "note diff"]):
            diff = MODULE.collect_diff("base", "head", paths, 10_000)

        self.assertIn(
            "## Review group: records/2026/09/08/alice/programmers-12922",
            diff,
        )
        self.assertIn("## Review group: records/2026/09/08/alice/note-git", diff)

    def test_review_prompt_requires_concise_korean_output(self):
        self.assertIn("concise Korean", MODULE.SYSTEM_PROMPT)
        self.assertIn("at most three short bullets", MODULE.SYSTEM_PROMPT)
        self.assertIn("## 🤖 AI Code Review", MODULE.SYSTEM_PROMPT)
        self.assertIn("For every changed record group", MODULE.SYSTEM_PROMPT)
        self.assertIn("#### 🚨 Critical", MODULE.SYSTEM_PROMPT)
        self.assertIn("factual errors", MODULE.SYSTEM_PROMPT)
        self.assertIn("inappropriate data", MODULE.SYSTEM_PROMPT)

    def test_review_prompt_lists_changed_record_groups(self):
        messages = MODULE.build_messages(
            "diff",
            "context",
            "alice/example",
            12,
            [
                "records/2026/09/08/alice/programmers-12922/solution.py",
                "records/2026/09/08/alice/note-git/README.md",
            ],
        )

        user_prompt = messages[1]["content"]
        self.assertIn("records/2026/09/08/alice/programmers-12922", user_prompt)
        self.assertIn("records/2026/09/08/alice/note-git", user_prompt)

    def test_changed_paths_compares_base_tip_to_head_without_merge_base(self):
        with patch.object(
            MODULE,
            "run_git",
            return_value="M\trecords/2026/09/07/alice/programmers-1/solution.py\n",
        ) as run_git:
            paths = MODULE.changed_paths("base-sha", "head-sha")

        self.assertEqual(
            paths,
            ["records/2026/09/07/alice/programmers-1/solution.py"],
        )
        run_git.assert_called_once_with(
            "diff",
            "--name-status",
            "--find-renames",
            "base-sha..head-sha",
            "--",
        )


if __name__ == "__main__":
    unittest.main()
