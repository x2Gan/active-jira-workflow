#!/usr/bin/env python3
"""Query window and checkpoint helpers for Jira automation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any


DEFAULT_LOOKBACK_MINUTES = 5
WINDOW_FIELDS = {
    "created": "created",
    "updated": "updated",
}


class JiraQueryRuntimeError(RuntimeError):
    """Raised when query window or checkpoint handling fails."""


@dataclass(frozen=True)
class QueryWindow:
    checkpoint: datetime
    query_start: datetime
    query_end: datetime
    lookback_minutes: int

    def as_payload(self) -> dict[str, str | int]:
        return {
            "checkpoint": format_datetime(self.checkpoint),
            "query_start": format_datetime(self.query_start),
            "query_end": format_datetime(self.query_end),
            "lookback_minutes": self.lookback_minutes,
        }


def parse_datetime(value: Any, *, field_name: str = "datetime") -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise JiraQueryRuntimeError(f"invalid {field_name}: {value}") from exc
    else:
        raise JiraQueryRuntimeError(f"missing {field_name}")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def runtime_checkpoint(runtime_state: dict[str, Any]) -> str | None:
    checkpoint = runtime_state.get("last_checkpoint") or runtime_state.get("current_checkpoint")
    return checkpoint if isinstance(checkpoint, str) and checkpoint.strip() else None


def initial_checkpoint(task: dict[str, Any]) -> datetime:
    explicit = task.get("initial_checkpoint") or task.get("start_at")
    if explicit:
        return parse_datetime(explicit, field_name="initial checkpoint")
    return parse_datetime(task.get("created_at"), field_name="task created_at")


def checkpoint_for(task: dict[str, Any], runtime_state: dict[str, Any] | None = None) -> datetime:
    runtime_state = runtime_state or {}
    checkpoint = runtime_checkpoint(runtime_state) or task.get("last_checkpoint")
    if checkpoint:
        return parse_datetime(checkpoint, field_name="last_checkpoint")
    return initial_checkpoint(task)


def lookback_minutes_for(task: dict[str, Any], default: int = DEFAULT_LOOKBACK_MINUTES) -> int:
    query_rule = task.get("query_rule") if isinstance(task.get("query_rule"), dict) else {}
    raw_value = task.get("lookback_minutes", query_rule.get("lookback_minutes", default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise JiraQueryRuntimeError(f"invalid lookback_minutes: {raw_value}") from exc
    if value < 0:
        raise JiraQueryRuntimeError("lookback_minutes must be non-negative")
    return value


def window_mode_for(task: dict[str, Any]) -> str:
    mode = task.get("window_mode", "created")
    if mode not in {"created", "updated", "snapshot"}:
        raise JiraQueryRuntimeError(f"invalid window_mode: {mode}")
    return mode


def compute_query_window(
    task: dict[str, Any],
    runtime_state: dict[str, Any] | None = None,
    *,
    current_time: datetime | None = None,
    default_lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
) -> QueryWindow:
    checkpoint = checkpoint_for(task, runtime_state)
    query_end = (current_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if query_end < checkpoint:
        raise JiraQueryRuntimeError("current_time must not be earlier than checkpoint")
    lookback_minutes = lookback_minutes_for(task, default_lookback_minutes)
    query_start = checkpoint - timedelta(minutes=lookback_minutes)
    return QueryWindow(
        checkpoint=checkpoint,
        query_start=query_start,
        query_end=query_end,
        lookback_minutes=lookback_minutes,
    )


def split_order_by(jql: str) -> tuple[str, str | None]:
    """Split a JQL string into the query body and trailing ORDER BY clause.

    The scanner is quote-aware so an issue summary containing "order by" does
    not accidentally truncate the base query.
    """
    text = jql.strip().rstrip(";").strip()
    lower = text.lower()
    in_quote = False
    escaped = False
    order_index: int | None = None
    order_content_index: int | None = None

    for index, char in enumerate(text):
        if char == "\\" and in_quote:
            escaped = not escaped
            continue
        if char == '"' and not escaped:
            in_quote = not in_quote
        escaped = False
        if in_quote:
            continue
        if lower.startswith("order", index):
            before = lower[index - 1] if index > 0 else " "
            after_order = lower[index + 5] if index + 5 < len(lower) else " "
            by_start = index + 5
            if before.isalnum() or before == "_" or after_order.isalnum() or after_order == "_":
                continue
            while by_start < len(lower) and lower[by_start].isspace():
                by_start += 1
            if lower.startswith("by", by_start):
                after_by = lower[by_start + 2] if by_start + 2 < len(lower) else " "
                if not after_by.isalnum() and after_by != "_":
                    order_index = index
                    order_content_index = by_start + 2

    if order_index is None:
        return text, None
    body = text[:order_index].strip()
    assert order_content_index is not None
    return body, text[order_content_index:].strip()


def _configured_order_by(task: dict[str, Any]) -> str | None:
    raw_order_by = task.get("order_by")
    if isinstance(raw_order_by, str) and raw_order_by.strip():
        return raw_order_by.strip()

    query_spec = task.get("query_spec")
    if not isinstance(query_spec, dict):
        return None
    spec_order_by = query_spec.get("order_by")
    if isinstance(spec_order_by, str) and spec_order_by.strip():
        return spec_order_by.strip()
    if isinstance(spec_order_by, list) and spec_order_by:
        clauses: list[str] = []
        for item in spec_order_by:
            if not isinstance(item, dict):
                continue
            field = item.get("field")
            if not isinstance(field, str) or not field.strip():
                continue
            direction = str(item.get("direction", "ASC")).upper()
            if direction not in {"ASC", "DESC"}:
                raise JiraQueryRuntimeError(f"invalid order_by direction: {direction}")
            clauses.append(f"{field.strip()} {direction}")
        if clauses:
            return ", ".join(clauses)
    return None


def _jql_datetime(value: datetime) -> str:
    return format_datetime(value)


def build_final_jql(task: dict[str, Any], window: QueryWindow) -> str:
    base_jql = task.get("base_jql")
    if not isinstance(base_jql, str) or not base_jql.strip():
        raise JiraQueryRuntimeError("missing base_jql")

    mode = window_mode_for(task)
    base_body, existing_order_by = split_order_by(base_jql)
    configured_order_by = _configured_order_by(task)

    if mode in WINDOW_FIELDS:
        window_field = WINDOW_FIELDS[mode]
        order_by = configured_order_by or f"{window_field} ASC"
        return (
            f"({base_body}) "
            f'AND {window_field} >= "{_jql_datetime(window.query_start)}" '
            f'AND {window_field} < "{_jql_datetime(window.query_end)}" '
            f"ORDER BY {order_by}"
        )

    order_by = configured_order_by or existing_order_by
    final_jql = f"({base_body})"
    if order_by:
        final_jql = f"{final_jql} ORDER BY {order_by}"
    return final_jql


def created_in_checkpoint_range(created_at: str | datetime, window: QueryWindow) -> bool:
    created = parse_datetime(created_at, field_name="issue created_at")
    return window.checkpoint < created < window.query_end


def value_for_match_identity(match: dict[str, Any], field: str) -> str:
    candidates = (f"{field}_at", field)
    for key in candidates:
        value = match.get(key)
        if value not in (None, ""):
            if isinstance(value, datetime):
                return format_datetime(value)
            return str(value)
    raise JiraQueryRuntimeError(f"match is missing {field} value for identity")


def base_jql_hash(task: dict[str, Any]) -> str:
    base_jql = task.get("base_jql")
    if not isinstance(base_jql, str) or not base_jql.strip():
        raise JiraQueryRuntimeError("missing base_jql")
    normalized = " ".join(base_jql.strip().split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def match_identity_for(task: dict[str, Any], match: dict[str, Any]) -> str:
    task_id = task.get("task_id")
    issue_key = match.get("key") or match.get("issue_key")
    if not isinstance(task_id, str) or not task_id.strip():
        raise JiraQueryRuntimeError("task is missing task_id for identity")
    if not isinstance(issue_key, str) or not issue_key.strip():
        raise JiraQueryRuntimeError("match is missing issue key for identity")

    mode = window_mode_for(task)
    if mode == "snapshot":
        return f"{task_id}:{issue_key}:{base_jql_hash(task)}"
    identity_value = value_for_match_identity(match, mode)
    return f"{task_id}:{issue_key}:{identity_value}"


def checkpoint_update_payload(window: QueryWindow) -> dict[str, Any]:
    return {
        "last_checkpoint": format_datetime(window.query_end),
        "idempotency_window": window.as_payload(),
    }
