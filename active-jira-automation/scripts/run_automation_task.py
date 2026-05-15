#!/usr/bin/env python3
"""Shared runner for active-jira-automation tasks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Protocol


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from jira_query_runtime import (  # noqa: E402
    QueryWindow,
    build_final_jql,
    checkpoint_update_payload,
    compute_query_window,
    format_datetime,
)
from lark_delivery_runtime import LarkDeliveryRuntime  # noqa: E402
from llm_summary_runtime import LLMSummaryRuntime  # noqa: E402
from scenario_registry import ScenarioRegistry, ScenarioRegistryError, ScenarioSpec, default_registry  # noqa: E402
from task_store import DEFAULT_DATA_ROOT, TaskStore, TaskStoreError, read_json, write_json  # noqa: E402


class RunnerError(RuntimeError):
    """Raised when the shared automation runner cannot complete."""


class JiraClient(Protocol):
    def query(self, query: Any, window: QueryWindow, task: dict[str, Any]) -> list[Any]:
        """Return Jira query hits, preferably key plus window identity fields."""


class SummaryRuntime(Protocol):
    def summarize(self, matches: list[dict[str, Any]], task: dict[str, Any], scenario: ScenarioSpec) -> Any:
        """Return scenario-controlled summaries for matched records."""


class DeliveryRuntime(Protocol):
    def deliver(
        self,
        cards: list[dict[str, Any]],
        target: dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Deliver cards to the requested target."""


@dataclass
class RunnerDependencies:
    store: TaskStore
    registry: ScenarioRegistry
    jira_client: JiraClient
    summary_runtime: SummaryRuntime
    delivery_runtime: DeliveryRuntime


class UnconfiguredJiraClient:
    def query(self, query: Any, window: QueryWindow, task: dict[str, Any]) -> list[Any]:
        raise RunnerError("jira_client is not configured")


def extract_issue_items(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("issues", "data", "values"):
            value = raw.get(key)
            if isinstance(value, list):
                return value
        if "key" in raw:
            return [raw]
    return []


def query_hit_from_issue(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else raw
    key = raw.get("key") or raw.get("issue_key") or fields.get("key")
    hit = {"key": key}
    created = raw.get("created_at") or raw.get("created") or fields.get("created")
    updated = raw.get("updated_at") or raw.get("updated") or fields.get("updated")
    if created:
        hit["created_at"] = created
    if updated:
        hit["updated_at"] = updated
    return hit


def default_command_runner(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RunnerError(f"command failed with exit code {proc.returncode}: {err}")
    return proc.stdout


class JiraCliClient:
    """Jira client backed by the local active-jira/jira-cli capability."""

    def __init__(self, *, jira_bin: str = "jira", command_runner: Callable[[list[str]], str] | None = None) -> None:
        self.jira_bin = jira_bin
        self.command_runner = command_runner or default_command_runner
        self.calls: list[list[str]] = []

    def _run_json(self, cmd: list[str]) -> Any:
        self.calls.append(cmd)
        output = self.command_runner(cmd).strip()
        if not output:
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise RunnerError(f"could not parse jira-cli JSON output: {exc}") from exc

    def query(self, query: Any, window: QueryWindow, task: dict[str, Any]) -> list[Any]:
        if not isinstance(query, str) or not query.strip():
            raise RunnerError("jira query must be a non-empty JQL string")
        raw = self._run_json([self.jira_bin, "issue", "list", "--raw", "-q", query])
        return [hit for hit in (query_hit_from_issue(item) for item in extract_issue_items(raw)) if hit.get("key")]

    def fetch_details(self, issue_keys: list[str], task: dict[str, Any]) -> list[Any]:
        details: list[Any] = []
        for key in issue_keys:
            raw = self._run_json([self.jira_bin, "issue", "view", key, "--raw"])
            items = extract_issue_items(raw)
            details.append(items[0] if items else raw)
        return details


class FixtureJiraClient:
    """Local Jira client for deterministic dry-run and tests.

    The fixture may be either a JSON list of issues, {"issues": [...]}, or
    {"queries": [{"contains": "...", "issues": [...]}]} for simple JQL-based
    routing without requiring a real Jira connection.
    """

    def __init__(self, fixture: Any) -> None:
        self.fixture = fixture
        self.calls: list[Any] = []
        self.detail_calls: list[list[str]] = []

    @classmethod
    def from_file(cls, path: str | Path) -> "FixtureJiraClient":
        fixture_path = Path(path)
        try:
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RunnerError(f"fixture file not found: {fixture_path}") from exc
        except json.JSONDecodeError as exc:
            raise RunnerError(f"invalid fixture JSON: {fixture_path}: {exc}") from exc
        return cls(fixture)

    def query(self, query: Any, window: QueryWindow, task: dict[str, Any]) -> list[Any]:
        self.calls.append(query)
        fixture = self.fixture
        if isinstance(fixture, list):
            return fixture
        if not isinstance(fixture, dict):
            raise RunnerError("fixture JSON must be a list or object")
        if isinstance(fixture.get("issues"), list):
            return fixture["issues"]
        if isinstance(fixture.get("query_hits"), list):
            return fixture["query_hits"]
        if isinstance(fixture.get("queries"), list):
            query_text = query if isinstance(query, str) else json.dumps(query, ensure_ascii=False, sort_keys=True)
            for candidate in fixture["queries"]:
                if not isinstance(candidate, dict):
                    continue
                contains = candidate.get("contains")
                if isinstance(contains, str) and contains in query_text:
                    issues = candidate.get("issues", [])
                    if "query_hits" in candidate:
                        issues = candidate.get("query_hits", [])
                    if not isinstance(issues, list):
                        raise RunnerError("fixture query issues must be a list")
                    return issues
            return []
        raise RunnerError("fixture JSON must contain issues or queries")

    def fetch_details(self, issue_keys: list[str], task: dict[str, Any]) -> list[Any]:
        self.detail_calls.append(list(issue_keys))
        fixture = self.fixture
        if not isinstance(fixture, dict):
            return []
        details = fixture.get("details")
        if isinstance(details, dict):
            return [details[key] for key in issue_keys if key in details]
        if isinstance(details, list):
            details_by_key = {_issue_key(item): item for item in details if isinstance(item, dict)}
            return [details_by_key[key] for key in issue_keys if key in details_by_key]
        issues = fixture.get("issues")
        if isinstance(issues, list):
            details_by_key = {_issue_key(item): item for item in issues if isinstance(item, dict)}
            return [details_by_key[key] for key in issue_keys if key in details_by_key]
        return []


def load_runtime_state(store: TaskStore, task_id: str) -> dict[str, Any]:
    path = store.paths_for(task_id).runtime
    if not path.exists():
        return {}
    return read_json(path)


def update_task_checkpoint(store: TaskStore, task: dict[str, Any], checkpoint: str) -> dict[str, Any]:
    updated = {**task, "last_checkpoint": checkpoint}
    write_json(store.paths_for(task["task_id"]).definition, updated)
    return updated


def call_query_builder(scenario: ScenarioSpec, task: dict[str, Any], window: QueryWindow) -> Any:
    if not callable(scenario.query_builder):
        return build_final_jql(task, window)
    return scenario.query_builder(task, window)


def normalize_results(scenario: ScenarioSpec, raw_results: list[Any], task: dict[str, Any], window: QueryWindow) -> list[dict[str, Any]]:
    if not callable(scenario.result_normalizer):
        raise RunnerError(f"scenario result_normalizer is not callable: {scenario.scenario_key}")
    normalized = scenario.result_normalizer(raw_results, task, window)
    if not isinstance(normalized, list):
        raise RunnerError("scenario result_normalizer must return a list")
    if not all(isinstance(item, dict) for item in normalized):
        raise RunnerError("scenario result_normalizer must return dictionaries")
    return normalized


def _issue_key(record: Any) -> str:
    if not isinstance(record, dict):
        return ""
    value = record.get("key") or record.get("issue_key")
    if not value and isinstance(record.get("fields"), dict):
        value = record["fields"].get("key")
    return str(value) if value not in (None, "") else ""


def fetch_issue_details(jira_client: JiraClient, issue_keys: list[str], task: dict[str, Any]) -> list[Any]:
    fetcher = getattr(jira_client, "fetch_details", None)
    if not callable(fetcher) or not issue_keys:
        return []
    details = fetcher(issue_keys, task)
    if not isinstance(details, list):
        raise RunnerError("jira_client.fetch_details must return a list")
    return details


def enrich_matches(
    scenario: ScenarioSpec,
    matches: list[dict[str, Any]],
    jira_client: JiraClient,
    task: dict[str, Any],
    window: QueryWindow,
) -> list[dict[str, Any]]:
    issue_keys = [_issue_key(match) for match in matches]
    issue_keys = [key for key in issue_keys if key]
    raw_details = fetch_issue_details(jira_client, issue_keys, task)
    if not raw_details:
        return matches

    normalized_details = normalize_results(scenario, raw_details, task, window)
    details_by_key = {_issue_key(detail): detail for detail in normalized_details}
    enriched: list[dict[str, Any]] = []
    for match in matches:
        key = _issue_key(match)
        detail = details_by_key.get(key)
        if detail is None:
            enriched.append(match)
            continue
        identity = match.get("_identity")
        merged = {**match, **detail}
        if identity:
            merged["_identity"] = identity
        enriched.append(merged)
    return enriched


def identity_for(scenario: ScenarioSpec, match: dict[str, Any], task: dict[str, Any]) -> str:
    if not callable(scenario.match_identity):
        raise RunnerError(f"scenario match_identity is not callable: {scenario.scenario_key}")
    identity = scenario.match_identity(match, task)
    if not isinstance(identity, str) or not identity.strip():
        raise RunnerError("scenario match_identity must return a non-empty string")
    return identity


def render_cards(
    scenario: ScenarioSpec,
    matches: list[dict[str, Any]],
    summaries: Any,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    if not callable(scenario.renderer):
        raise RunnerError(f"scenario renderer is not callable: {scenario.scenario_key}")
    cards = scenario.renderer(matches, summaries, task)
    if not isinstance(cards, list):
        raise RunnerError("scenario renderer must return a list")
    if not all(isinstance(card, dict) for card in cards):
        raise RunnerError("scenario renderer must return card dictionaries")
    return cards


def filter_new_matches(
    scenario: ScenarioSpec,
    normalized: list[dict[str, Any]],
    task: dict[str, Any],
    runtime_state: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    known = set(runtime_state.get("delivered_identities") or [])
    seen_this_run: set[str] = set()
    fresh: list[dict[str, Any]] = []
    identities: list[str] = []
    for match in normalized:
        identity = identity_for(scenario, match, task)
        if identity in known or identity in seen_this_run:
            continue
        match["_identity"] = identity
        seen_this_run.add(identity)
        fresh.append(match)
        identities.append(identity)
    return fresh, identities


def apply_notify_limit(matches: list[dict[str, Any]], task: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    notify_policy = task.get("notify_policy") if isinstance(task.get("notify_policy"), dict) else {}
    try:
        limit = int(notify_policy.get("max_issues_per_run", len(matches)))
    except (TypeError, ValueError) as exc:
        raise RunnerError("notify_policy.max_issues_per_run must be an integer") from exc
    if limit <= 0:
        raise RunnerError("notify_policy.max_issues_per_run must be positive")
    limited = matches[:limit]
    return limited, max(0, len(matches) - len(limited))


def run_task(
    task_selector: str,
    deps: RunnerDependencies,
    *,
    dry_run: bool = False,
    current_time: Any = None,
) -> dict[str, Any]:
    task = deps.store.resolve_task(task_selector, include_deleted=False)
    if task.get("status") != "enabled":
        raise RunnerError(f"task is not enabled: {task['task_id']} ({task.get('status')})")

    scenario = deps.registry.get(task["scenario_key"])
    runtime_state = load_runtime_state(deps.store, task["task_id"])
    window = compute_query_window(task, runtime_state, current_time=current_time)
    try:
        query = call_query_builder(scenario, task, window)
        raw_results = deps.jira_client.query(query, window, task)
        normalized = normalize_results(scenario, raw_results, task, window)
        matches, fresh_identities = filter_new_matches(scenario, normalized, task, runtime_state)
        matches, skipped_by_limit = apply_notify_limit(matches, task)
        delivered_identities = fresh_identities[: len(matches)]
        matches = enrich_matches(scenario, matches, deps.jira_client, task, window)

        checkpoint_payload = checkpoint_update_payload(window)
        if not matches:
            if dry_run:
                return {
                    "task_id": task["task_id"],
                    "scenario_key": scenario.scenario_key,
                    "status": "success",
                    "match_count": 0,
                    "delivery_count": 0,
                    "dry_run": True,
                    "window": window.as_payload(),
                    "checkpoint_candidate": checkpoint_payload["last_checkpoint"],
                    "skipped_by_limit": 0,
                }
            runtime = deps.store.write_runtime_state(
                task["task_id"],
                {
                    **checkpoint_payload,
                    "last_run_at": format_datetime(window.query_end),
                    "last_run_status": "success",
                    "last_match_count": 0,
                    "last_delivery_count": 0,
                    "last_error": None,
                },
            )
            update_task_checkpoint(deps.store, task, checkpoint_payload["last_checkpoint"])
            deps.store.append_log(task["task_id"], {"event": "run_finished", "status": "success", "match_count": 0})
            return {
                "task_id": task["task_id"],
                "scenario_key": scenario.scenario_key,
                "status": "success",
                "match_count": 0,
                "delivery_count": 0,
                "dry_run": dry_run,
                "window": window.as_payload(),
                "runtime": runtime,
                "skipped_by_limit": 0,
            }

        summaries = deps.summary_runtime.summarize(matches, task, scenario)
        cards = render_cards(scenario, matches, summaries, task)
        delivery_result = deps.delivery_runtime.deliver(
            cards,
            {"chat_id": task["target_chat_id"], "chat_name": task.get("target_chat_name")},
            dry_run=dry_run,
        )
        if dry_run:
            return {
                "task_id": task["task_id"],
                "scenario_key": scenario.scenario_key,
                "status": "success",
                "match_count": len(matches),
                "delivery_count": 0,
                "dry_run": True,
                "window": window.as_payload(),
                "checkpoint_candidate": checkpoint_payload["last_checkpoint"],
                "delivery_result": delivery_result,
                "skipped_by_limit": skipped_by_limit,
            }
        previous_identities = list(runtime_state.get("delivered_identities") or [])
        next_identities = previous_identities + delivered_identities
        delivery_count = int(delivery_result.get("sent_count", len(cards) if not dry_run else 0))
        runtime = deps.store.write_runtime_state(
            task["task_id"],
            {
                **checkpoint_payload,
                "last_run_at": format_datetime(window.query_end),
                "last_run_status": "success",
                "last_match_count": len(matches),
                "last_delivery_count": delivery_count,
                "last_error": None,
                "delivered_identities": next_identities,
                "last_delivery_result": delivery_result,
                "skipped_by_limit": skipped_by_limit,
            },
        )
        update_task_checkpoint(deps.store, task, checkpoint_payload["last_checkpoint"])
        deps.store.append_log(
            task["task_id"],
            {
                "event": "run_finished",
                "status": "success",
                "match_count": len(matches),
                "delivery_count": delivery_count,
                "skipped_by_limit": skipped_by_limit,
                "dry_run": dry_run,
            },
        )
        return {
            "task_id": task["task_id"],
            "scenario_key": scenario.scenario_key,
            "status": "success",
            "match_count": len(matches),
            "delivery_count": delivery_count,
            "dry_run": dry_run,
            "window": window.as_payload(),
            "delivery_result": delivery_result,
            "runtime": runtime,
            "skipped_by_limit": skipped_by_limit,
        }
    except Exception as exc:
        error_message = str(exc)
        deps.store.write_runtime_state(
            task["task_id"],
            {
                "last_run_at": format_datetime(window.query_end),
                "last_run_status": "error",
                "last_error": error_message,
            },
        )
        deps.store.append_log(
            task["task_id"],
            {"event": "run_finished", "status": "error", "error": error_message, "dry_run": dry_run},
        )
        if isinstance(exc, RunnerError):
            raise
        raise RunnerError(f"task execution failed: {error_message}") from exc


def build_default_dependencies(data_root: str | None = None) -> RunnerDependencies:
    return RunnerDependencies(
        store=TaskStore(data_root or DEFAULT_DATA_ROOT),
        registry=default_registry(),
        jira_client=UnconfiguredJiraClient(),
        summary_runtime=LLMSummaryRuntime(),
        delivery_runtime=LarkDeliveryRuntime(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an active-jira-automation task through the shared runner.")
    parser.add_argument("task", help="Task ID or unique task name.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT), help="Task data root.")
    parser.add_argument("--dry-run", action="store_true", help="Render and validate without real delivery.")
    parser.add_argument("--fixture-json", help="Read Jira query results from a local fixture JSON file.")
    parser.add_argument("--jira-bin", help="Use local jira-cli binary for query hits and detail enrichment.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    deps = build_default_dependencies(args.data_root)
    if args.fixture_json:
        deps.jira_client = FixtureJiraClient.from_file(args.fixture_json)
    elif args.jira_bin:
        deps.jira_client = JiraCliClient(jira_bin=args.jira_bin)
    try:
        result = run_task(args.task, deps, dry_run=args.dry_run)
    except (RunnerError, TaskStoreError, ScenarioRegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
