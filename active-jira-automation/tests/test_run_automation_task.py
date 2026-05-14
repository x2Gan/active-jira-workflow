from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

RUNNER_SCRIPT = SCRIPTS_DIR / "run_automation_task.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_automation_task", RUNNER_SCRIPT)
assert RUNNER_SPEC is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)

from scenario_registry import ScenarioRegistry, ScenarioSpec  # noqa: E402
from task_store import TaskNotFoundError, TaskStore  # noqa: E402


def payload(scenario_key: str = "new-p0-bug-alert") -> dict[str, object]:
    return {
        "task_name": "Geneva P0 Bug Alert",
        "scenario_key": scenario_key,
        "project": "GENEVA",
        "query_rule": {"issue_type": "Bug", "severity": "P0"},
        "schedule_type": "recurring",
        "schedule_expr": "0 * * * *",
        "target_chat_id": "oc_123",
        "message_template_key": "lark-p0-bug-card-v1",
        "llm_policy": "on-match-only",
    }


class FakeJiraClient:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self.results = results
        self.calls: list[object] = []

    def query(self, query: object, window: object, task: dict[str, object]) -> list[dict[str, object]]:
        self.calls.append(query)
        return self.results


class FakeSummaryRuntime:
    def __init__(self) -> None:
        self.calls = 0

    def summarize(self, matches: list[dict[str, object]], task: dict[str, object], scenario: ScenarioSpec) -> list[dict[str, str]]:
        self.calls += 1
        return [{"symptom_summary": str(match["summary"]), "impact_summary": "impact"} for match in matches]


class FakeDeliveryRuntime:
    def __init__(self) -> None:
        self.calls = 0
        self.dry_runs: list[bool] = []

    def deliver(self, cards: list[dict[str, object]], target: dict[str, object], *, dry_run: bool = False) -> dict[str, object]:
        self.calls += 1
        self.dry_runs.append(dry_run)
        return {"sent_count": 0 if dry_run else len(cards), "target": target, "dry_run": dry_run}


def build_spec(*, broken_normalizer: bool = False) -> ScenarioSpec:
    def query_builder(task: dict[str, object], window: object) -> dict[str, object]:
        return {"project": task["project"], "window": window.as_payload()}

    def normalizer(raw_results: list[dict[str, object]], task: dict[str, object], window: object) -> list[dict[str, object]]:
        if broken_normalizer:
            raise ValueError("scenario normalize failed")
        return list(raw_results)

    def identity(match: dict[str, object], task: dict[str, object]) -> str:
        return f"{task['task_id']}:{match['key']}:{match['created_at']}"

    def renderer(matches: list[dict[str, object]], summaries: list[dict[str, object]], task: dict[str, object]) -> list[dict[str, object]]:
        return [{"key": match["key"], "summary": summary} for match, summary in zip(matches, summaries)]

    return ScenarioSpec(
        scenario_key="new-p0-bug-alert",
        display_name="新增 P0 BUG Jira 定时提醒",
        trigger_examples=("alert me",),
        config_schema={"project": {"required": True}},
        defaulting_rules="default",
        query_builder=query_builder,
        result_normalizer=normalizer,
        match_identity=identity,
        llm_policy="on-match-only",
        llm_output_schema={"symptom_summary": "string", "impact_summary": "string"},
        message_template_key="lark-p0-bug-card-v1",
        renderer=renderer,
        delivery_policy="one card per match",
        acceptance_cases=("runs",),
    )


def deps_for(tmpdir: str, jira_results: list[dict[str, object]], *, broken_normalizer: bool = False) -> tuple[runner.RunnerDependencies, FakeSummaryRuntime, FakeDeliveryRuntime]:
    store = TaskStore(tmpdir)
    store.create_task(payload(), task_id="task-1", now=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc))
    registry = ScenarioRegistry()
    registry.register(build_spec(broken_normalizer=broken_normalizer))
    summary = FakeSummaryRuntime()
    delivery = FakeDeliveryRuntime()
    deps = runner.RunnerDependencies(
        store=store,
        registry=registry,
        jira_client=FakeJiraClient(jira_results),
        summary_runtime=summary,
        delivery_runtime=delivery,
    )
    return deps, summary, delivery


class RunAutomationTaskTests(unittest.TestCase):
    def test_no_match_updates_checkpoint_without_summary_or_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            deps, summary, delivery = deps_for(tmpdir, [])

            result = runner.run_task(
                "task-1",
                deps,
                current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
            )

            runtime = deps.store.read_runtime_state("task-1")
            task = deps.store.get_task("task-1")
            self.assertEqual(result["match_count"], 0)
            self.assertEqual(summary.calls, 0)
            self.assertEqual(delivery.calls, 0)
            self.assertEqual(runtime["last_checkpoint"], "2026-05-14T09:00:00Z")
            self.assertEqual(task["last_checkpoint"], "2026-05-14T09:00:00Z")

    def test_match_path_summarizes_renders_delivers_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            results = [{"key": "GENEVA-1", "created_at": "2026-05-14T08:30:00Z", "summary": "first"}]
            deps, summary, delivery = deps_for(tmpdir, results)

            first = runner.run_task(
                "task-1",
                deps,
                current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
            )
            second = runner.run_task(
                "task-1",
                deps,
                current_time=datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc),
            )

            runtime = deps.store.read_runtime_state("task-1")
            self.assertEqual(first["match_count"], 1)
            self.assertEqual(first["delivery_count"], 1)
            self.assertEqual(second["match_count"], 0)
            self.assertEqual(summary.calls, 1)
            self.assertEqual(delivery.calls, 1)
            self.assertEqual(len(runtime["delivered_identities"]), 1)

    def test_dry_run_does_not_record_delivered_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            results = [{"key": "GENEVA-1", "created_at": "2026-05-14T08:30:00Z", "summary": "first"}]
            deps, _summary, delivery = deps_for(tmpdir, results)

            result = runner.run_task(
                "task-1",
                deps,
                dry_run=True,
                current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
            )

            task = deps.store.get_task("task-1")
            self.assertTrue(result["dry_run"])
            self.assertEqual(delivery.dry_runs, [True])
            self.assertFalse(deps.store.paths_for("task-1").runtime.exists())
            self.assertIsNone(task["last_checkpoint"])

    def test_unknown_task_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            deps, _summary, _delivery = deps_for(tmpdir, [])

            with self.assertRaises(TaskNotFoundError):
                runner.run_task("missing", deps)

    def test_unknown_scenario_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(tmpdir)
            store.create_task(payload("missing-scenario"), task_id="task-1")
            deps = runner.RunnerDependencies(
                store=store,
                registry=ScenarioRegistry(),
                jira_client=FakeJiraClient([]),
                summary_runtime=FakeSummaryRuntime(),
                delivery_runtime=FakeDeliveryRuntime(),
            )

            with self.assertRaises(runner.ScenarioRegistryError):
                runner.run_task("task-1", deps)

    def test_scenario_execution_exception_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            deps, _summary, _delivery = deps_for(
                tmpdir,
                [{"key": "GENEVA-1", "created_at": "2026-05-14T08:30:00Z", "summary": "first"}],
                broken_normalizer=True,
            )

            with self.assertRaises(runner.RunnerError):
                runner.run_task(
                    "task-1",
                    deps,
                    current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
                )

            runtime = deps.store.read_runtime_state("task-1")
            task = deps.store.get_task("task-1")
            self.assertEqual(runtime["last_run_status"], "error")
            self.assertIn("scenario normalize failed", runtime["last_error"])
            self.assertIsNone(task["last_checkpoint"])


if __name__ == "__main__":
    unittest.main()
