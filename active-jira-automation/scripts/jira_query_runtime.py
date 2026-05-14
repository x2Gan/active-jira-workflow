#!/usr/bin/env python3
"""Query window and checkpoint helpers for Jira automation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_LOOKBACK_MINUTES = 5


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


def created_in_checkpoint_range(created_at: str | datetime, window: QueryWindow) -> bool:
    created = parse_datetime(created_at, field_name="issue created_at")
    return window.checkpoint < created <= window.query_end


def checkpoint_update_payload(window: QueryWindow) -> dict[str, Any]:
    return {
        "last_checkpoint": format_datetime(window.query_end),
        "idempotency_window": window.as_payload(),
    }
