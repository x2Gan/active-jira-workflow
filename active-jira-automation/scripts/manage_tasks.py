#!/usr/bin/env python3
"""Manage active-jira-automation task definitions."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from task_store import (  # noqa: E402
    DEFAULT_DATA_ROOT,
    TaskStore,
    TaskStoreError,
    TaskValidationError,
)


DEFAULT_SCENARIO_METADATA = {
    "jira-scheduled-query-alert": {
        "message_template_key": "lark-jira-query-alert-card-v1",
        "llm_policy": "on-match-only",
        "window_mode": "created",
        "lookback_minutes": 5,
        "notify_policy": {
            "mode": "per_issue",
            "max_issues_per_run": 20,
            "repeat_snapshot": False,
        },
    }
}


def load_json_value(value: str, field_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise TaskValidationError(f"{field_name} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise TaskValidationError(f"{field_name} must be a JSON object")
    return parsed


def load_json_file(path: str, field_name: str = "input JSON") -> dict[str, Any]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaskValidationError(f"{field_name} is invalid: {exc}") from exc
    if not isinstance(parsed, dict):
        raise TaskValidationError(f"{field_name} must be an object")
    return parsed


def build_create_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = load_json_file(args.input_json) if args.input_json else {}
    scenario_key = args.scenario_key or payload.get("scenario_key")
    if scenario_key in DEFAULT_SCENARIO_METADATA:
        payload = {**copy.deepcopy(DEFAULT_SCENARIO_METADATA[scenario_key]), **payload}

    if args.query_spec_json and args.query_spec_file:
        raise TaskValidationError("use only one of --query-spec-json or --query-spec-file")

    field_values = {
        "task_name": args.task_name,
        "scenario_key": args.scenario_key,
        "project": args.project,
        "filter_prompt": args.filter_prompt,
        "base_jql": args.base_jql,
        "window_mode": args.window_mode,
        "lookback_minutes": args.lookback_minutes,
        "schedule_type": args.schedule_type,
        "schedule_expr": args.schedule_expr,
        "target_chat_id": args.target_chat_id,
        "target_chat_name": args.target_chat_name,
        "message_template_key": args.message_template_key,
        "llm_policy": args.llm_policy,
        "created_by": args.created_by,
    }
    payload.update({key: value for key, value in field_values.items() if value is not None})
    if args.query_rule is not None:
        payload["query_rule"] = load_json_value(args.query_rule, "query_rule")
    if args.query_spec_json is not None:
        payload["query_spec"] = load_json_value(args.query_spec_json, "query_spec")
    if args.query_spec_file is not None:
        payload["query_spec"] = load_json_file(args.query_spec_file, "query_spec file")
    if args.notify_policy_json is not None:
        payload["notify_policy"] = load_json_value(args.notify_policy_json, "notify_policy")
    return payload


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def task_summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "task_name": task.get("task_name"),
        "scenario_key": task.get("scenario_key"),
        "status": task.get("status"),
        "project": task.get("project"),
        "filter_prompt": task.get("filter_prompt"),
        "query_spec": task.get("query_spec"),
        "base_jql": task.get("base_jql"),
        "window_mode": task.get("window_mode"),
        "lookback_minutes": task.get("lookback_minutes"),
        "notify_policy": task.get("notify_policy"),
        "query_rule": task.get("query_rule"),
        "schedule": f"{task.get('schedule_type')}:{task.get('schedule_expr')}",
        "target_chat_id": task.get("target_chat_id"),
        "target_chat_name": task.get("target_chat_name"),
        "message_template_key": task.get("message_template_key"),
        "llm_policy": task.get("llm_policy"),
        "updated_at": task.get("updated_at"),
    }


def command_create(args: argparse.Namespace) -> int:
    store = TaskStore(args.data_root)
    task = store.create_task(build_create_payload(args))
    print_json({"created": True, "task": task_summary(task)})
    return 0


def command_list(args: argparse.Namespace) -> int:
    store = TaskStore(args.data_root)
    tasks = [task_summary(task) for task in store.list_tasks(include_deleted=args.include_deleted)]
    print_json({"tasks": tasks})
    return 0


def command_pause(args: argparse.Namespace) -> int:
    store = TaskStore(args.data_root)
    task = store.update_status(args.task, "paused")
    print_json({"paused": True, "task": task_summary(task)})
    return 0


def command_resume(args: argparse.Namespace) -> int:
    store = TaskStore(args.data_root)
    task = store.update_status(args.task, "enabled")
    print_json({"resumed": True, "task": task_summary(task)})
    return 0


def command_delete(args: argparse.Namespace) -> int:
    store = TaskStore(args.data_root)
    task = store.resolve_task(args.task, include_deleted=False)
    if not args.confirm:
        print_json({"deleted": False, "requires_confirmation": True, "task": task_summary(task)})
        return 2
    task = store.update_status(task["task_id"], "deleted")
    print_json({"deleted": True, "task": task_summary(task)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage active-jira-automation tasks.")
    parser.set_defaults(handler=None)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--data-root",
        default=str(DEFAULT_DATA_ROOT),
        help="Task data root. Defaults to active-jira-automation/data.",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    create_parser = subparsers.add_parser("create", parents=[common], help="Create a task definition.")
    create_parser.add_argument("--input-json", help="Read task definition fields from a JSON file, or '-' for stdin.")
    create_parser.add_argument("--task-name")
    create_parser.add_argument("--scenario", "--scenario-key", dest="scenario_key")
    create_parser.add_argument("--project")
    create_parser.add_argument("--filter-prompt", help="Original natural-language Jira filter intent.")
    create_parser.add_argument("--base-jql", help="Base JQL without runtime window clauses.")
    create_parser.add_argument("--query-spec-json", help="Auditable query_spec as a JSON object.")
    create_parser.add_argument("--query-spec-file", help="Read query_spec JSON object from a file, or '-' for stdin.")
    create_parser.add_argument("--query-rule", help="Legacy structured query rule as a JSON object.")
    create_parser.add_argument("--window-mode", choices=["created", "updated", "snapshot"])
    create_parser.add_argument("--lookback-minutes", type=int)
    create_parser.add_argument("--notify-policy-json", help="Notification policy as a JSON object.")
    create_parser.add_argument("--schedule-type", choices=["recurring", "once"])
    create_parser.add_argument("--schedule-expr")
    create_parser.add_argument("--target-chat-id")
    create_parser.add_argument("--target-chat-name")
    create_parser.add_argument("--message-template-key")
    create_parser.add_argument("--llm-policy")
    create_parser.add_argument("--created-by")
    create_parser.set_defaults(handler=command_create)

    list_parser = subparsers.add_parser("list", parents=[common], help="List task definitions.")
    list_parser.add_argument("--include-deleted", action="store_true", help="Include logically deleted tasks.")
    list_parser.set_defaults(handler=command_list)

    pause_parser = subparsers.add_parser("pause", parents=[common], help="Pause a task by task_id or unique task name.")
    pause_parser.add_argument("task")
    pause_parser.set_defaults(handler=command_pause)

    resume_parser = subparsers.add_parser("resume", parents=[common], help="Resume a task by task_id or unique task name.")
    resume_parser.add_argument("task")
    resume_parser.set_defaults(handler=command_resume)

    delete_parser = subparsers.add_parser("delete", parents=[common], help="Logically delete a task.")
    delete_parser.add_argument("task")
    delete_parser.add_argument("--confirm", action="store_true", help="Confirm logical deletion.")
    delete_parser.set_defaults(handler=command_delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (TaskStoreError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
