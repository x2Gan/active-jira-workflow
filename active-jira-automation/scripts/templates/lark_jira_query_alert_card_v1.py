#!/usr/bin/env python3
"""Lark interactive card template for generic Jira query alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from renderers.interactive_card_renderer import build_card, safe_text, text_node  # noqa: E402


TEMPLATE_KEY = "lark-jira-query-alert-card-v1"
DEFAULT_TITLE = "Jira 查询命中提醒"
SUMMARY_MAX_LENGTH = 220
ANALYSIS_MAX_LENGTH = 360
FIELD_MAX_LENGTH = 80


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _text(value: Any, *, fallback: str = "未设置") -> str:
    return str(value) if _present(value) else fallback


def _summary_at(index: int, summaries: Any) -> dict[str, Any]:
    if isinstance(summaries, list) and index < len(summaries) and isinstance(summaries[index], dict):
        return summaries[index]
    if isinstance(summaries, dict):
        return summaries
    return {}


def _first(summary: dict[str, Any], match: dict[str, Any], fields: tuple[str, ...], fallback: str) -> str:
    for field in fields:
        value = summary.get(field)
        if _present(value):
            return str(value)
    for field in fields:
        value = match.get(field)
        if _present(value):
            return str(value)
    return fallback


def _format_time(value: Any) -> str:
    if isinstance(value, datetime):
        current = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            current = datetime.fromisoformat(text)
        except ValueError:
            return value.strip()
    else:
        return "未设置"

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _priority_text(match: dict[str, Any]) -> str:
    severity = match.get("severity")
    priority = match.get("priority")
    if _present(severity):
        return str(severity)
    if _present(priority):
        return str(priority)
    return "未设置"


def header_template(match: dict[str, Any], task: dict[str, Any]) -> str:
    configured = task.get("card_header_template") or task.get("header_template")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()

    signal = f"{match.get('severity', '')} {match.get('priority', '')}".lower()
    if any(token in signal for token in ("p0", "blocker", "critical", "highest")):
        return "red"
    if any(token in signal for token in ("p1", "high", "major")):
        return "orange"
    if any(token in signal for token in ("medium", "p2")):
        return "yellow"
    return "blue"


def _jira_link(match: dict[str, Any]) -> str:
    key = _text(match.get("key") or match.get("issue_key"), fallback="UNKNOWN")
    url = match.get("url")
    if isinstance(url, str) and url.strip():
        return f"[{safe_text(key)}]({url.strip()})"
    return safe_text(key)


def _field(label: str, value: Any, *, escape_value: bool = True) -> dict[str, Any]:
    display_value = safe_text(value, fallback="未设置") if escape_value else _text(value)
    return {
        "is_short": True,
        "text": text_node(f"**{label}**\n{display_value}", max_length=FIELD_MAX_LENGTH, escape=False),
    }


def render_card(match: dict[str, Any], summary: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    title = _text(task.get("task_name"), fallback=DEFAULT_TITLE)
    key = _text(match.get("key") or match.get("issue_key"), fallback="UNKNOWN")
    issue_summary = _text(match.get("summary"), fallback="未命名 Jira")
    problem_summary = _first(summary, match, ("problem_summary", "symptom_summary"), issue_summary)
    risk_assessment = _first(summary, match, ("risk_assessment", "risk_summary", "impact_summary"), "待人工确认影响范围")

    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": text_node(
                f"**{safe_text(key)}**\n{safe_text(issue_summary)}",
                max_length=SUMMARY_MAX_LENGTH,
                escape=False,
            ),
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "fields": [
                _field("Jira 链接", _jira_link(match), escape_value=False),
                _field("创建时间", _format_time(match.get("created_at"))),
                _field("负责人", _text(match.get("assignee"), fallback="Unassigned")),
                _field("Reporter", match.get("reporter")),
                _field("优先级/Severity", _priority_text(match)),
                _field("状态", match.get("status")),
                _field("影响版本", match.get("affects_versions")),
                _field("归属团队", match.get("team")),
            ],
        },
        {
            "tag": "div",
            "text": text_node(f"**问题摘要**\n{safe_text(problem_summary)}", max_length=ANALYSIS_MAX_LENGTH, escape=False),
        },
        {
            "tag": "div",
            "text": text_node(f"**风险评估**\n{safe_text(risk_assessment)}", max_length=ANALYSIS_MAX_LENGTH, escape=False),
        },
    ]

    url = match.get("url")
    if isinstance(url, str) and url.strip():
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开 Jira"},
                        "url": url.strip(),
                    }
                ],
            }
        )

    return build_card(title, elements, template=header_template(match, task))


def render_cards(matches: list[dict[str, Any]], summaries: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    return [render_card(match, _summary_at(index, summaries), task) for index, match in enumerate(matches)]
