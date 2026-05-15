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
FIXTURE_FILE = Path(__file__).resolve().parent / "fixtures" / "jira_query_results.json"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_automation_task", RUNNER_SCRIPT)
assert RUNNER_SPEC is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
sys.modules[RUNNER_SPEC.name] = runner
RUNNER_SPEC.loader.exec_module(runner)

from scenario_registry import ScenarioRegistry, ScenarioSpec  # noqa: E402
from jira_query_runtime import build_final_jql, match_identity_for  # noqa: E402
from task_store import TaskNotFoundError, TaskStore  # noqa: E402


def payload(scenario_key: str = "jira-scheduled-query-alert") -> dict[str, object]:
    return {
        "task_name": "Geneva P0 Bug Alert",
        "scenario_key": scenario_key,
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
    def query_builder(task: dict[str, object], window: object) -> str:
        return build_final_jql(task, window)

    def normalizer(raw_results: list[dict[str, object]], task: dict[str, object], window: object) -> list[dict[str, object]]:
        if broken_normalizer:
            raise ValueError("scenario normalize failed")
        return list(raw_results)

    def identity(match: dict[str, object], task: dict[str, object]) -> str:
        return match_identity_for(task, match)

    def renderer(matches: list[dict[str, object]], summaries: list[dict[str, object]], task: dict[str, object]) -> list[dict[str, object]]:
        return [{"key": match["key"], "summary": summary} for match, summary in zip(matches, summaries)]

    return ScenarioSpec(
        scenario_key="jira-scheduled-query-alert",
        display_name="Jira 定时查询并提醒",
        trigger_examples=("alert me",),
        config_schema={"project": {"required": True}},
        defaulting_rules="default",
        query_builder=query_builder,
        result_normalizer=normalizer,
        match_identity=identity,
        llm_policy="on-match-only",
        llm_output_schema={"symptom_summary": "string", "impact_summary": "string"},
        message_template_key="lark-jira-query-alert-card-v1",
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
            self.assertEqual(
                deps.jira_client.calls[0],
                '(project = GENEVA AND issuetype = Bug AND "Severity" = P0) '
                'AND created >= "2026-05-14T07:55:00Z" AND created < "2026-05-14T09:00:00Z" '
                "ORDER BY created ASC",
            )

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

    def test_updated_mode_dedupes_by_updated_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            results = [{"key": "GENEVA-1", "updated_at": "2026-05-14T08:30:00Z", "summary": "first"}]
            deps, _summary, _delivery = deps_for(tmpdir, results)
            task = deps.store.get_task("task-1")
            task["window_mode"] = "updated"
            deps.store.update_status("task-1", "enabled")
            runner.write_json(deps.store.paths_for("task-1").definition, task)

            runner.run_task(
                "task-1",
                deps,
                current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
            )

            runtime = deps.store.read_runtime_state("task-1")
            self.assertEqual(runtime["delivered_identities"], ["task-1:GENEVA-1:2026-05-14T08:30:00Z"])
            self.assertIn("updated >=", deps.jira_client.calls[0])

    def test_snapshot_mode_dedupes_by_base_jql_hash_without_window_jql(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            results = [{"key": "GENEVA-1", "summary": "first"}]
            deps, summary, delivery = deps_for(tmpdir, results)
            task = deps.store.get_task("task-1")
            task["window_mode"] = "snapshot"
            runner.write_json(deps.store.paths_for("task-1").definition, task)

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

            self.assertEqual(first["match_count"], 1)
            self.assertEqual(second["match_count"], 0)
            self.assertEqual(summary.calls, 1)
            self.assertEqual(delivery.calls, 1)
            self.assertEqual(deps.jira_client.calls[0], '(project = GENEVA AND issuetype = Bug AND "Severity" = P0)')

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

    def test_jira_query_failure_is_recorded_without_advancing_checkpoint(self) -> None:
        class FailingJiraClient:
            def query(self, query: object, window: object, task: dict[str, object]) -> list[dict[str, object]]:
                raise RuntimeError("jira unavailable")

        with tempfile.TemporaryDirectory() as tmpdir:
            deps, _summary, _delivery = deps_for(tmpdir, [])
            deps.jira_client = FailingJiraClient()

            with self.assertRaises(runner.RunnerError):
                runner.run_task(
                    "task-1",
                    deps,
                    current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
                )

            runtime = deps.store.read_runtime_state("task-1")
            task = deps.store.get_task("task-1")
            self.assertEqual(runtime["last_run_status"], "error")
            self.assertIn("jira unavailable", runtime["last_error"])
            self.assertIsNone(task["last_checkpoint"])

    def test_fixture_client_supports_no_match_single_match_and_multiple_matches(self) -> None:
        no_match = runner.FixtureJiraClient({"queries": [{"contains": "missing", "issues": [{"key": "NOPE"}]}]})
        single = runner.FixtureJiraClient({"issues": [{"key": "GENEVA-1"}]})
        multiple = runner.FixtureJiraClient([{"key": "GENEVA-1"}, {"key": "GENEVA-2"}])
        from_file = runner.FixtureJiraClient.from_file(FIXTURE_FILE)

        self.assertEqual(no_match.query("project = GENEVA", object(), {}), [])
        self.assertEqual(single.query("project = GENEVA", object(), {}), [{"key": "GENEVA-1"}])
        self.assertEqual(len(multiple.query("project = GENEVA", object(), {})), 2)
        self.assertEqual(len(from_file.query("project = GENEVA", object(), {})), 2)

    def test_notify_policy_limits_fixture_match_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            deps, summary, delivery = deps_for(
                tmpdir,
                [
                    {"key": "GENEVA-1", "created_at": "2026-05-14T08:30:00Z", "summary": "first"},
                    {"key": "GENEVA-2", "created_at": "2026-05-14T08:31:00Z", "summary": "second"},
                ],
            )
            task = deps.store.get_task("task-1")
            task["notify_policy"]["max_issues_per_run"] = 1
            runner.write_json(deps.store.paths_for("task-1").definition, task)

            result = runner.run_task(
                "task-1",
                deps,
                current_time=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
            )

            runtime = deps.store.read_runtime_state("task-1")
            self.assertEqual(result["match_count"], 1)
            self.assertEqual(result["skipped_by_limit"], 1)
            self.assertEqual(summary.calls, 1)
            self.assertEqual(delivery.calls, 1)
            self.assertEqual(len(runtime["delivered_identities"]), 2)

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
