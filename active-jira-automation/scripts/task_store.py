#!/usr/bin/env python3
"""Persistent task store for active-jira-automation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = SKILL_ROOT / "data"

TASK_STATUSES = {"enabled", "paused", "deleted"}
SCHEDULE_TYPES = {"recurring", "once"}
ALLOWED_TRANSITIONS = {
    "enabled": {"paused", "deleted"},
    "paused": {"enabled", "deleted"},
    "deleted": set(),
}
REQUIRED_TASK_FIELDS = (
    "task_name",
    "scenario_key",
    "project",
    "query_rule",
    "schedule_type",
    "schedule_expr",
    "target_chat_id",
    "message_template_key",
    "llm_policy",
)


class TaskStoreError(RuntimeError):
    """Base error for task persistence and lifecycle failures."""


class TaskValidationError(TaskStoreError):
    """Raised when a task payload is invalid."""


class TaskNotFoundError(TaskStoreError):
    """Raised when no task matches a selector."""


class TaskConflictError(TaskStoreError):
    """Raised when a task selector or task name is ambiguous."""


class TaskStateTransitionError(TaskStoreError):
    """Raised when a lifecycle transition is not allowed."""


@dataclass(frozen=True)
class TaskPaths:
    definition: Path
    runtime: Path
    log_dir: Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "jira-automation-task"


def generate_task_id(task_name: str, now: datetime | None = None) -> str:
    timestamp = (now or utc_now()).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{slugify(task_name)}-{timestamp}-{uuid4().hex[:8]}"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TaskNotFoundError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TaskValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TaskValidationError(f"expected JSON object in {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def validate_task_payload(payload: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_TASK_FIELDS if payload.get(field) in (None, "", [], {})]
    if missing:
        raise TaskValidationError(f"missing required task field(s): {', '.join(missing)}")

    for field in (
        "task_name",
        "scenario_key",
        "project",
        "schedule_type",
        "schedule_expr",
        "target_chat_id",
        "message_template_key",
        "llm_policy",
    ):
        if not isinstance(payload.get(field), str):
            raise TaskValidationError(f"{field} must be a string")

    if payload["schedule_type"] not in SCHEDULE_TYPES:
        raise TaskValidationError(f"schedule_type must be one of: {', '.join(sorted(SCHEDULE_TYPES))}")

    if not isinstance(payload.get("query_rule"), dict):
        raise TaskValidationError("query_rule must be a JSON object")

    status = payload.get("status", "enabled")
    if status not in TASK_STATUSES:
        raise TaskValidationError(f"status must be one of: {', '.join(sorted(TASK_STATUSES))}")


class TaskStore:
    """Filesystem-backed task store.

    Layout:
    - tasks/<task_id>.json for task definitions
    - runtime/<task_id>.json for mutable runtime state
    - logs/<task_id>/<timestamp>.json for append-only run/audit logs
    """

    def __init__(self, data_root: Path | str | None = None) -> None:
        self.data_root = Path(data_root) if data_root is not None else DEFAULT_DATA_ROOT
        self.tasks_dir = self.data_root / "tasks"
        self.runtime_dir = self.data_root / "runtime"
        self.logs_dir = self.data_root / "logs"
        self.ensure_layout()

    def ensure_layout(self) -> None:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def paths_for(self, task_id: str) -> TaskPaths:
        return TaskPaths(
            definition=self.tasks_dir / f"{task_id}.json",
            runtime=self.runtime_dir / f"{task_id}.json",
            log_dir=self.logs_dir / task_id,
        )

    def create_task(
        self,
        payload: dict[str, Any],
        *,
        task_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        candidate = dict(payload)
        validate_task_payload(candidate)
        self._ensure_unique_task_name(candidate["task_name"])

        current_time = isoformat_utc(now)
        new_task_id = task_id or generate_task_id(candidate["task_name"], now)
        paths = self.paths_for(new_task_id)
        if paths.definition.exists():
            raise TaskConflictError(f"task_id already exists: {new_task_id}")

        task = {
            **candidate,
            "task_id": new_task_id,
            "status": candidate.get("status", "enabled"),
            "created_at": candidate.get("created_at") or current_time,
            "updated_at": current_time,
        }
        if "last_checkpoint" not in task:
            task["last_checkpoint"] = None
        write_json(paths.definition, task)
        return task

    def get_task(self, task_id: str) -> dict[str, Any]:
        return read_json(self.paths_for(task_id).definition)

    def list_tasks(self, *, include_deleted: bool = False) -> list[dict[str, Any]]:
        tasks = [read_json(path) for path in sorted(self.tasks_dir.glob("*.json"))]
        if not include_deleted:
            tasks = [task for task in tasks if task.get("status") != "deleted"]
        return sorted(tasks, key=lambda task: (task.get("created_at", ""), task.get("task_id", "")))

    def resolve_task(self, selector: str, *, include_deleted: bool = True) -> dict[str, Any]:
        by_id = self.paths_for(selector).definition
        if by_id.exists():
            task = read_json(by_id)
            if include_deleted or task.get("status") != "deleted":
                return task
            raise TaskNotFoundError(f"task is deleted: {selector}")

        matches = [task for task in self.list_tasks(include_deleted=include_deleted) if task.get("task_name") == selector]
        if not matches:
            raise TaskNotFoundError(f"task not found: {selector}")
        if len(matches) > 1:
            raise TaskConflictError(f"task name is ambiguous, use task_id instead: {selector}")
        return matches[0]

    def update_status(self, selector: str, status: str, *, now: datetime | None = None) -> dict[str, Any]:
        if status not in TASK_STATUSES:
            raise TaskValidationError(f"unknown status: {status}")
        task = self.resolve_task(selector, include_deleted=False)
        current_status = task.get("status")
        if current_status == status:
            return task
        if status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise TaskStateTransitionError(f"cannot transition task {task['task_id']} from {current_status} to {status}")
        task["status"] = status
        task["updated_at"] = isoformat_utc(now)
        write_json(self.paths_for(task["task_id"]).definition, task)
        return task

    def write_runtime_state(
        self,
        task_id: str,
        state: dict[str, Any],
        *,
        merge: bool = True,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        self.get_task(task_id)
        path = self.paths_for(task_id).runtime
        current: dict[str, Any] = read_json(path) if path.exists() and merge else {}
        updated = {**current, **state, "task_id": task_id, "updated_at": isoformat_utc(now)}
        write_json(path, updated)
        return updated

    def read_runtime_state(self, task_id: str) -> dict[str, Any]:
        return read_json(self.paths_for(task_id).runtime)

    def append_log(
        self,
        task_id: str,
        event: dict[str, Any],
        *,
        timestamp: datetime | None = None,
    ) -> Path:
        self.get_task(task_id)
        ts = (timestamp or utc_now()).astimezone(timezone.utc)
        filename = ts.strftime("%Y%m%dT%H%M%SZ") + f"-{uuid4().hex[:8]}.json"
        path = self.paths_for(task_id).log_dir / filename
        payload = {"task_id": task_id, "logged_at": isoformat_utc(ts), **event}
        write_json(path, payload)
        return path

    def _ensure_unique_task_name(self, task_name: str) -> None:
        matches = [
            task
            for task in self.list_tasks(include_deleted=True)
            if task.get("task_name") == task_name and task.get("status") != "deleted"
        ]
        if matches:
            raise TaskConflictError(f"task_name already exists: {task_name}")
