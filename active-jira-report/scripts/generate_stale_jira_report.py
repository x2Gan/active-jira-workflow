#!/usr/bin/env python3
"""Generate a rule-compliant stale Jira Markdown report.

This report generator is intentionally scenario-shaped but not hardcoded:
the caller must pass --project and --age from the user's trigger phrase.
It handles JiraCLI pagination, issue normalization, urgency sorting, overdue
age calculation, and the required Active Jira Report Markdown table.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_JIRA_SCRIPTS = REPO_ROOT / "active-jira" / "scripts"
sys.path.insert(0, str(ACTIVE_JIRA_SCRIPTS))

try:
    from query_stale_jiras import (  # type: ignore
        DEFAULT_ACTIVE_CLOSED_STATUSES,
        DEFAULT_ACTIVE_OPEN_STATUSES,
        UserError,
        build_assignee_clause,
        build_jql,
        parse_age_to_days,
        split_values,
        validate_project_key,
    )
except ImportError as exc:  # pragma: no cover - only hit if repo layout changes.
    raise SystemExit(f"Cannot import active-jira query helpers: {exc}") from exc


SEVERITY_COLUMNS = [
    "customfield_10401",
    "severity",
    "Severity",
    "fields.customfield_10401",
    "fields.severity",
    "fields.Severity",
]
TEAM_FIELDS = [
    "customfield_11801",
    "归属Team",
    "归属 Team",
    "归属团队",
    "所属Team",
    "所属 Team",
    "所属团队",
    "team",
    "Team",
]
TABLE_COLUMNS = [
    "排序",
    "Jira",
    "Severity/紧急程度",
    "创建时间",
    "超期时长(天)",
    "状态",
    "责任人",
    "问题摘要",
    "评论摘要",
]
HIGHLIGHT_COLUMNS = [
    "Jira",
    "紧急程度",
    "超期天数",
    "状态",
    "责任人",
    "推荐理由",
    "摘要",
]


@dataclass
class ReportIssue:
    key: str
    created: datetime | None
    created_display: str
    overdue_days: float
    status: str
    assignee: str
    summary: str
    severity: str
    severity_source: str
    team: str
    team_source: str
    comment_summary: str = "-"


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


def extract_issue_items(raw: Any) -> list[dict[str, Any]]:
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
        items = []
    return [item for item in items if isinstance(item, dict)]


def read_json_inputs(paths: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in paths:
        if path == "-":
            text = sys.stdin.read()
        else:
            text = Path(path).read_text(encoding="utf-8")
        items.extend(extract_issue_items(load_json_loose(text)))
    return dedupe_issues(items)


def dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for issue in issues:
        key = str(get_nested(issue, ["key", "issueKey", "id"]) or "")
        marker = key or json.dumps(issue, sort_keys=True, default=str)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(issue)
    return result


def check_jira_bin(jira_bin: str) -> None:
    if shutil.which(jira_bin) is None:
        raise UserError(
            f"Cannot find jira binary '{jira_bin}'. Install ankitpokhrel/jira-cli and run `jira init` first."
        )


def run_command(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise UserError(f"Command failed with exit code {proc.returncode}:\n{err}\n\nCommand:\n{shlex.join(cmd)}")
    return proc.stdout


def jira_list_cmd(jira_bin: str, jql: str, page_start: int, page_size: int, config: str | None) -> list[str]:
    cmd = [
        jira_bin,
        "issue",
        "list",
        "--raw",
        "--paginate",
        f"{page_start}:{page_size}",
        "-q",
        jql,
    ]
    if config:
        cmd.extend(["-c", config])
    return cmd


def jira_view_raw_cmd(jira_bin: str, key: str, config: str | None) -> list[str]:
    cmd = [jira_bin, "issue", "view", key, "--raw"]
    if config:
        cmd.extend(["-c", config])
    return cmd


def jira_comments_cmd(jira_bin: str, key: str, limit: int, config: str | None) -> list[str]:
    cmd = [jira_bin, "issue", "view", key, "--comments", str(limit)]
    if config:
        cmd.extend(["-c", config])
    return cmd


def fetch_all_pages(
    jira_bin: str,
    jql: str,
    config: str | None,
    page_size: int,
    verbose: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    check_jira_bin(jira_bin)
    start = 0
    pages: list[str] = []
    issues: list[dict[str, Any]] = []
    while True:
        cmd = jira_list_cmd(jira_bin, jql, start, page_size, config)
        if verbose:
            print(f"Fetching page {start}:{page_size}", file=sys.stderr)
        pages.append(shlex.join(cmd))
        raw = load_json_loose(run_command(cmd))
        page_items = extract_issue_items(raw)
        issues.extend(page_items)
        if len(page_items) < page_size:
            break
        start += page_size
    return dedupe_issues(issues), pages


def enrich_issue_detail(jira_bin: str, issue: dict[str, Any], config: str | None) -> dict[str, Any]:
    key = str(get_nested(issue, ["key", "issueKey", "id"]) or "")
    if not key:
        return issue
    raw = load_json_loose(run_command(jira_view_raw_cmd(jira_bin, key, config)))
    items = extract_issue_items(raw)
    return items[0] if items else issue


def get_nested(obj: Any, path: Iterable[str] | str) -> Any:
    parts = path.split(".") if isinstance(path, str) else list(path)
    cur = obj
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def first_present(obj: dict[str, Any], paths: Iterable[str]) -> tuple[Any, str]:
    for path in paths:
        value = get_nested(obj, path)
        if value not in (None, "", [], {}):
            return value, path
        if not path.startswith("fields."):
            value = get_nested(obj, f"fields.{path}")
            if value not in (None, "", [], {}):
                return value, f"fields.{path}"
    return None, ""


def value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return normalize_space(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ["value", "name", "displayName", "key", "id"]:
            if value.get(key) not in (None, ""):
                return value_to_text(value[key])
        return normalize_space(adf_to_text(value))
    if isinstance(value, list):
        return ", ".join(part for part in (value_to_text(item) for item in value) if part)
    return normalize_space(str(value))


def adf_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(adf_to_text(item) for item in value)
    if isinstance(value, dict):
        parts: list[str] = []
        if isinstance(value.get("text"), str):
            parts.append(value["text"])
        if "content" in value:
            parts.append(adf_to_text(value["content"]))
        return " ".join(part for part in parts if part)
    return ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def display_person(value: Any) -> str:
    if value in (None, "", [], {}):
        return "Unassigned"
    if isinstance(value, dict):
        for key in ["displayName", "name", "emailAddress", "accountId", "key"]:
            if value.get(key):
                return str(value[key])
    return value_to_text(value) or "Unassigned"


def display_status(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, dict):
        if value.get("name"):
            return str(value["name"])
        category = value.get("statusCategory")
        if isinstance(category, dict) and category.get("name"):
            return str(category["name"])
    return value_to_text(value)


def parse_jira_datetime(value: Any, local_tz: timezone) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", normalized)
    candidates = [
        normalized,
        normalized[:19],
        text[:10],
    ]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=local_tz)
            return dt
        except ValueError:
            continue
    return None


def format_datetime(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def local_timezone_label(dt: datetime) -> str:
    offset = dt.utcoffset() or timedelta()
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return f"UTC{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def issue_key(issue: dict[str, Any]) -> str:
    return str(get_nested(issue, "key") or get_nested(issue, "issueKey") or get_nested(issue, "id") or "")


def issue_has_configured_severity(issue: dict[str, Any], severity_fields: list[str]) -> bool:
    severity_value, _ = first_present(issue, severity_fields)
    return bool(value_to_text(severity_value))


def issue_has_configured_team(issue: dict[str, Any], team_fields: list[str]) -> bool:
    team_value, _ = first_present(issue, team_fields)
    return bool(value_to_text(team_value))


def extract_severity(issue: dict[str, Any], severity_fields: list[str]) -> tuple[str, str]:
    severity_value, severity_source = first_present(issue, severity_fields)
    severity_text = value_to_text(severity_value)
    if severity_text:
        return severity_text, severity_source
    priority_value, priority_source = first_present(issue, ["priority", "fields.priority"])
    priority_text = value_to_text(priority_value)
    if priority_text:
        return priority_text, priority_source or "priority"
    return "未设置", ""


def extract_team(issue: dict[str, Any], team_fields: list[str]) -> tuple[str, str]:
    team_value, team_source = first_present(issue, team_fields)
    team_text = value_to_text(team_value)
    return (team_text or "未设置", team_source)


def issue_to_report_issue(
    issue: dict[str, Any],
    query_time: datetime,
    local_tz: timezone,
    severity_fields: list[str],
    team_fields: list[str],
    summary_limit: int,
) -> ReportIssue:
    fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
    key = issue_key(issue)
    created = parse_jira_datetime(get_nested(issue, "fields.created") or issue.get("created"), local_tz)
    overdue_days = 0.0
    if created:
        overdue_days = max(0.0, (query_time - created.astimezone(query_time.tzinfo)).total_seconds() / 86400)
    assignee = display_person(get_nested(issue, "fields.assignee") or issue.get("assignee"))
    status = display_status(get_nested(issue, "fields.status") or issue.get("status"))
    summary = value_to_text(fields.get("summary") or issue.get("summary") or issue.get("title"))
    if not summary:
        summary = value_to_text(fields.get("description") or issue.get("description"))
    severity, severity_source = extract_severity(issue, severity_fields)
    team, team_source = extract_team(issue, team_fields)
    return ReportIssue(
        key=key,
        created=created,
        created_display=format_datetime(created),
        overdue_days=overdue_days,
        status=status,
        assignee=assignee,
        summary=truncate(summary, summary_limit),
        severity=severity,
        severity_source=severity_source,
        team=team,
        team_source=team_source,
    )


def severity_rank(value: str) -> float:
    normalized = (value or "").strip().lower()
    p_match = re.fullmatch(r"p\s*([0-4])", normalized)
    if p_match:
        return float(p_match.group(1))
    ranks = {
        "blocker": 0.5,
        "critical": 0.8,
        "highest": 1.0,
        "high": 2.0,
        "medium": 3.0,
        "low": 4.0,
        "lowest": 5.0,
        "trivial": 5.5,
        "minor": 5.5,
        "未设置": 99.0,
        "未知": 99.0,
        "": 99.0,
    }
    return ranks.get(normalized, 90.0)


def sort_report_issues(rows: list[ReportIssue]) -> list[ReportIssue]:
    return sorted(
        rows,
        key=lambda row: (
            severity_rank(row.severity),
            row.created or datetime.max.replace(tzinfo=timezone.utc),
            row.key,
        ),
    )


def sort_oldest_issues(rows: list[ReportIssue]) -> list[ReportIssue]:
    return sorted(
        rows,
        key=lambda row: (
            -row.overdue_days,
            severity_rank(row.severity),
            row.key,
        ),
    )


def status_risk_rank(status: str) -> float:
    normalized = (status or "").strip().lower()
    ranks = {
        "reopened": 0.0,
        "open": 1.0,
        "in progress": 2.0,
        "pending": 3.0,
        "resolved": 4.0,
        "in review": 4.5,
        "closed": 99.0,
    }
    return ranks.get(normalized, 10.0)


def sort_highlight_issues(rows: list[ReportIssue]) -> list[ReportIssue]:
    return sorted(
        rows,
        key=lambda row: (
            severity_rank(row.severity),
            status_risk_rank(row.status),
            0 if row.assignee.lower() == "unassigned" else 1,
            -row.overdue_days,
            row.key,
        ),
    )


def format_distribution(counts: Counter[str], severity_order: bool = False) -> str:
    if not counts:
        return "-"
    if severity_order:
        items = sorted(counts.items(), key=lambda item: (severity_rank(item[0]), item[0]))
    else:
        items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name} {count}" for name, count in items)


def format_top_counts(counts: Counter[str], limit: int = 3) -> str:
    if not counts:
        return "-"
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{name} {count}" for name, count in items)


def average_overdue_days(rows: list[ReportIssue]) -> float:
    if not rows:
        return 0.0
    return sum(row.overdue_days for row in rows) / len(rows)


def missing_team_sort_value(team: str) -> int:
    return 1 if (team or "").strip() in {"", "-", "未设置", "未知"} else 0


def team_groups(sorted_rows: list[ReportIssue]) -> list[tuple[str, list[ReportIssue]]]:
    grouped: dict[str, list[ReportIssue]] = {}
    for row in sorted_rows:
        grouped.setdefault(row.team or "未设置", []).append(row)
    return sorted(
        grouped.items(),
        key=lambda item: (
            missing_team_sort_value(item[0]),
            -len(item[1]),
            min(severity_rank(row.severity) for row in item[1]),
            min((row.created or datetime.max.replace(tzinfo=timezone.utc) for row in item[1])),
            item[0],
        ),
    )


def highlight_reason(row: ReportIssue) -> str:
    parts = [f"紧急程度 {row.severity}", f"已超期 {row.overdue_days:.1f} 天"]
    if row.status:
        parts.append(f"状态 {row.status}")
    if row.assignee.lower() == "unassigned":
        parts.append("当前未分配责任人")
    return "，".join(parts)


def truncate(value: str, limit: int) -> str:
    value = normalize_space(value)
    if limit <= 0 or len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def summarize_comments_text(text: str, limit: int) -> str:
    cleaned = normalize_space(re.sub(r"[-=]{3,}", " ", text))
    return truncate(cleaned, limit) if cleaned else "-"


def fetch_comment_summary(jira_bin: str, key: str, config: str | None, comment_limit: int, text_limit: int) -> str:
    if not key:
        return "-"
    text = run_command(jira_comments_cmd(jira_bin, key, comment_limit, config))
    return summarize_comments_text(text, text_limit)


def comments_from_raw(issue: dict[str, Any], text_limit: int) -> str:
    comments = get_nested(issue, "fields.comment.comments") or get_nested(issue, "comment.comments")
    if not isinstance(comments, list) or not comments:
        return "-"
    bodies: list[str] = []
    for comment in comments[-5:]:
        if isinstance(comment, dict):
            body = value_to_text(comment.get("body"))
            author = display_person(comment.get("author")) if comment.get("author") else ""
            bodies.append(f"{author}: {body}" if author else body)
    return truncate(" / ".join(part for part in bodies if part), text_limit) or "-"


def append_highlight_section(lines: list[str], sorted_rows: list[ReportIssue], limit: int) -> None:
    highlight_rows = sort_highlight_issues(sorted_rows)[:limit]
    lines.extend(
        [
            "",
            "## Highlight",
            "",
            "建议 PL/项目经理优先推动以下 Jira 的修复或责任确认；排序依据为紧急程度、状态风险、是否未分配责任人和超期天数。",
            "",
            "| " + " | ".join(HIGHLIGHT_COLUMNS) + " |",
            "| " + " | ".join(["---"] * len(HIGHLIGHT_COLUMNS)) + " |",
        ]
    )
    if not highlight_rows:
        lines.append("| - | - | - | - | - | - | 未查询到需要立即推动的 Jira |")
        return
    for row in highlight_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row.key),
                    md_escape(row.severity),
                    f"{row.overdue_days:.1f}",
                    md_escape(row.status),
                    md_escape(row.assignee),
                    md_escape(highlight_reason(row)),
                    md_escape(row.summary),
                ]
            )
            + " |"
        )


def append_issue_table(
    lines: list[str],
    rows: list[ReportIssue],
    rank_by_key: dict[str, int] | None = None,
) -> None:
    lines.extend(
        [
            "| " + " | ".join(TABLE_COLUMNS) + " |",
            "| " + " | ".join(["---"] * len(TABLE_COLUMNS)) + " |",
        ]
    )
    if not rows:
        lines.append("| - | - | - | - | - | - | - | 未查询到满足条件的 Jira | - |")
        return
    for local_index, row in enumerate(rows, start=1):
        rank = rank_by_key.get(row.key, local_index) if rank_by_key else local_index
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    md_escape(row.key),
                    md_escape(row.severity),
                    md_escape(row.created_display),
                    f"{row.overdue_days:.1f}",
                    md_escape(row.status),
                    md_escape(row.assignee),
                    md_escape(row.summary),
                    md_escape(row.comment_summary),
                ]
            )
            + " |"
        )


def append_team_grouped_issue_section(lines: list[str], sorted_rows: list[ReportIssue]) -> None:
    rank_by_key = {row.key: index for index, row in enumerate(sorted_rows, start=1) if row.key}
    grouped_rows = team_groups(sorted_rows)
    lines.extend(
        [
            "",
            "## Jira 清单（按归属Team分组）",
            "",
            f"共 {len(grouped_rows)} 个归属Team；各组内按紧急程度、创建时间、Jira Key 排序。",
        ]
    )
    if not sorted_rows:
        lines.append("")
        append_issue_table(lines, [], rank_by_key)
        return

    for team, rows in grouped_rows:
        oldest = max(rows, key=lambda row: row.overdue_days, default=None)
        unassigned = sum(1 for row in rows if row.assignee.lower() == "unassigned")
        status_counts = Counter(row.status or "未设置" for row in rows)
        severity_counts = Counter(row.severity or "未设置" for row in rows)
        assignee_counts = Counter(row.assignee for row in rows if row.assignee.lower() != "unassigned")
        oldest_text = f"{oldest.key}，{oldest.overdue_days:.1f} 天" if oldest else "-"

        lines.extend(
            [
                "",
                f"### 归属Team：{md_escape(team)}",
                "",
                f"- 数量: {len(rows)}",
                f"- 状态分布: {format_distribution(status_counts)}",
                f"- 紧急程度: {format_distribution(severity_counts, severity_order=True)}",
                f"- 未分配责任人: {unassigned}",
                f"- 平均超期: {average_overdue_days(rows):.1f} 天",
                f"- 最久未处理: {oldest_text}",
                f"- 责任人 Top 3: {format_top_counts(assignee_counts, 3)}",
                "",
            ]
        )
        append_issue_table(lines, rows, rank_by_key)


def append_summary_section(
    lines: list[str],
    sorted_rows: list[ReportIssue],
    comment_policy: str,
    source_line: str,
    team_source_line: str,
) -> None:
    oldest = max(sorted_rows, key=lambda row: row.overdue_days, default=None)
    unassigned = sum(1 for row in sorted_rows if row.assignee.lower() == "unassigned")
    status_counts = Counter(row.status or "未设置" for row in sorted_rows)
    severity_counts = Counter(row.severity or "未设置" for row in sorted_rows)
    assignee_counts = Counter(row.assignee for row in sorted_rows if row.assignee.lower() != "unassigned")
    assignee_top = sorted(assignee_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    oldest_top = sort_oldest_issues(sorted_rows)[:5]

    lines.extend(
        [
            "",
            "## 汇总",
            "",
            f"总数: {len(sorted_rows)}",
            f"状态分布: {format_distribution(status_counts)}",
            f"紧急程度: {format_distribution(severity_counts, severity_order=True)}",
            f"未分配: {unassigned}",
            f"最久未处理: {oldest.key + '，' + f'{oldest.overdue_days:.1f}' + ' 天' if oldest else '-'}",
            "",
            "### 责任人数量 Top 5",
            "",
            "| 责任人 | 数量 |",
            "| --- | --- |",
        ]
    )
    if assignee_top:
        for assignee, count in assignee_top:
            lines.append(f"| {md_escape(assignee)} | {count} |")
    else:
        lines.append("| - | - |")

    lines.extend(
        [
            "",
            "### 最久未处理 Top 5",
            "",
            "| Jira | 紧急程度 | 超期天数 | 状态 | 责任人 | 摘要 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if oldest_top:
        for row in oldest_top:
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row.key),
                        md_escape(row.severity),
                        f"{row.overdue_days:.1f}",
                        md_escape(row.status),
                        md_escape(row.assignee),
                        md_escape(row.summary),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            f"{comment_policy}；紧急程度来源: {source_line}；归属Team来源: {team_source_line}。",
        ]
    )


def build_report(
    rows: list[ReportIssue],
    project: str,
    age: str,
    query_time: datetime,
    report_command: str,
    data_command_pattern: str,
    jql: str,
    page_count: int,
    comment_policy: str,
    input_mode: bool,
    highlight_limit: int,
) -> str:
    sorted_rows = sort_report_issues(rows)
    severity_sources = sorted({row.severity_source or "未设置" for row in sorted_rows}) if sorted_rows else []
    source_line = ", ".join(severity_sources) if severity_sources else "-"
    team_sources = sorted({row.team_source or "未设置" for row in sorted_rows}) if sorted_rows else []
    team_source_line = ", ".join(team_sources) if team_sources else "-"
    time_label = f"{query_time.strftime('%Y-%m-%d %H:%M:%S')} {local_timezone_label(query_time)}"

    lines = [
        f"# {project} 长期未处理 Jira 报告",
        "",
        "## 查询信息",
        "",
        f"- 查询时间: {time_label}",
        f"- 项目: {project}",
        f"- 超时时间: {age}",
        f"- 命令: `{report_command}`",
        f"- 数据命令: `{data_command_pattern}`",
        f"- JQL: `{jql}`",
        f"- 分页: {'input-json' if input_mode else f'{page_count} 页'}",
        f"- 评论摘要策略: {comment_policy}",
        f"- Severity 来源: {source_line}",
        f"- 归属Team 来源: {team_source_line}",
    ]

    append_highlight_section(lines, sorted_rows, highlight_limit)
    append_team_grouped_issue_section(lines, sorted_rows)
    append_summary_section(lines, sorted_rows, comment_policy, source_line, team_source_line)
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a full Markdown report for stale, non-closed Jira issues."
    )
    parser.add_argument("--project", required=True, help="Jira project key extracted from the trigger phrase.")
    parser.add_argument("--age", required=True, help="Age threshold extracted from the trigger phrase, e.g. 7d, 1w, 30天.")
    parser.add_argument(
        "--closed-mode",
        choices=[
            "auto",
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
        default="auto",
        help="How to define non-closed issues. auto uses GENEVA Active statuses, otherwise status-not-closed.",
    )
    parser.add_argument("--statuses", help="Comma-separated status whitelist for active-status modes.")
    parser.add_argument("--closed-statuses", help="Comma-separated closed status list for status-not-closed modes.")
    parser.add_argument("--assignee-current-user", action="store_true", help="Add assignee in (currentUser()).")
    parser.add_argument("--assignee", help="Comma-separated assignee values to add as assignee in (...).")
    parser.add_argument("--extra-jql", help="Extra JQL clause to AND with the generated query.")
    parser.add_argument(
        "--date-mode",
        choices=["absolute", "relative", "start-of-day", "start-of-day-unquoted"],
        default="absolute",
        help="How to express the created-date cutoff in JQL.",
    )
    parser.add_argument("--jira-bin", default="jira", help="jira-cli executable name or path.")
    parser.add_argument("--config", help="Path to a jira-cli config file; passed as -c.")
    parser.add_argument("--page-size", type=int, default=100, help="JiraCLI page size. Max: 100.")
    parser.add_argument("--input-json", action="append", help="Read raw Jira JSON from a file or '-' instead of running JiraCLI.")
    parser.add_argument("--severity-field", action="append", help="Additional severity field path, e.g. customfield_10401.")
    parser.add_argument("--team-field", action="append", help="Additional 归属Team field path, e.g. customfield_11801.")
    parser.add_argument(
        "--enrich-details",
        choices=["none", "missing-severity", "all"],
        default="missing-severity",
        help="Fetch jira issue view --raw for all issues, only issues missing required report fields, or none.",
    )
    parser.add_argument(
        "--comments",
        choices=["none", "input", "top", "all"],
        default="none",
        help="Comment summary mode. input reads comments already present in --input-json/raw issue data.",
    )
    parser.add_argument("--comments-top", type=int, default=20, help="Number of sorted rows to fetch comments for in top mode.")
    parser.add_argument("--comment-limit", type=int, default=5, help="Recent comments to request from JiraCLI.")
    parser.add_argument("--comment-summary-limit", type=int, default=120, help="Max comment summary characters.")
    parser.add_argument("--summary-limit", type=int, default=80, help="Max issue summary characters.")
    parser.add_argument("--highlight-limit", type=int, default=5, help="Max Jira issues to include in the opening Highlight.")
    parser.add_argument("--output", help="Write the Markdown report to this file instead of stdout.")
    parser.add_argument("--dry-run", action="store_true", help="Print JQL and command plan without querying Jira.")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr.")
    return parser.parse_args(argv)


def choose_closed_mode(project: str, mode: str) -> str:
    if mode != "auto":
        return mode
    return "active-statuses" if project == "GENEVA" else "status-not-closed"


def build_report_command(argv: list[str]) -> str:
    executable = Path(__file__).as_posix()
    return shlex.join(["python", executable, *argv])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        project = validate_project_key(args.project)
        age_days = parse_age_to_days(args.age)
        if args.page_size < 1 or args.page_size > 100:
            raise UserError("--page-size must be between 1 and 100 because JiraCLI caps issue list pages at 100.")
        if args.highlight_limit < 0:
            raise UserError("--highlight-limit must be greater than or equal to 0.")

        statuses = split_values(args.statuses) if args.statuses else None
        closed_statuses = split_values(args.closed_statuses) if args.closed_statuses else None
        assignee_clause = build_assignee_clause(args)
        closed_mode = choose_closed_mode(project, args.closed_mode)
        jql = build_jql(
            project,
            age_days,
            closed_mode,
            args.extra_jql,
            "asc",
            args.date_mode,
            False,
            statuses or (DEFAULT_ACTIVE_OPEN_STATUSES if closed_mode.startswith("active-statuses") else None),
            closed_statuses or (DEFAULT_ACTIVE_CLOSED_STATUSES if closed_mode.startswith("status-not-closed") else None),
            assignee_clause,
        )
        command_pattern = shlex.join(jira_list_cmd(args.jira_bin, jql, 0, args.page_size, args.config)).replace(
            f"0:{args.page_size}", f"<offset>:{args.page_size}"
        )
        report_command = build_report_command(argv)
        severity_fields = list(dict.fromkeys((args.severity_field or []) + SEVERITY_COLUMNS))
        team_fields = list(dict.fromkeys((args.team_field or []) + TEAM_FIELDS))

        if args.dry_run:
            print("JQL:")
            print(jql)
            print("\nReport command:")
            print(report_command)
            print("\nData command pattern:")
            print(command_pattern)
            if args.output:
                print("\nReport output:")
                print(Path(args.output).expanduser())
            return 0

        input_mode = bool(args.input_json)
        if input_mode:
            raw_issues = read_json_inputs(args.input_json)
            page_commands: list[str] = []
        else:
            raw_issues, page_commands = fetch_all_pages(
                args.jira_bin,
                jql,
                args.config,
                args.page_size,
                args.verbose,
            )

        if not input_mode and args.enrich_details != "none":
            check_jira_bin(args.jira_bin)
            enriched: list[dict[str, Any]] = []
            for index, issue in enumerate(raw_issues, start=1):
                needs_detail = (
                    args.enrich_details == "all"
                    or not issue_has_configured_severity(issue, severity_fields)
                    or not issue_has_configured_team(issue, team_fields)
                )
                if needs_detail:
                    if args.verbose and index % 25 == 0:
                        print(f"Enriching issue details {index}/{len(raw_issues)}", file=sys.stderr)
                    issue = enrich_issue_detail(args.jira_bin, issue, args.config)
                enriched.append(issue)
            raw_issues = enriched

        query_time = datetime.now().astimezone()
        local_tz = query_time.tzinfo or timezone.utc
        rows = [
            issue_to_report_issue(issue, query_time, local_tz, severity_fields, team_fields, args.summary_limit)
            for issue in raw_issues
        ]
        rows = sort_report_issues(rows)

        if args.comments == "input":
            raw_by_key = {issue_key(issue): issue for issue in raw_issues}
            for row in rows:
                row.comment_summary = comments_from_raw(raw_by_key.get(row.key, {}), args.comment_summary_limit)
            comment_policy = "input-json 中已有评论"
        elif args.comments in {"top", "all"}:
            check_jira_bin(args.jira_bin)
            count = len(rows) if args.comments == "all" else min(args.comments_top, len(rows))
            keys_for_comments = {row.key for row in rows[:count]}
            for index, row in enumerate(rows, start=1):
                if row.key in keys_for_comments:
                    if args.verbose:
                        print(f"Fetching comments {index}/{count}: {row.key}", file=sys.stderr)
                    row.comment_summary = fetch_comment_summary(
                        args.jira_bin,
                        row.key,
                        args.config,
                        args.comment_limit,
                        args.comment_summary_limit,
                    )
            comment_policy = f"{args.comments}, recent {args.comment_limit}"
        else:
            comment_policy = "未抓取评论，评论摘要列以 - 表示"

        report = build_report(
            rows,
            project,
            args.age,
            query_time,
            report_command,
            command_pattern,
            jql,
            len(page_commands),
            comment_policy,
            input_mode,
            args.highlight_limit,
        )
        if args.output:
            output_path = Path(args.output).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report + "\n", encoding="utf-8")
            print(f"Wrote report: {output_path}", file=sys.stderr)
        else:
            print(report)
        return 0
    except UserError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
