---
name: active-jira-report
description: create project-specific Jira reports and rule-based Jira issue drafts for Active teams. use when the user asks for formatted Jira summaries, stale issue reports, weekly or release reports, issue rollups by assignee or status, project-specific report templates, or creation of new bug Jira issues with required fields, custom fields, labels, components, or other project conventions.
---

# Active Jira Report

## Overview

Use this skill for Jira workflows that are shaped by project rules rather than by raw Jira mechanics. Typical cases include formatted status reports, release or sprint rollups, stale issue summaries, and creating new defects or tasks with project-specific fields filled according to local conventions.

This skill assumes the generic Jira command layer is available through the sibling `active-jira` skill. In practice, use local `jira` commands directly here, and read `../active-jira/references/jira-cli-usage.md` when you need exact CLI syntax.

Keep this skill focused on:

- Project-specific report structures and summarization rules
- Rule-based issue creation flows
- Field-filling conventions and custom field discovery
- Reusable Markdown report formats for teams

## Trigger examples

- "帮我按 GENEVA 的格式整理一份 Jira 周报"
- "汇总这个项目的 Jira 状态，按 assignee 和 status 出报告"
- "帮我创建一个缺陷 Jira，按项目规范自动填写字段"
- "根据这批 Jira 输出发布风险报告"
- "查一下超过 1 周未关闭的 Jira，并整理成汇报格式"
- "帮我查询 GENEVA 项目超过 1 周未处理的 Jira 情况"

## Core workflows

### 1. Create new defect or task Jira with project rules

Use this workflow when the user wants a new Jira issue created according to team or project conventions.

Recommended process:

1. Confirm or infer the target project, issue type, and whether the user wants a draft command or an actual Jira creation.
2. Collect the minimum required fields: summary, description, priority or severity, assignee, labels, components, versions, epic or sprint, and any known custom fields.
3. Inspect one to three recent issues from the same project and type when the project uses special fields or custom field conventions. Prefer real examples over guessing.
4. If the Jira instance supports it, use `jira issue create --custom key=value` for extra fields; otherwise provide a ready-to-run command or a clear field checklist.
5. If required project-specific fields remain unknown after inspecting comparable issues, stop and ask one focused question rather than creating a broken issue.

Field handling rules:

- Never invent custom field names or IDs.
- Reuse labels, components, fix versions, and severity vocabulary already present in the project.
- When the user says "自动填写", infer only from project examples, not from generic Jira assumptions.
- If the user asks to actually create the issue, ensure they have given explicit intent to mutate Jira.

### 2. Project-specific Jira report collation

Use this workflow when the user wants a polished report rather than raw query output.

Recommended process:

1. Identify the reporting scope: project, sprint, assignee set, release, age threshold, or specific issue keys.
2. Query Jira in `--raw` JSON when possible, then normalize into a stable working table.
3. Choose the report format that matches the request:
   - status rollup
   - assignee rollup
   - stale issue report
   - release risk report
   - new/closed/carry-over summary
4. Preserve important facts explicitly: issue key, owner, status, age or updated time, summary, blocker note.
5. Keep the final report short, scan-friendly, and decision-oriented.

Preferred report sections:

- Scope
- Summary
- Key changes
- Risks or blockers
- Action items

### 3. Long-unhandled Jira report

Use this workflow when the user asks for "长期未处理 Jira", "超过 N 天/周/月未处理", "stale issues", or over-age non-closed Jira reports.

Parameter extraction:

- `project`: Jira project key such as `GENEVA`. If absent, use the configured JiraCLI default project only when it is clear; otherwise ask one focused question.
- `age`: threshold such as `7d`, `1w`, `14d`, `1mo`, or Chinese inputs like `30天` and `1周`. Treat 1 week as 7 days and 1 month as 30 days.
- Optional filters: assignee, status, component, version, label, or extra JQL from the user.

Default "unhandled" definition:

- Created before the age cutoff.
- Not closed or not complete.
- For GENEVA, default to `status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved`.
- For other projects, prefer the project's known status convention. If unknown, use `status not in (Closed) AND resolution = Unresolved`.

Run the shared script for the base query:

```bash
python ../active-jira/scripts/query_stale_jiras.py --project <PROJECT> --age <AGE>
```

Useful variants:

```bash
python ../active-jira/scripts/query_stale_jiras.py --project GENEVA --age 1mo
python ../active-jira/scripts/query_stale_jiras.py --project GENEVA --age 14d
python ../active-jira/scripts/query_stale_jiras.py --project GENEVA --age 1w --assignee-current-user
python ../active-jira/scripts/query_stale_jiras.py --project GENEVA --age 1w --dry-run
```

Always keep query provenance in the report: query time, command, project, age threshold, and generated JQL. Use `--dry-run` first when you need to show or verify the generated JQL.

If the script table does not include all required report fields, enrich each matching issue with read-only detail commands:

```bash
jira issue view <ISSUE-KEY> --raw
jira issue view <ISSUE-KEY> --comments 5
```

Only read fields needed for the report: issue key, created time, assignee, status, Severity/Priority, Summary, Description, and recent comments. Do not create, edit, transition, comment on, or assign Jira issues unless the user explicitly requests that mutation.

Data handling rules:

- Query time: record local execution time as `YYYY-MM-DD HH:mm:ss <timezone>`.
- Overdue days: compute `query time - created time`, in days, with one decimal place; sort by the raw numeric value when needed.
- Urgency: prefer Jira `Severity`; fall back to `Priority`; if neither exists, mark `未设置`.
- Severity order: `P0 > P1 > P2 > P3 > P4 > 未设置/未知`. Preserve non-P values such as `Blocker`, `Critical`, `High`, `Medium`, and `Low`; map them only when project evidence or Jira priority order supports the mapping.
- Issue summary: prefer `Summary`; summarize `Description` into one sentence under about 80 Chinese characters when needed. If description is absent, use `Summary`.
- Comment summary: optional by default. Include it when the user asks, the issue count is small, or comments contain obvious risk signals such as blockers, waiting, dependency, or confirmation needed; otherwise use `-`.

Report format:

```markdown
# <PROJECT> 长期未处理 Jira 报告

## 查询信息

- 查询时间: <YYYY-MM-DD HH:mm:ss timezone>
- 项目: <PROJECT>
- 超时时间: <AGE>
- 命令: `<command>`
- JQL: `<jql>`

## 汇总

- 总数: <count>
- 最高紧急程度: <severity>
- 最久未处理: <issue key> / <days> 天
- 未分配数量: <count>

## Jira 清单

| 排序 | Jira | Severity/紧急程度 | 创建时间 | 超期时长(天) | 状态 | 责任人 | 问题摘要 | 评论摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

Sort the Jira table by severity first (`P0` first), then earlier created time, then issue key for stable output. Make Jira keys clickable when a base URL is available; otherwise show the key. If no matching issues exist, still output the query info, summary, and empty table, and state that no matching Jira issues were found. If JiraCLI fails, report the failed command and reason, then provide the copyable JQL or command instead of inventing results.

## Report formatting rules

- Default to Markdown output unless the user asks for another format.
- Prefer concise sections over long prose.
- Group by status, assignee, or risk only when that grouping helps decision-making.
- Call out blockers and overdue items explicitly.
- Separate facts from suggestions: report what Jira says first, then add recommendations.
- If there are no matching issues, say so clearly and keep the empty table when the workflow expects one.

## References

- Read `references/reporting-patterns.md` for reusable report shapes, defect-creation checklists, and field-filling rules.
- Read `../active-jira/references/jira-cli-usage.md` when you need exact JiraCLI command syntax.

## Safety and escalation

- Do not create or edit Jira issues unless the user explicitly asks for that mutation.
- For project-specific required fields, inspect comparable issues before guessing.
- If the team appears to use a strict reporting template, mirror it closely instead of inventing a new format.
- If the user request mixes generic Jira operations and formatted reporting, it is fine to use both `active-jira` and `active-jira-report` guidance in the same turn.
