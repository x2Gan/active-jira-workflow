from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SCRIPT = SCRIPTS_DIR / "scenarios" / "jira_scheduled_query_alert.py"
SPEC = importlib.util.spec_from_file_location("jira_scheduled_query_alert", SCRIPT)
assert SPEC is not None
scenario = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = scenario
SPEC.loader.exec_module(scenario)

from jira_query_runtime import compute_query_window  # noqa: E402


def task(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "task_id": "task-1",
        "task_name": "Generic Jira Alert",
        "project": "DEMO",
        "filter_prompt": "自定义 Jira 查询提醒",
        "query_spec": {},
        "base_jql": "project = DEMO",
        "window_mode": "created",
        "lookback_minutes": 5,
        "notify_policy": {"mode": "per_issue", "max_issues_per_run": 20, "repeat_snapshot": False},
        "created_at": "2026-05-14T08:00:00Z",
    }
    payload.update(overrides)
    return payload


def window(task_payload: dict[str, object]) -> object:
    return compute_query_window(
        task_payload,
        {},
        current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
    )


class JiraScheduledQueryAlertTests(unittest.TestCase):
    def test_query_builder_accepts_p0_bug_sample_as_task_configuration(self) -> None:
        task_payload = task(
            project="GENEVA",
            base_jql='project = GENEVA AND issuetype = Bug AND "Severity" = P0',
            filter_prompt="每小时查询一次 GENEVA 新增的 P0 Bug",
        )

        jql = scenario.query_builder(task_payload, window(task_payload))

        self.assertIn('project = GENEVA AND issuetype = Bug AND "Severity" = P0', jql)
        self.assertIn("created >=", jql)
        self.assertIn("ORDER BY created ASC", jql)

    def test_query_builder_accepts_open_blocker_sample(self) -> None:
        task_payload = task(
            base_jql='project = REL AND status = Open AND labels = "release-blocker"',
            window_mode="snapshot",
        )

        jql = scenario.query_builder(task_payload, window(task_payload))

        self.assertEqual(jql, '(project = REL AND status = Open AND labels = "release-blocker")')

    def test_query_builder_accepts_unassigned_updated_sample(self) -> None:
        task_payload = task(
            base_jql="project = DEMO AND assignee IS EMPTY",
            window_mode="updated",
        )

        jql = scenario.query_builder(task_payload, window(task_payload))

        self.assertIn("assignee IS EMPTY", jql)
        self.assertIn("updated >=", jql)
        self.assertIn("ORDER BY updated ASC", jql)

    def test_query_builder_accepts_label_sample(self) -> None:
        task_payload = task(base_jql='project = DEMO AND labels = "customer-escalation"')

        jql = scenario.query_builder(task_payload, window(task_payload))

        self.assertIn('labels = "customer-escalation"', jql)

    def test_result_normalizer_maps_jira_rest_fields(self) -> None:
        raw = [
            {
                "key": "DEMO-1",
                "fields": {
                    "summary": "Customer escalation",
                    "created": "2026-05-14T08:30:00Z",
                    "updated": "2026-05-14T08:45:00Z",
                    "status": {"name": "Open"},
                    "assignee": {"displayName": "Alice"},
                    "reporter": {"displayName": "Bob"},
                    "priority": {"name": "High"},
                    "customfield_10401": {"value": "P1"},
                    "fixVersions": [{"name": "2026.05"}],
                    "labels": ["customer-escalation"],
                    "components": [{"name": "Checkout"}],
                },
            }
        ]

        normalized = scenario.result_normalizer(raw, task(jira_base_url="https://jira.example.com"), window(task()))

        self.assertEqual(normalized[0]["key"], "DEMO-1")
        self.assertEqual(normalized[0]["summary"], "Customer escalation")
        self.assertEqual(normalized[0]["status"], "Open")
        self.assertEqual(normalized[0]["assignee"], "Alice")
        self.assertEqual(normalized[0]["reporter"], "Bob")
        self.assertEqual(normalized[0]["priority"], "High")
        self.assertEqual(normalized[0]["severity"], "P1")
        self.assertEqual(normalized[0]["fix_versions"], "2026.05")
        self.assertEqual(normalized[0]["labels"], "customer-escalation")
        self.assertEqual(normalized[0]["components"], "Checkout")
        self.assertEqual(normalized[0]["url"], "https://jira.example.com/browse/DEMO-1")

    def test_result_normalizer_uses_missing_field_fallbacks(self) -> None:
        normalized = scenario.result_normalizer([{"key": "DEMO-2"}], task(), window(task()))

        self.assertEqual(normalized[0]["summary"], "未命名 Jira")
        self.assertEqual(normalized[0]["status"], "未设置")
        self.assertEqual(normalized[0]["assignee"], "未设置")
        self.assertEqual(normalized[0]["severity"], "未设置")

    def test_match_identity_uses_window_mode(self) -> None:
        created_task = task(window_mode="created")
        updated_task = task(window_mode="updated")
        snapshot_task = task(window_mode="snapshot", base_jql="project = DEMO AND status = Open")

        self.assertEqual(
            scenario.match_identity({"key": "DEMO-1", "created_at": "2026-05-14T08:30:00Z"}, created_task),
            "task-1:DEMO-1:2026-05-14T08:30:00Z",
        )
        self.assertEqual(
            scenario.match_identity({"key": "DEMO-1", "updated_at": "2026-05-14T08:45:00Z"}, updated_task),
            "task-1:DEMO-1:2026-05-14T08:45:00Z",
        )
        self.assertRegex(
            scenario.match_identity({"key": "DEMO-1"}, snapshot_task),
            r"^task-1:DEMO-1:[a-f0-9]{16}$",
        )

    def test_renderer_returns_valid_card_per_match(self) -> None:
        cards = scenario.renderer(
            [{"key": "DEMO-1", "summary": "Customer escalation", "status": "Open", "url": "https://jira.example.com/browse/DEMO-1"}],
            [{"match_reason": "matches filter"}],
            task(),
        )

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["header"]["title"]["content"], "Generic Jira Alert")

    def test_module_does_not_hardcode_business_filter_values(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("GENEVA", source)
        self.assertNotIn("P0", source)
        self.assertNotIn("issuetype = Bug", source)


if __name__ == "__main__":
    unittest.main()
