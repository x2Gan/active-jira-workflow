from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "jira_query_runtime.py"
SPEC = importlib.util.spec_from_file_location("jira_query_runtime", SCRIPT)
assert SPEC is not None
jira_query_runtime = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = jira_query_runtime
SPEC.loader.exec_module(jira_query_runtime)


class JiraQueryRuntimeTests(unittest.TestCase):
    def test_first_run_uses_task_created_at_without_lookback_leading_edge(self) -> None:
        task = {
            "created_at": "2026-05-14T08:00:00Z",
            "query_rule": {"lookback_minutes": 5},
        }

        window = jira_query_runtime.compute_query_window(
            task,
            {},
            current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(jira_query_runtime.format_datetime(window.checkpoint), "2026-05-14T08:00:00Z")
        self.assertEqual(jira_query_runtime.format_datetime(window.query_start), "2026-05-14T07:55:00Z")
        self.assertEqual(jira_query_runtime.format_datetime(window.query_end), "2026-05-14T09:00:00Z")

    def test_first_run_can_use_explicit_initial_checkpoint(self) -> None:
        task = {
            "created_at": "2026-05-14T08:00:00Z",
            "initial_checkpoint": "2026-05-14T07:30:00Z",
            "query_rule": {},
        }

        window = jira_query_runtime.compute_query_window(
            task,
            {},
            current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(jira_query_runtime.format_datetime(window.checkpoint), "2026-05-14T07:30:00Z")

    def test_normal_resume_uses_runtime_checkpoint_and_lookback(self) -> None:
        task = {
            "created_at": "2026-05-14T08:00:00Z",
            "query_rule": {"lookback_minutes": 10},
        }
        runtime = {"last_checkpoint": "2026-05-14T09:00:00Z"}

        window = jira_query_runtime.compute_query_window(
            task,
            runtime,
            current_time=datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(jira_query_runtime.format_datetime(window.query_start), "2026-05-14T08:50:00Z")
        self.assertEqual(jira_query_runtime.format_datetime(window.query_end), "2026-05-14T10:00:00Z")

    def test_created_in_checkpoint_range_prevents_duplicates_from_lookback_overlap(self) -> None:
        window = jira_query_runtime.compute_query_window(
            {"created_at": "2026-05-14T08:00:00Z", "query_rule": {}},
            {"last_checkpoint": "2026-05-14T09:00:00Z"},
            current_time=datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(jira_query_runtime.created_in_checkpoint_range("2026-05-14T08:58:00Z", window))
        self.assertFalse(jira_query_runtime.created_in_checkpoint_range("2026-05-14T09:00:00Z", window))
        self.assertTrue(jira_query_runtime.created_in_checkpoint_range("2026-05-14T09:00:01Z", window))
        self.assertTrue(jira_query_runtime.created_in_checkpoint_range("2026-05-14T10:00:00Z", window))
        self.assertFalse(jira_query_runtime.created_in_checkpoint_range("2026-05-14T10:00:01Z", window))

    def test_checkpoint_update_payload_moves_checkpoint_to_query_end(self) -> None:
        window = jira_query_runtime.compute_query_window(
            {"created_at": "2026-05-14T08:00:00Z", "query_rule": {}},
            {},
            current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
        )

        payload = jira_query_runtime.checkpoint_update_payload(window)

        self.assertEqual(payload["last_checkpoint"], "2026-05-14T09:00:00Z")
        self.assertEqual(payload["idempotency_window"]["checkpoint"], "2026-05-14T08:00:00Z")


if __name__ == "__main__":
    unittest.main()
