#!/usr/bin/env python3
# Copyright (c) 2026 Zepp Health. All rights reserved.
# Author: Gan GAN
# Affiliation: Zepp Health, Active BU AI Lab
"""Query stale, non-closed Jira issues with ankitpokhrel/jira-cli.

This wrapper builds a Jira Query Language (JQL) query, runs:
    jira issue list --raw -q '<JQL>'
and converts the raw JSON result into a Markdown table.

It is intended to be run on the user's machine where `jira` is installed,
authenticated, and configured via `jira init` or JIRA_CONFIG_FILE.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from typing import Any, Iterable


DEFAULT_COLUMNS = ["Jira", "Assignee", "Status", "Created", "Summary"]

# Geneva/Active Jira workflow statuses observed from the user's Jira filter.
# "Closed" is intentionally excluded from the default stale-not-closed search.
DEFAULT_ACTIVE_OPEN_STATUSES = [
    "Open",
    "In Progress",
    "Reopened",
    "Resolved",
    "In Review",
    "Pending",
]
DEFAULT_ACTIVE_CLOSED_STATUSES = ["Closed"]


class UserError(Exception):
    pass


def parse_age_to_days(raw: str) -> int:
    """Parse age strings such as 7d, 1w, 1mo, 30 days, 1 month.

    Months are normalized to 30 days to keep JQL portable across Jira versions.
    Years are normalized to 365 days.
    """
    value = (raw or "").strip().lower()
    value = value.replace(" ", "")
    aliases = {
        "week": "1w",
        "weekly": "1w",
        "month": "1mo",
        "monthly": "1mo",
    }
    value = aliases.get(value, value)

    # Chinese units are intentionally represented via unicode escapes here so
    # this source remains ASCII-safe for tooling that expects POSIX text.
    zh_units = {
        "\u5929": "d",       # day
        "\u65e5": "d",       # day
        "\u5468": "w",       # week
        "\u661f\u671f": "w",  # week
        "\u4e2a\u6708": "mo", # month
        "\u6708": "mo",      # month
        "\u5e74": "y",       # year
    }
    for zh, unit in zh_units.items():
        if value.endswith(zh):
            value = value[: -len(zh)] + unit
            break

    match = re.fullmatch(r"(\d+)(d|day|days|w|week|weeks|mo|mon|month|months|m|y|year|years)", value)
    if not match:
        raise UserError(
            "Invalid --age. Use values like 7d, 1w, 2w, 1mo, 30days, or 1month."
        )

    number = int(match.group(1))
    unit = match.group(2)
    if number <= 0:
        raise UserError("--age must be greater than zero.")

    if unit in {"d", "day", "days"}:
        return number
    if unit in {"w", "week", "weeks"}:
        return number * 7
    if unit in {"mo", "mon", "month", "months", "m"}:
        return number * 30
    if unit in {"y", "year", "years"}:
        return number * 365
    raise UserError(f"Unsupported age unit: {unit}")


def validate_project_key(project: str) -> str:
    project = (project or "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", project):
        raise UserError("Project key must contain letters, digits, underscore, or hyphen and start with a letter.")
    return project.upper()


def split_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    reader = csv.reader([raw], skipinitialspace=True)
    values = next(reader, [])
    return [value.strip().strip("'").strip('"') for value in values if value.strip()]


def jql_value(value: str) -> str:
    """Return a Jira JQL value literal.

    Jira accepts bare words such as Open and Reopened, but values containing
    spaces must be quoted. Quoting all string values is not accepted by every
    legacy Jira parser, so keep simple identifiers bare and quote only when
    needed.
    """
    cleaned = value.strip()
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", cleaned):
        return cleaned
    return '"' + cleaned.replace('\\', '\\\\').replace('"', '\\"') + '"'


def status_in_clause(statuses: list[str]) -> str:
    if not statuses:
        raise UserError("Status list cannot be empty.")
    return "status in (" + ", ".join(jql_value(status) for status in statuses) + ")"


def status_not_in_clause(statuses: list[str]) -> str:
    if not statuses:
        raise UserError("Closed-status list cannot be empty.")
    return "status not in (" + ", ".join(jql_value(status) for status in statuses) + ")"


def build_non_closed_clause(
    mode: str,
    statuses: list[str] | None,
    closed_statuses: list[str] | None,
) -> str:
    open_statuses = statuses or DEFAULT_ACTIVE_OPEN_STATUSES
    closed_status_values = closed_statuses or DEFAULT_ACTIVE_CLOSED_STATUSES
    status_category_open = 'statusCategory IN ("To Do", "In Progress")'

    if mode == "active-statuses":
        return f"{status_in_clause(open_statuses)} AND resolution = Unresolved"
    if mode == "active-statuses-no-resolution":
        return status_in_clause(open_statuses)
    if mode == "status-not-closed":
        return f"{status_not_in_clause(closed_status_values)} AND resolution = Unresolved"
    if mode == "status-not-closed-no-resolution":
        return status_not_in_clause(closed_status_values)
    if mode == "resolution-unresolved":
        return "resolution = Unresolved"
    if mode == "resolution-empty":
        return "resolution IS EMPTY"
    if mode == "resolution-null":
        return "resolution = NULL"
    if mode == "status-category":
        return status_category_open
    if mode == "status-category-alias":
        return "statusCategory IN (New, Indeterminate)"
    if mode == "status-category-not-done":
        return 'statusCategory != "Done"'
    if mode == "status-category-not-complete":
        return "statusCategory != Complete"
    if mode == "both":
        return f"resolution = Unresolved AND {status_category_open}"
    raise UserError(f"Unsupported closed mode: {mode}")


def build_created_clause(age_days: int, date_mode: str) -> str:
    if date_mode == "absolute":
        cutoff = (date.today() - timedelta(days=age_days)).isoformat()
        return f'created <= "{cutoff}"'
    if date_mode == "relative":
        return f"created <= -{age_days}d"
    if date_mode == "start-of-day":
        return f'created <= startOfDay("-{age_days}d")'
    if date_mode == "start-of-day-unquoted":
        return f"created <= startOfDay(-{age_days}d)"
    raise UserError(f"Unsupported date mode: {date_mode}")


def build_assignee_clause(args: argparse.Namespace) -> str | None:
    if args.assignee_current_user and args.assignee:
        raise UserError("Use either --assignee-current-user or --assignee, not both.")
    if args.assignee_current_user:
        return "assignee in (currentUser())"
    if args.assignee:
        values = split_values(args.assignee)
        if not values:
            raise UserError("--assignee cannot be empty.")
        return "assignee in (" + ", ".join(jql_value(value) for value in values) + ")"
    return None


def build_jql(
    project: str,
    age_days: int,
    closed_mode: str,
    extra_jql: str | None,
    order: str,
    date_mode: str,
    include_jql_order: bool,
    statuses: list[str] | None,
    closed_statuses: list[str] | None,
    assignee_clause: str | None,
) -> str:
    non_closed = build_non_closed_clause(closed_mode, statuses, closed_statuses)
    order_dir = "ASC" if order == "asc" else "DESC"
    clauses = [
        f"project = {project}",
        build_created_clause(age_days, date_mode),
        non_closed,
    ]
    if assignee_clause:
        clauses.append(assignee_clause)
    if extra_jql:
        clauses.append(f"({extra_jql})")
    jql = " AND ".join(clauses)
    if include_jql_order:
        jql += f" ORDER BY created {order_dir}"
    return jql


def run_jira_raw(jira_bin: str, jql: str, config: str | None) -> str:
    if shutil.which(jira_bin) is None:
        raise UserError(
            f"Cannot find jira binary '{jira_bin}'. Install ankitpokhrel/jira-cli and run `jira init` first."
        )
    cmd = [jira_bin, "issue", "list", "--raw", "-q", jql]
    if config:
        cmd.extend(["-c", config])
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        command = shlex.join(cmd)
        raise UserError(
            f"jira-cli failed with exit code {proc.returncode}:\n{err}\n\n"
            f"Generated JQL:\n{jql}\n\nCommand:\n{command}"
        )
    return proc.stdout


def load_json_loose(text: str) -> Any:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    starts = [pos for pos in [cleaned.find("["), cleaned.find("{")] if pos >= 0]
    if not starts:
        raise UserError("jira-cli returned output that does not contain JSON.")
    start = min(starts)
    end = max(cleaned.rfind("]"), cleaned.rfind("}"))
    if end <= start:
        raise UserError("jira-cli returned incomplete JSON.")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        preview = cleaned[:600]
        raise UserError(f"Could not parse jira-cli JSON output: {exc}\nOutput preview:\n{preview}") from exc


def normalize_issues(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        if isinstance(raw.get("issues"), list):
            items = raw["issues"]
        elif isinstance(raw.get("data"), list):
            items = raw["data"]
        else:
            items = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        return []

    return [normalize_issue(item) for item in items if isinstance(item, dict)]


def get_nested(obj: dict[str, Any], paths: Iterable[tuple[str, ...]]) -> Any:
    for path in paths:
        cur: Any = obj
        ok = True
        for part in path:
            if not isinstance(cur, dict) or part not in cur:
                ok = False
                break
            cur = cur[part]
        if ok and cur not in (None, ""):
            return cur
    return None


def display_person(value: Any) -> str:
    if value is None:
        return "Unassigned"
    if isinstance(value, str):
        return value or "Unassigned"
    if isinstance(value, dict):
        for key in ["displayName", "name", "emailAddress", "accountId", "key"]:
            if value.get(key):
                return str(value[key])
    return str(value)


def display_status(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("name"):
            return str(value["name"])
        if isinstance(value.get("statusCategory"), dict) and value["statusCategory"].get("name"):
            return str(value["statusCategory"]["name"])
    return str(value)


def normalize_created(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    candidate = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text[:19]


def normalize_issue(issue: dict[str, Any]) -> dict[str, str]:
    key = get_nested(issue, [("key",), ("issueKey",), ("id",)])
    assignee = get_nested(issue, [("fields", "assignee"), ("assignee",)])
    status = get_nested(issue, [("fields", "status"), ("status",)])
    created = get_nested(issue, [("fields", "created"), ("created",)])
    summary = get_nested(issue, [("fields", "summary"), ("summary",), ("title",)])
    return {
        "Jira": str(key or ""),
        "Assignee": display_person(assignee),
        "Status": display_status(status),
        "Created": normalize_created(created),
        "Summary": str(summary or ""),
    }


def md_escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def truncate(value: str, limit: int) -> str:
    value = value.strip()
    if limit <= 0 or len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def to_markdown(rows: list[dict[str, str]], summary_limit: int) -> str:
    lines = [
        "| " + " | ".join(DEFAULT_COLUMNS) + " |",
        "| " + " | ".join(["---"] * len(DEFAULT_COLUMNS)) + " |",
    ]
    for row in rows:
        values = []
        for col in DEFAULT_COLUMNS:
            value = row.get(col, "")
            if col == "Summary":
                value = truncate(value, summary_limit)
            values.append(md_escape(value))
        lines.append("| " + " | ".join(values) + " |")
    if not rows:
        lines.append("| _No matching Jira issues._ |  |  |  |  |")
    return "\n".join(lines)


def csv_to_json_like(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query stale non-closed Jira issues and print a Markdown table."
    )
    parser.add_argument("--project", default="GENEVA", help="Jira project key. Default: GENEVA")
    parser.add_argument("--age", default="1w", help="Minimum open age, e.g. 7d, 1w, 1mo, 30days.")
    parser.add_argument(
        "--closed-mode",
        choices=[
            "active-statuses",
            "active-statuses-no-resolution",
            "status-not-closed",
            "status-not-closed-no-resolution",
            "resolution-unresolved",
            "resolution-empty",
            "resolution-null",
            "status-category",
            "status-category-alias",
            "status-category-not-done",
            "status-category-not-complete",
            "both",
        ],
        default="active-statuses",
        help=(
            "How to define non-closed issues. Default: active-statuses, meaning "
            "status in (Open, In Progress, Reopened, Resolved, In Review, Pending) "
            "AND resolution = Unresolved."
        ),
    )
    parser.add_argument(
        "--statuses",
        help=(
            "Comma-separated status whitelist for --closed-mode active-statuses or "
            "active-statuses-no-resolution. Default excludes Closed."
        ),
    )
    parser.add_argument(
        "--closed-statuses",
        help="Comma-separated closed status list for status-not-closed modes. Default: Closed.",
    )
    parser.add_argument(
        "--assignee-current-user",
        action="store_true",
        help="Add assignee in (currentUser()) to the generated JQL.",
    )
    parser.add_argument(
        "--assignee",
        help="Comma-separated assignee values to add as assignee in (...). Do not combine with --assignee-current-user.",
    )
    parser.add_argument("--extra-jql", help="Extra JQL clause to AND with the generated query.")
    parser.add_argument(
        "--date-mode",
        choices=["absolute", "relative", "start-of-day", "start-of-day-unquoted"],
        default="absolute",
        help=(
            "How to express the created-date cutoff in JQL. "
            "Default: absolute, e.g. created <= \"2026-04-21\"."
        ),
    )
    parser.add_argument(
        "--include-jql-order",
        action="store_true",
        help="Append ORDER BY created to JQL. By default rows are sorted locally to avoid parser-specific ORDER BY errors.",
    )
    parser.add_argument("--jira-bin", default="jira", help="jira-cli executable name or path.")
    parser.add_argument("--config", help="Path to a jira-cli config file; passed as -c.")
    parser.add_argument("--max", type=int, default=0, help="Maximum rows to print after querying; 0 means no limit.")
    parser.add_argument("--summary-limit", type=int, default=140, help="Maximum summary characters. Default: 140.")
    parser.add_argument("--order", choices=["asc", "desc"], default="asc", help="Created sort order. Default: asc.")
    parser.add_argument("--dry-run", action="store_true", help="Print the JQL and jira-cli command without executing.")
    parser.add_argument("--input-json", help="Read jira-cli raw JSON from this file instead of executing jira-cli.")
    parser.add_argument("--input-csv", help="Read jira-cli CSV output from this file instead of executing jira-cli.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        project = validate_project_key(args.project)
        age_days = parse_age_to_days(args.age)
        statuses = split_values(args.statuses) if args.statuses else None
        closed_statuses = split_values(args.closed_statuses) if args.closed_statuses else None
        assignee_clause = build_assignee_clause(args)
        jql = build_jql(
            project,
            age_days,
            args.closed_mode,
            args.extra_jql,
            args.order,
            args.date_mode,
            args.include_jql_order,
            statuses,
            closed_statuses,
            assignee_clause,
        )

        if args.dry_run:
            cmd = [args.jira_bin, "issue", "list", "--raw", "-q", jql]
            if args.config:
                cmd.extend(["-c", args.config])
            print("JQL:")
            print(jql)
            print("\nCommand:")
            print(shlex.join(cmd))
            return 0

        if args.input_json:
            raw_data = load_json_loose(open(args.input_json, encoding="utf-8").read())
            rows = normalize_issues(raw_data)
        elif args.input_csv:
            rows = normalize_issues(csv_to_json_like(open(args.input_csv, encoding="utf-8").read()))
        else:
            output = run_jira_raw(args.jira_bin, jql, args.config)
            rows = normalize_issues(load_json_loose(output))

        rows = sorted(rows, key=lambda row: row.get("Created", ""), reverse=(args.order == "desc"))
        if args.max and args.max > 0:
            rows = rows[: args.max]
        print(to_markdown(rows, args.summary_limit))
        return 0
    except UserError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
