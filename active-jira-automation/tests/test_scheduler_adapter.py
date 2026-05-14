from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scheduler_adapter.py"
SPEC = importlib.util.spec_from_file_location("scheduler_adapter", SCRIPT)
assert SPEC is not None
scheduler_adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = scheduler_adapter
SPEC.loader.exec_module(scheduler_adapter)


def job() -> object:
    return scheduler_adapter.SchedulerJob(
        task_id="task-1",
        schedule_type="recurring",
        schedule_expr="0 * * * *",
        runner_command=["python", "run_automation_task.py", "task-1"],
    )


class SchedulerAdapterTests(unittest.TestCase):
    def test_in_memory_adapter_lifecycle(self) -> None:
        adapter = scheduler_adapter.InMemorySchedulerAdapter()

        created = adapter.create(job())
        paused = adapter.pause(created.scheduler_job_id)
        resumed = adapter.resume(created.scheduler_job_id)
        deleted = adapter.delete(created.scheduler_job_id)
        status = adapter.get_status(created.scheduler_job_id)

        self.assertEqual(created.scheduler_job_id, "mock-task-1")
        self.assertEqual(created.status, "enabled")
        self.assertEqual(paused.status, "paused")
        self.assertEqual(resumed.status, "enabled")
        self.assertEqual(deleted.status, "deleted")
        self.assertEqual(status.status, "deleted")

    def test_in_memory_adapter_wraps_unknown_job_as_adapter_error(self) -> None:
        adapter = scheduler_adapter.InMemorySchedulerAdapter()

        with self.assertRaises(scheduler_adapter.SchedulerAdapterError):
            adapter.pause("missing")

    def test_openclaw_placeholder_requires_client(self) -> None:
        adapter = scheduler_adapter.OpenclawSchedulerAdapter()

        with self.assertRaises(scheduler_adapter.SchedulerAdapterError):
            adapter.create(job())

    def test_openclaw_adapter_normalizes_client_dict_result(self) -> None:
        class Client:
            def create(self, payload: object) -> dict[str, str]:
                return {"id": "openclaw-1", "status": "enabled"}

        adapter = scheduler_adapter.OpenclawSchedulerAdapter(Client())

        result = adapter.create(job())

        self.assertEqual(result.scheduler_job_id, "openclaw-1")
        self.assertEqual(result.status, "enabled")


if __name__ == "__main__":
    unittest.main()
