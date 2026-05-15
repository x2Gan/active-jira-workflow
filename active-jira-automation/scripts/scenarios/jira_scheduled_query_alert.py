#!/usr/bin/env python3
"""Scenario adapter for generic scheduled Jira query alerts."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from jira_query_runtime import QueryWindow, build_final_jql, match_identity_for  # noqa: E402
from scenario_registry import ScenarioSpec  # noqa: E402
from templates.lark_jira_query_alert_card_v1 import render_cards  # noqa: E402


SCENARIO_KEY = "jira-scheduled-query-alert"
MESSAGE_TEMPLATE_KEY = "lark-jira-query-alert-card-v1"


CONFIG_SCHEMA = {
    "project": {"required": True, "type": "string"},
    "filter_prompt": {"required": True, "type": "string"},
    "query_spec": {"required": True, "type": "object"},
    "base_jql": {"required": True, "type": "string"},
    "window_mode": {"required": True, "enum": ["created", "updated", "snapshot"]},
    "lookback_minutes": {"required": True, "type": "integer", "minimum": 0},
    "notify_policy": {
        "required": True,
        "type": "object",
        "properties": {
            "mode": {"enum": ["per_issue", "batch_summary"]},
            "max_issues_per_run": {"type": "integer", "minimum": 1},
            "repeat_snapshot": {"type": "boolean"},
        },
    },
    "target_chat_id": {"required": True, "type": "string"},
}


DEFAULTING_RULES = {
    "window_mode": "created",
    "lookback_minutes": 5,
    "notify_policy": {
        "mode": "per_issue",
        "max_issues_per_run": 20,
        "repeat_snapshot": False,
    },
    "sort": {
        "created": "created ASC",
        "updated": "updated ASC",
    },
}


LLM_OUTPUT_SCHEMA = {
    "match_reason": "string",
    "problem_summary": "string",
    "risk_assessment": "string",
}


def query_builder(task: dict[str, Any], window: QueryWindow) -> str:
    return build_final_jql(task, window)


def _first_value(*values: Any, fallback: str = "未设置") -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return fallback


def _display_name(value: Any, *, fallback: str = "未设置") -> str:
    if isinstance(value, dict):
        return str(
            _first_value(
                value.get("displayName"),
                value.get("name"),
                value.get("value"),
                value.get("emailAddress"),
                fallback=fallback,
            )
        )
    if isinstance(value, list):
        names = [_display_name(item, fallback="") for item in value]
        names = [name for name in names if name]
        return ", ".join(names) if names else fallback
    return str(_first_value(value, fallback=fallback))


def _names(values: Any) -> str:
    if not isinstance(values, list):
        return _display_name(values)
    names = [_display_name(value, fallback="") for value in values]
    names = [name for name in names if name]
    return ", ".join(names) if names else "未设置"


def _field(fields: dict[str, Any], task: dict[str, Any], logical_name: str, *fallback_paths: str) -> Any:
    configured = task.get(f"{logical_name}_field") or task.get(f"{logical_name}_field_path")
    paths = [configured] if isinstance(configured, str) and configured.strip() else []
    paths.extend(fallback_paths)
    for path in paths:
        if not path:
            continue
        current: Any = fields
        for part in str(path).split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                current = None
                break
        if current not in (None, "", [], {}):
            return current
    return None


def _issue_url(raw: dict[str, Any], task: dict[str, Any], key: str) -> str:
    for field in ("url", "browse_url", "web_url"):
        value = raw.get(field)
        if isinstance(value, str) and value.strip():
            return value
    base_url = task.get("jira_base_url")
    if isinstance(base_url, str) and base_url.strip():
        return f"{base_url.rstrip('/')}/browse/{key}"
    return ""


def normalize_issue(raw: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else raw
    key = str(_first_value(raw.get("key"), raw.get("issue_key"), fields.get("key"), fallback="UNKNOWN"))
    severity = _field(fields, task, "severity", "severity", "Severity", "customfield_10401")
    priority = _field(fields, task, "priority", "priority")
    status = _field(fields, task, "status", "status")
    assignee = _field(fields, task, "assignee", "assignee")
    reporter = _field(fields, task, "reporter", "reporter")
    team = _field(
        fields,
        task,
        "team",
        "team",
        "Team",
        "team.name",
        "归属Team",
        "归属团队",
        "customfield_11801",
    )

    return {
        "key": key,
        "issue_key": key,
        "summary": str(_first_value(raw.get("summary"), fields.get("summary"), fallback="未命名 Jira")),
        "url": _issue_url(raw, task, key),
        "created_at": _first_value(raw.get("created_at"), raw.get("created"), fields.get("created"), fallback=""),
        "updated_at": _first_value(raw.get("updated_at"), raw.get("updated"), fields.get("updated"), fallback=""),
        "status": _display_name(status),
        "assignee": _display_name(assignee),
        "reporter": _display_name(reporter),
        "priority": _display_name(priority),
        "severity": _display_name(severity),
        "fix_versions": _names(_field(fields, task, "fix_versions", "fixVersions", "fix_versions")),
        "affects_versions": _names(_field(fields, task, "affects_versions", "versions", "affectsVersions", "affects_versions")),
        "team": _display_name(team),
        "labels": _names(_field(fields, task, "labels", "labels")),
        "components": _names(_field(fields, task, "components", "components")),
        "match_reason": str(_first_value(raw.get("match_reason"), task.get("filter_prompt"), fallback="命中当前查询条件")),
        "raw": raw,
    }


def result_normalizer(raw_results: list[Any], task: dict[str, Any], window: QueryWindow) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        normalized.append(normalize_issue(raw, task))
    return normalized


def match_identity(match: dict[str, Any], task: dict[str, Any]) -> str:
    return match_identity_for(task, match)


def renderer(matches: list[dict[str, Any]], summaries: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    return render_cards(matches, summaries, task)


def get_scenario_spec() -> ScenarioSpec:
    return ScenarioSpec(
        scenario_key=SCENARIO_KEY,
        display_name="Jira 定时查询并提醒",
        trigger_examples=(
            "每小时查询一次项目里新增的高优先级缺陷",
            "每天上午检查仍处于 Open 的 blocker",
            "每 30 分钟提醒最近有更新且 assignee 为空的 Jira",
        ),
        config_schema=CONFIG_SCHEMA,
        defaulting_rules=DEFAULTING_RULES,
        query_builder=query_builder,
        result_normalizer=result_normalizer,
        match_identity=match_identity,
        llm_policy="on-match-only",
        llm_output_schema=LLM_OUTPUT_SCHEMA,
        message_template_key=MESSAGE_TEMPLATE_KEY,
        renderer=renderer,
        delivery_policy={"mode": "per_issue", "max_issues_per_run": "notify_policy.max_issues_per_run"},
        acceptance_cases=(
            "build final JQL from task base_jql and window mode",
            "normalize Jira fields without business-condition hardcoding",
            "render one interactive card per delivered issue",
        ),
    )
