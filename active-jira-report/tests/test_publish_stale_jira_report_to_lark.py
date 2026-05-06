from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_stale_jira_report_to_lark.py"
SPEC = importlib.util.spec_from_file_location("publish_stale_jira_report_to_lark", SCRIPT)
assert SPEC is not None
publisher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = publisher
SPEC.loader.exec_module(publisher)


class PublishStaleJiraReportTests(unittest.TestCase):
    def parse(self, extra: list[str]):
        args, report_args = publisher.parse_args(["--project", "GENEVA", "--age", "30天", *extra])
        return args, report_args

    def test_default_idempotency_key_is_short_and_target_aware(self) -> None:
        first_args, _ = self.parse(["--chat-id", "oc_first"])
        second_args, _ = self.parse(["--chat-id", "oc_second"])
        report_path = Path("reports/geneva-stale-jira.md")
        doc_url = "https://zepp.feishu.cn/docx/JalBdZotKoif3WxY33ncL3kLnth"

        first_key = publisher.default_idempotency_key(first_args, doc_url, report_path)
        second_key = publisher.default_idempotency_key(second_args, doc_url, report_path)

        self.assertLessEqual(len(first_key), publisher.MAX_IDEMPOTENCY_KEY_LEN)
        self.assertLessEqual(len(second_key), publisher.MAX_IDEMPOTENCY_KEY_LEN)
        self.assertNotEqual(first_key, second_key)

    def test_long_manual_idempotency_key_is_shortened(self) -> None:
        args, _ = self.parse(["--chat-id", "oc_xxx", "--idempotency-key", "x" * 200])

        key = publisher.effective_idempotency_key(
            args,
            "https://zepp.feishu.cn/docx/JalBdZotKoif3WxY33ncL3kLnth",
            Path("reports/geneva-stale-jira.md"),
        )

        self.assertLessEqual(len(key), publisher.MAX_IDEMPOTENCY_KEY_LEN)
        self.assertTrue(key.startswith("active-jira-report-manual-"))

    def test_build_message_cmd_can_target_user(self) -> None:
        args, _ = self.parse(["--user-id", "ou_user"])

        cmd = publisher.build_message_cmd(
            args,
            "lark-cli",
            Path("reports/geneva-stale-jira.md"),
            "https://zepp.feishu.cn/docx/JalBdZotKoif3WxY33ncL3kLnth",
        )

        self.assertIn("--user-id", cmd)
        self.assertIn("ou_user", cmd)
        self.assertNotIn("--chat-id", cmd)

    def test_report_input_rejects_forwarded_generator_options(self) -> None:
        args, report_args = self.parse(["--report-input", "report.md", "--comments", "top"])

        with self.assertRaises(publisher.PublishError):
            publisher.validate_forwarded_args(args, report_args)


if __name__ == "__main__":
    unittest.main()
