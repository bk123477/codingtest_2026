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
        self.assertIn("한국어로 작성", MODULE.SYSTEM_PROMPT)
        self.assertIn("분석 과정, 사고 과정, 작업 계획을 출력하지 마세요", MODULE.SYSTEM_PROMPT)
        self.assertIn("Let me analyze", MODULE.SYSTEM_PROMPT)
        self.assertIn("## 🤖 AI Code Review", MODULE.SYSTEM_PROMPT)
        self.assertIn("### 📁 <record directory>", MODULE.SYSTEM_PROMPT)
        self.assertIn("#### 🚨 Critical", MODULE.SYSTEM_PROMPT)
        self.assertIn("### ✅ Summary", MODULE.SYSTEM_PROMPT)

    def test_user_prompt_requires_korean_final_review_without_analysis(self):
        messages = MODULE.build_messages("diff", "context", "alice/repo", 1)
        user_prompt = messages[1]["content"]
        self.assertIn("한국어 최종 리뷰만 출력", user_prompt)
        self.assertIn("분석 과정 출력 금지", user_prompt)

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

    def test_validate_review_output_pass_cases(self):
        # 1. Normal Korean review
        normal_review = (
            "## 🤖 AI Code Review\n\n"
            "### 📁 records/2026/09/08/alice/programmers-1\n"
            "구체적인 오류를 발견하지 못했습니다.\n\n"
            "### ✅ Summary\n"
            "전체적으로 깔끔하게 작성되었습니다."
        )
        self.assertTrue(MODULE.validate_review_output(normal_review))

        # 2. Korean review with code identifiers and English terms
        code_review = (
            "## 🤖 AI Code Review\n\n"
            "### 📁 records/2026/09/08/alice/programmers-12903\n"
            "#### 💡 Suggestions\n"
            "- `solution.py`의 `s[len(s)//2]` 슬라이싱 로직이 직관적입니다.\n"
            "- O(1) 시간 복잡도로 잘 해결되었습니다.\n\n"
            "### ✅ Summary\n"
            "문자열 인덱싱을 적절히 활용하여 효율적으로 해결했습니다."
        )
        self.assertTrue(MODULE.validate_review_output(code_review))

    def test_validate_review_output_fail_cases(self):
        # Starts with "Let me analyze..."
        preamble_review = (
            "Let me analyze the PR material first...\n"
            "## 🤖 AI Code Review\n\n"
            "### 📁 records/2026/09/08/alice/p-1\n"
            "구체적인 오류를 발견하지 못했습니다.\n\n"
            "### ✅ Summary\n"
            "요약입니다."
        )
        self.assertFalse(MODULE.validate_review_output(preamble_review))

        # Contains other preambles like "Let me think", "Wait,", etc.
        self.assertFalse(MODULE.validate_review_output(
            "## 🤖 AI Code Review\n\nWait, let me re-check...\n### ✅ Summary\n요약입니다."
        ))
        self.assertFalse(MODULE.validate_review_output(
            "## 🤖 AI Code Review\n\nI need to inspect the code...\n### ✅ Summary\n요약입니다."
        ))
        self.assertFalse(MODULE.validate_review_output(
            "## 🤖 AI Code Review\n\nFirst, let me inspect the code...\n### ✅ Summary\n요약입니다."
        ))

        # Mostly English review without sufficient Korean
        english_review = (
            "## 🤖 AI Code Review\n\n"
            "### 📁 records/2026/09/08/alice/programmers-1\n"
            "#### 💡 Suggestions\n"
            "- The solution looks great and handles edge cases properly.\n"
            "- Time complexity is O(N) which is optimal.\n\n"
            "### ✅ Summary\n"
            "Good job on this pull request."
        )
        self.assertFalse(MODULE.validate_review_output(english_review))

        # Missing Summary section
        no_summary = (
            "## 🤖 AI Code Review\n\n"
            "### 📁 records/2026/09/08/alice/programmers-1\n"
            "구체적인 오류를 발견하지 못했습니다."
        )
        self.assertFalse(MODULE.validate_review_output(no_summary))

        # Empty or too short response
        self.assertFalse(MODULE.validate_review_output(""))
        self.assertFalse(MODULE.validate_review_output("   \n  "))
        self.assertFalse(MODULE.validate_review_output("## 🤖 AI Code Review\n짧음"))

    def test_parse_openrouter_payload_and_truncation_detection(self):
        import json
        # Normal completion
        normal_payload = {
            "choices": [
                {
                    "message": {"content": "정상 응답입니다."},
                    "finish_reason": "stop",
                }
            ]
        }
        text, reason = MODULE.parse_openrouter_payload(normal_payload)
        self.assertEqual(text, "정상 응답입니다.")
        self.assertEqual(reason, "stop")

        # Truncated completion (finish_reason: length)
        truncated_payload = {
            "choices": [
                {
                    "message": {"content": "중간에 잘린 응답..."},
                    "finish_reason": "length",
                }
            ]
        }
        text, reason = MODULE.parse_openrouter_payload(truncated_payload)
        self.assertEqual(reason, "length")

        # In call_openrouter, finish_reason == 'length' must raise ReviewSkipped
        with patch.object(MODULE, "urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = json.dumps(truncated_payload).encode("utf-8")
            with self.assertRaises(MODULE.ReviewSkipped) as cm:
                MODULE.call_openrouter("fake-key", "fake-model", [{"role": "user", "content": "hi"}])
            self.assertIn("truncated", str(cm.exception))

    def test_generate_review_batches_large_prs(self):
        paths = [
            f"records/2026/09/08/alice/prob-{i}/solution.py" for i in range(1, 7)
        ]
        batch_responses = [
            (
                "### 📁 records/2026/09/08/alice/prob-1\n구체적인 오류를 발견하지 못했습니다.\n\n"
                "### 📁 records/2026/09/08/alice/prob-2\n구체적인 오류를 발견하지 못했습니다.\n\n"
                "### 📁 records/2026/09/08/alice/prob-3\n구체적인 오류를 발견하지 못했습니다."
            ),
            (
                "### 📁 records/2026/09/08/alice/prob-4\n구체적인 오류를 발견하지 못했습니다.\n\n"
                "### 📁 records/2026/09/08/alice/prob-5\n구체적인 오류를 발견하지 못했습니다.\n\n"
                "### 📁 records/2026/09/08/alice/prob-6\n구체적인 오류를 발견하지 못했습니다."
            ),
        ]

        with patch.object(MODULE, "call_openrouter", side_effect=batch_responses) as mock_call, \
             patch.object(MODULE, "collect_diff", return_value="dummy diff"), \
             patch.object(MODULE, "collect_record_context", return_value="dummy context"), \
             patch.object(MODULE, "review_group_descriptions", return_value=[(f"records/2026/09/08/alice/prob-{i}", "코딩 문제") for i in range(1, 7)]), \
             patch.object(MODULE, "time"):
            review = MODULE.generate_review(
                "base", "head", paths, "alice/repo", 1, "key", "model", batch_size=3
            )

        self.assertEqual(mock_call.call_count, 2)
        self.assertTrue(review.startswith("## 🤖 AI Code Review"))
        self.assertIn("### ✅ Summary", review)
        self.assertIn("prob-1", review)
        self.assertIn("prob-6", review)
        self.assertTrue(MODULE.validate_review_output(review))


if __name__ == "__main__":
    unittest.main()

