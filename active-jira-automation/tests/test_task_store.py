from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "task_store.py"
SPEC = importlib.util.spec_from_file_location("task_store", SCRIPT)
assert SPEC is not None
task_store = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = task_store
SPEC.loader.exec_module(task_store)


def sample_payload(name: str = "Geneva P0 Bug Alert") -> dict[str, object]:
    return {
        "task_name": name,
        "scenario_key": "jira-scheduled-query-alert",
        "project": "GENEVA",
        "filter_prompt": "每小时查询一次 GENEVA 新增的 P0 Bug",
        "query_spec": {
            "projects": ["GENEVA"],
            "clauses": [
                {"field": "issuetype", "op": "=", "value": "Bug"},
                {"field": "Severity", "op": "=", "value": "P0"},
            ],
        },
        "base_jql": 'project = GENEVA AND issuetype = Bug AND "Severity" = P0',
        "window_mode": "created",
        "lookback_minutes": 5,
        "notify_policy": {"mode": "per_issue", "max_issues_per_run": 20, "repeat_snapshot": False},
        "query_rule": {"issue_type": "Bug", "severity": "P0"},
        "schedule_type": "recurring",
        "schedule_expr": "0 * * * *",
        "target_chat_id": "oc_123",
        "message_template_key": "lark-jira-query-alert-card-v1",
        "llm_policy": "on-match-only",
    }


class TaskStoreTests(unittest.TestCase):
    def test_create_task_definition_uses_fixed_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = task_store.TaskStore(tmpdir)

            task = store.create_task(
                sample_payload(),
                task_id="geneva-p0-bug-alert",
                now=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
            )

            self.assertEqual(task["status"], "enabled")
            self.assertEqual(task["created_at"], "2026-05-14T08:00:00Z")
            self.assertTrue((Path(tmpdir) / "tasks" / "geneva-p0-bug-alert.json").exists())
            self.assertTrue((Path(tmpdir) / "runtime").is_dir())
            self.assertTrue((Path(tmpdir) / "logs").is_dir())

    def test_update_status_respects_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = task_store.TaskStore(tmpdir)
            store.create_task(sample_payload(), task_id="task-1")

            paused = store.update_status("task-1", "paused")
            resumed = store.update_status("task-1", "enabled")
            deleted = store.update_status("task-1", "deleted")

            self.assertEqual(paused["status"], "paused")
            self.assertEqual(resumed["status"], "enabled")
            self.assertEqual(deleted["status"], "deleted")
            with self.assertRaises(task_store.TaskNotFoundError):
                store.update_status("task-1", "enabled")

    def test_write_runtime_state_and_append_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = task_store.TaskStore(tmpdir)
            store.create_task(sample_payload(), task_id="task-1")

            runtime = store.write_runtime_state(
                "task-1",
                {
                    "last_run_at": "2026-05-14T08:00:00Z",
                    "last_run_status": "success",
                    "last_match_count": 2,
                    "last_delivery_count": 2,
                    "last_error": None,
                },
            )
            log_path = store.append_log("task-1", {"event": "run_finished", "match_count": 2})

            self.assertEqual(runtime["task_id"], "task-1")
            self.assertEqual(store.read_runtime_state("task-1")["last_match_count"], 2)
            self.assertEqual(log_path.parent, Path(tmpdir) / "logs" / "task-1")
            self.assertEqual(task_store.read_json(log_path)["event"], "run_finished")

    def test_duplicate_active_task_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = task_store.TaskStore(tmpdir)
            store.create_task(sample_payload(), task_id="task-1")

            with self.assertRaises(task_store.TaskConflictError):
                store.create_task(sample_payload(), task_id="task-2")

    def test_minimum_generalized_task_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = task_store.TaskStore(tmpdir)
            payload = sample_payload("General Query Alert")
            payload.pop("query_rule")

            task = store.create_task(payload, task_id="task-1")

            self.assertEqual(task["filter_prompt"], "每小时查询一次 GENEVA 新增的 P0 Bug")
            self.assertEqual(task["window_mode"], "created")
            self.assertEqual(task["lookback_minutes"], 5)

    def test_missing_base_jql_fails(self) -> None:
        payload = sample_payload()
        payload.pop("base_jql")

        with self.assertRaisesRegex(task_store.TaskValidationError, "base_jql"):
            task_store.validate_task_payload(payload)

    def test_invalid_window_mode_fails(self) -> None:
        payload = sample_payload()
        payload["window_mode"] = "recent"

        with self.assertRaisesRegex(task_store.TaskValidationError, "window_mode"):
            task_store.validate_task_payload(payload)

    def test_invalid_notify_policy_fails(self) -> None:
        payload = sample_payload()
        payload["notify_policy"] = {"mode": "per_issue", "max_issues_per_run": 0}

        with self.assertRaisesRegex(task_store.TaskValidationError, "max_issues_per_run"):
            task_store.validate_task_payload(payload)

    def test_legacy_task_lifecycle_does_not_require_new_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = task_store.TaskStore(tmpdir)
            legacy_task = {
                "task_id": "legacy-task",
                "task_name": "Legacy P0 Bug Alert",
                "scenario_key": "new-p0-bug-alert",
                "project": "GENEVA",
                "query_rule": {"issue_type": "Bug", "severity": "P0"},
                "schedule_type": "recurring",
                "schedule_expr": "0 * * * *",
                "target_chat_id": "oc_123",
                "message_template_key": "lark-p0-bug-card-v1",
                "llm_policy": "on-match-only",
                "status": "enabled",
                "created_at": "2026-05-14T08:00:00Z",
                "updated_at": "2026-05-14T08:00:00Z",
            }
            task_store.write_json(Path(tmpdir) / "tasks" / "legacy-task.json", legacy_task)

            paused = store.update_status("legacy-task", "paused")
            deleted = store.update_status("legacy-task", "deleted")

            self.assertEqual(paused["status"], "paused")
            self.assertEqual(deleted["status"], "deleted")


if __name__ == "__main__":
    unittest.main()
