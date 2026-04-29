#!/usr/bin/env python3
# Copyright (c) 2026 Zepp Health. All rights reserved.
"""Query Jira field values and dynamic creation options.

This helper is read-only and CLI-first. It uses the local `jira` command for
operations that JiraCLI exposes, and uses Jira REST only for metadata endpoints
such as createmeta/project statuses that JiraCLI does not expose as stable
commands.
"""

from __future__ import annotations

import argparse
import base64
import json
import netrc
import os
import re
import shutil
import ssl
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_CONFIG = Path.home() / ".config" / ".jira" / ".config.yml"
DEFAULT_DYNAMIC_FIELDS = [
    "project",
    "status",
    "versions",
    "fixVersions",
    "components",
    "customfield_10800",  # Products
    "customfield_12700",  # Planned version
]
FIELD_LABELS = {
    "project": "Project",
    "status": "Status",
    "versions": "Affects Version/s",
    "fixVersions": "Fix Version/s",
    "components": "Component/s",
    "customfield_10800": "Products",
    "customfield_12700": "规划版本",
}


class UserError(Exception):
    pass


def read_config(path: str | None) -> dict[str, str]:
    config_path = Path(path or os.environ.get("JIRA_CONFIG_FILE") or DEFAULT_CONFIG)
    values: dict[str, str] = {}
    if not config_path.exists():
        return values
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith((" ", "\t")) or ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in {"server", "login", "auth_type"} and value:
            values[key] = value
    return values


def run_jira_cli(args: argparse.Namespace, command: list[str]) -> str:
    jira_bin = args.jira_bin
    if not shutil.which(jira_bin) and not Path(jira_bin).exists():
        raise UserError(f"Cannot find jira CLI executable: {jira_bin}")

    cmd = [jira_bin]
    if args.config:
        cmd.extend(["--config", args.config])
    cmd.extend(command)

    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    completed = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise UserError(f"jira CLI failed: {' '.join(cmd)}\n{message}")
    return completed.stdout


def resolve_auth(server: str, login: str | None, auth_type: str | None) -> tuple[str, dict[str, str]]:
    parsed = urlparse(server)
    if not parsed.hostname:
        raise UserError(f"Invalid Jira server URL: {server}")

    token = os.environ.get("JIRA_API_TOKEN") or os.environ.get("JIRA_TOKEN")
    resolved_login = login or ""
    if not token:
        try:
            auth = netrc.netrc().authenticators(parsed.hostname)
        except (FileNotFoundError, netrc.NetrcParseError):
            auth = None
        if auth:
            netrc_login, _, netrc_password = auth
            if not resolved_login:
                resolved_login = netrc_login
            if not login or login == netrc_login:
                token = netrc_password

    if not token:
        raise UserError(
            "Cannot find Jira credentials for metadata REST calls. Set JIRA_API_TOKEN "
            "or add a matching ~/.netrc entry."
        )

    auth_type = (auth_type or "basic").lower()
    headers = {"Accept": "application/json"}
    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {token}"
    else:
        if not resolved_login:
            raise UserError("Jira login is required for basic auth.")
        raw = f"{resolved_login}:{token}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    return resolved_login, headers


def jira_get(server: str, headers: dict[str, str], path: str, insecure: bool = False) -> Any:
    url = server.rstrip("/") + path
    request = Request(url, headers=headers)
    context = ssl._create_unverified_context() if insecure else None
    try:
        with urlopen(request, timeout=30, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise UserError(f"Jira REST failed: HTTP {exc.code}\n{body}\nURL: {url}") from exc
    except URLError as exc:
        raise UserError(f"Jira REST failed: {exc}\nURL: {url}") from exc


def split_fields(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_DYNAMIC_FIELDS)
    return [part.strip() for part in raw.split(",") if part.strip()]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def value_to_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return "-"
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip())
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(part for part in (value_to_text(item) for item in value) if part != "-") or "-"
    if isinstance(value, dict):
        for key in ["value", "name", "displayName", "key", "id"]:
            if value.get(key) not in (None, "", [], {}):
                return value_to_text(value[key])
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def issue_value_to_text(field_id: str, value: Any) -> str:
    if field_id == "project" and isinstance(value, dict):
        key = value.get("key")
        name = value.get("name")
        if key and name:
            return f"{key} / {name}"
    return value_to_text(value)


def option_rows(field_id: str, field: dict[str, Any], match: str | None, source: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    field_name = field.get("name") or field_id
    for option in field.get("allowedValues") or []:
        text = value_to_text(option)
        if match and normalize(match) not in normalize(text):
            continue
        rows.append(
            {
                "field": field_name,
                "field_id": field_id,
                "value": text,
                "id": str(option.get("id", "-")) if isinstance(option, dict) else "-",
                "source": source,
            }
        )
    if not rows and not field.get("allowedValues"):
        rows.append(
            {
                "field": field_name,
                "field_id": field_id,
                "value": "-",
                "id": "-",
                "source": f"{source}; no static allowedValues",
            }
        )
    return rows


def print_rows(rows: list[dict[str, str]], output: str) -> None:
    if output == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print("| Field | Field ID | Value | Option ID | Source |")
    print("| --- | --- | --- | --- | --- |")
    for row in rows:
        print(
            "| {field} | `{field_id}` | {value} | {id} | {source} |".format(
                **{key: str(value).replace("|", "\\|") for key, value in row.items()}
            )
        )


def find_issue_type(meta: dict[str, Any], issue_type: str) -> dict[str, Any]:
    projects = meta.get("projects") or []
    if not projects:
        raise UserError("No project metadata returned.")
    issue_types = projects[0].get("issuetypes") or []
    for item in issue_types:
        if item.get("name", "").casefold() == issue_type.casefold():
            return item
    available = ", ".join(item.get("name", "") for item in issue_types)
    raise UserError(f"Issue type '{issue_type}' not found. Available: {available}")


def command_issue(args: argparse.Namespace) -> None:
    raw = run_jira_cli(args, ["issue", "view", args.issue, "--raw"])
    try:
        issue = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserError(f"Cannot parse jira CLI raw issue JSON for {args.issue}.") from exc

    names = issue.get("names") or {}
    fields = issue.get("fields") or {}
    rows = []
    for field_id in split_fields(args.fields):
        rows.append(
            {
                "field": names.get(field_id) or FIELD_LABELS.get(field_id, field_id),
                "field_id": field_id,
                "value": issue_value_to_text(field_id, fields.get(field_id)),
                "id": "-",
                "source": f"jira issue view {args.issue} --raw",
            }
        )
    print_rows(rows, args.output)


def command_create(args: argparse.Namespace, server: str, headers: dict[str, str], insecure: bool) -> None:
    query = urlencode(
        {
            "projectKeys": args.project,
            "issuetypeNames": args.issue_type,
            "expand": "projects.issuetypes.fields",
        }
    )
    meta = jira_get(server, headers, f"/rest/api/2/issue/createmeta?{query}", insecure)
    issue_type = find_issue_type(meta, args.issue_type)
    fields = issue_type.get("fields") or {}
    rows: list[dict[str, str]] = []
    for field_id in split_fields(args.fields):
        if field_id == "status":
            rows.extend(status_rows(args, server, headers, insecure))
            continue
        if field_id == "project":
            project = (meta.get("projects") or [{}])[0]
            value = f"{project.get('key', args.project)} / {project.get('name', '-')}"
            if not args.match or normalize(args.match) in normalize(value):
                rows.append(
                    {
                        "field": "Project",
                        "field_id": "project",
                        "value": value,
                        "id": str(project.get("id", "-")),
                        "source": "createmeta selected project",
                    }
                )
            continue
        field = fields.get(field_id)
        if not field:
            rows.append(
                {
                    "field": field_id,
                    "field_id": field_id,
                    "value": "-",
                    "id": "-",
                    "source": f"not present for {args.project}/{args.issue_type}",
                }
            )
            continue
        rows.extend(option_rows(field_id, field, args.match, "createmeta"))
    print_rows(rows[: args.limit], args.output)


def status_rows(
    args: argparse.Namespace,
    server: str,
    headers: dict[str, str],
    insecure: bool,
) -> list[dict[str, str]]:
    data = jira_get(server, headers, f"/rest/api/2/project/{quote(args.project)}/statuses", insecure)
    rows: list[dict[str, str]] = []
    for issue_type in data:
        if issue_type.get("name", "").casefold() != args.issue_type.casefold():
            continue
        for status in issue_type.get("statuses") or []:
            value = status.get("name", "-")
            if args.match and normalize(args.match) not in normalize(value):
                continue
            rows.append(
                {
                    "field": "Status",
                    "field_id": "status",
                    "value": value,
                    "id": str(status.get("id", "-")),
                    "source": "project statuses",
                }
            )
    return rows


def command_projects(args: argparse.Namespace) -> None:
    raw = run_jira_cli(args, ["project", "list"])
    rows = []
    for line in raw.splitlines():
        if not line.strip() or line.startswith("KEY"):
            continue
        parts = [part.strip() for part in re.split(r"\t+", line.strip()) if part.strip()]
        if len(parts) < 2:
            continue
        key, name = parts[0], parts[1]
        value = f"{key} / {name}"
        if args.match and normalize(args.match) not in normalize(value):
            continue
        rows.append(
            {
                "field": "Project",
                "field_id": "project",
                "value": value,
                "id": "-",
                "source": "jira project list",
            }
        )
    print_rows(rows[: args.limit], args.output)


def resolve_rest_client(args: argparse.Namespace, config: dict[str, str]) -> tuple[str, dict[str, str]]:
    server = (args.server or config.get("server") or "").rstrip("/")
    if not server:
        raise UserError("Jira server is required for metadata lookup. Pass --server or configure jira-cli first.")
    login, headers = resolve_auth(
        server,
        args.login or config.get("login"),
        args.auth_type or config.get("auth_type"),
    )
    _ = login
    return server, headers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Jira CLI config path. Defaults to JIRA_CONFIG_FILE or ~/.config/.jira/.config.yml.")
    parser.add_argument("--server", help="Jira server URL. Defaults to Jira CLI config server.")
    parser.add_argument("--login", help="Jira login. Defaults to Jira CLI config login or ~/.netrc login.")
    parser.add_argument("--auth-type", choices=["basic", "bearer"], help="Jira auth type. Defaults to Jira CLI config auth_type or basic.")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification.")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--jira-bin", default="jira", help="Path to jira CLI executable. Default: jira.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_output_flag(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--output",
            choices=["markdown", "json"],
            default=argparse.SUPPRESS,
            help="Output format. Also accepted before the subcommand.",
        )

    issue = subparsers.add_parser("issue", help="Read field values from an existing issue.")
    issue.add_argument("issue", help="Issue key, for example GENEVA-1996.")
    issue.add_argument("--fields", help="Comma-separated field IDs. Defaults to dynamic fields.")
    add_output_flag(issue)

    create = subparsers.add_parser("create", help="Query legal values for creating an issue.")
    create.add_argument("--project", required=True, help="Target Jira project key.")
    create.add_argument("--issue-type", default="Bug", help="Target issue type. Default: Bug.")
    create.add_argument("--fields", help="Comma-separated field IDs. Defaults to dynamic fields.")
    create.add_argument("--match", help="Case-insensitive substring filter for option values.")
    create.add_argument("--limit", type=int, default=200, help="Maximum rows to print.")
    add_output_flag(create)

    projects = subparsers.add_parser("projects", help="Search visible Jira projects.")
    projects.add_argument("--match", help="Case-insensitive substring filter for project key/name.")
    projects.add_argument("--limit", type=int, default=200, help="Maximum rows to print.")
    add_output_flag(projects)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = read_config(args.config)

    if args.command == "issue":
        command_issue(args)
    elif args.command == "create":
        server, headers = resolve_rest_client(args, config)
        command_create(args, server, headers, args.insecure)
    elif args.command == "projects":
        command_projects(args)
    else:  # pragma: no cover
        parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UserError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)
