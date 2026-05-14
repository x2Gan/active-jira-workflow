#!/usr/bin/env python3
"""Scheduler adapter contract for active-jira-automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class SchedulerAdapterError(RuntimeError):
    """Raised when scheduler adapter operations fail."""


@dataclass(frozen=True)
class SchedulerJob:
    task_id: str
    schedule_type: str
    schedule_expr: str
    runner_command: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchedulerResult:
    scheduler_job_id: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)


class SchedulerAdapter(Protocol):
    def create(self, job: SchedulerJob) -> SchedulerResult:
        """Create a scheduler job."""

    def pause(self, scheduler_job_id: str) -> SchedulerResult:
        """Pause a scheduler job."""

    def resume(self, scheduler_job_id: str) -> SchedulerResult:
        """Resume a scheduler job."""

    def delete(self, scheduler_job_id: str) -> SchedulerResult:
        """Delete or disable a scheduler job."""

    def get_status(self, scheduler_job_id: str) -> SchedulerResult:
        """Return scheduler job status."""


class InMemorySchedulerAdapter:
    """Mock scheduler adapter used before the Openclaw API is finalized."""

    def __init__(self) -> None:
        self.jobs: dict[str, SchedulerJob] = {}
        self.statuses: dict[str, str] = {}

    def create(self, job: SchedulerJob) -> SchedulerResult:
        if not job.task_id.strip():
            raise SchedulerAdapterError("task_id must not be blank")
        scheduler_job_id = f"mock-{job.task_id}"
        if scheduler_job_id in self.jobs:
            raise SchedulerAdapterError(f"scheduler job already exists: {scheduler_job_id}")
        self.jobs[scheduler_job_id] = job
        self.statuses[scheduler_job_id] = "enabled"
        return SchedulerResult(scheduler_job_id=scheduler_job_id, status="enabled")

    def pause(self, scheduler_job_id: str) -> SchedulerResult:
        self._require_job(scheduler_job_id)
        self.statuses[scheduler_job_id] = "paused"
        return SchedulerResult(scheduler_job_id=scheduler_job_id, status="paused")

    def resume(self, scheduler_job_id: str) -> SchedulerResult:
        self._require_job(scheduler_job_id)
        self.statuses[scheduler_job_id] = "enabled"
        return SchedulerResult(scheduler_job_id=scheduler_job_id, status="enabled")

    def delete(self, scheduler_job_id: str) -> SchedulerResult:
        self._require_job(scheduler_job_id)
        self.statuses[scheduler_job_id] = "deleted"
        return SchedulerResult(scheduler_job_id=scheduler_job_id, status="deleted")

    def get_status(self, scheduler_job_id: str) -> SchedulerResult:
        self._require_job(scheduler_job_id)
        return SchedulerResult(scheduler_job_id=scheduler_job_id, status=self.statuses[scheduler_job_id])

    def _require_job(self, scheduler_job_id: str) -> None:
        if scheduler_job_id not in self.jobs:
            raise SchedulerAdapterError(f"unknown scheduler job: {scheduler_job_id}")


class OpenclawSchedulerAdapter:
    """Placeholder adapter boundary for the future Openclaw integration."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def create(self, job: SchedulerJob) -> SchedulerResult:
        return self._call_client("create", job)

    def pause(self, scheduler_job_id: str) -> SchedulerResult:
        return self._call_client("pause", scheduler_job_id)

    def resume(self, scheduler_job_id: str) -> SchedulerResult:
        return self._call_client("resume", scheduler_job_id)

    def delete(self, scheduler_job_id: str) -> SchedulerResult:
        return self._call_client("delete", scheduler_job_id)

    def get_status(self, scheduler_job_id: str) -> SchedulerResult:
        return self._call_client("get_status", scheduler_job_id)

    def _call_client(self, method_name: str, payload: Any) -> SchedulerResult:
        if self.client is None:
            raise SchedulerAdapterError("Openclaw client is not configured")
        method = getattr(self.client, method_name, None)
        if not callable(method):
            raise SchedulerAdapterError(f"Openclaw client does not support {method_name}")
        try:
            result = method(payload)
        except Exception as exc:  # pragma: no cover - exact client errors are defined later.
            raise SchedulerAdapterError(f"Openclaw {method_name} failed: {exc}") from exc
        if isinstance(result, SchedulerResult):
            return result
        if not isinstance(result, dict):
            raise SchedulerAdapterError(f"Openclaw {method_name} returned unsupported result")
        scheduler_job_id = result.get("scheduler_job_id") or result.get("id")
        status = result.get("status")
        if not scheduler_job_id or not status:
            raise SchedulerAdapterError(f"Openclaw {method_name} result missing scheduler_job_id/status")
        return SchedulerResult(scheduler_job_id=str(scheduler_job_id), status=str(status), detail=result)
