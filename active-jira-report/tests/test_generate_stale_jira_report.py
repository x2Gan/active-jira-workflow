from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_stale_jira_report.py"
SPEC = importlib.util.spec_from_file_location("generate_stale_jira_report", SCRIPT)
assert SPEC is not None
reporter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = reporter
SPEC.loader.exec_module(reporter)


class StaleJiraReportTests(unittest.TestCase):
    def test_dedupe_issues_uses_top_level_key_candidates(self) -> None:
        issues = [
            {"key": "GENEVA-1", "fields": {"summary": "first"}},
            {"key": "GENEVA-1", "fields": {"summary": "duplicate"}},
            {"issueKey": "GENEVA-2", "fields": {"summary": "second"}},
            {"id": "807408", "fields": {"summary": "third"}},
        ]

        deduped = reporter.dedupe_issues(issues)

        self.assertEqual([reporter.issue_key(issue) for issue in deduped], ["GENEVA-1", "GENEVA-2", "807408"])

    def test_enrich_issue_detail_uses_top_level_key_for_view_raw(self) -> None:
        called: list[list[str]] = []
        original_run_command = reporter.run_command

        def fake_run_command(cmd: list[str]) -> str:
            called.append(cmd)
            return '{"key":"GENEVA-1475","fields":{"customfield_11801":{"value":"Team A"}}}'

        reporter.run_command = fake_run_command
        try:
            enriched = reporter.enrich_issue_detail("jira", {"key": "GENEVA-1475", "fields": {}}, None)
        finally:
            reporter.run_command = original_run_command

        self.assertEqual(enriched["fields"]["customfield_11801"]["value"], "Team A")
        self.assertEqual(called, [["jira", "issue", "view", "GENEVA-1475", "--raw"]])

    def test_report_groups_all_issues_by_team(self) -> None:
        query_time = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
        raw_issues = [
            {
                "key": "GENEVA-1",
                "fields": {
                    "created": "2026-04-01T10:00:00.000+0800",
                    "assignee": {"displayName": "Alice"},
                    "status": {"name": "Open"},
                    "summary": "first",
                    "customfield_10401": {"value": "P1"},
                    "customfield_11801": {"value": "Team A"},
                },
            },
            {
                "key": "GENEVA-2",
                "fields": {
                    "created": "2026-04-02T10:00:00.000+0800",
                    "assignee": {"displayName": "Bob"},
                    "status": {"name": "Open"},
                    "summary": "second",
                    "customfield_10401": {"value": "P2"},
                    "customfield_11801": {"value": "Team B"},
                },
            },
        ]
        rows = [
            reporter.issue_to_report_issue(issue, query_time, timezone.utc, reporter.SEVERITY_COLUMNS, reporter.TEAM_FIELDS, 80)
            for issue in raw_issues
        ]

        report = reporter.build_report(
            rows,
            "GENEVA",
            "1w",
            query_time,
            "report command",
            "data command",
            "project = GENEVA",
            1,
            "comment policy",
            False,
            5,
        )

        self.assertIn("### " + "归属Team" + "\uff1aTeam A", report)
        self.assertIn("### " + "归属Team" + "\uff1aTeam B", report)
        self.assertIn("| 1 | GENEVA-1 | P1 |", report)
        self.assertIn("| 2 | GENEVA-2 | P2 |", report)
        self.assertIn("归属Team" + "来源: fields.customfield_11801", report)


if __name__ == "__main__":
    unittest.main()
