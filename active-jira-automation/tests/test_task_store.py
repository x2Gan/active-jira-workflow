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


if __name__ == "__main__":
    unittest.main()
