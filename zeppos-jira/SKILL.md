---
name: zeppos-jira
description: query zeppos jira information through the local open-source ankitpokhrel/jira-cli command. use when the user asks to search jira tickets, especially geneva project tickets that have not been closed for a duration such as 1 week, 1 month, or n days, and wants a table containing jira key, assignee, status, created time, and issue summary. supports zeppos-specific geneva status workflows and future jira reporting scenarios by constructing jql and using the bundled wrapper script.
---

# ZeppOS Jira

## Overview

Use this skill to answer Jira reporting requests by wrapping the user's local `ankitpokhrel/jira-cli` installation. The first supported scenario is stale, non-closed Jira issues in the `GENEVA` project for a user-specified age window.

The assistant usually cannot access the user's local Jira directly. When local execution is unavailable, provide the exact command the user should run and explain how to paste the output back, or use `--dry-run` to show the generated JQL and command.

## Primary scenario: stale non-closed GENEVA Jira issues

Trigger examples:

- "帮我查询GENEVA项目超过1周没有关闭的Jira"
- "查一下 GENEVA 超过1个月未关闭的 Jira"
- "show GENEVA Jira issues older than 14 days that are not closed"

Use the bundled script:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w
```

Common variants:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1mo
python scripts/query_stale_jiras.py --project GENEVA --age 14d
python scripts/query_stale_jiras.py --project GENEVA --age 1w --assignee-current-user
python scripts/query_stale_jiras.py --project GENEVA --age 1w --extra-jql 'issuetype != Epic'
python scripts/query_stale_jiras.py --project GENEVA --age 1w --config /path/to/jira_config.yaml
python scripts/query_stale_jiras.py --project GENEVA --age 1w --dry-run
```

The script prints a Markdown table with exactly these columns:

| Jira | Assignee | Status | Created | Summary |
| --- | --- | --- | --- | --- |

## Duration parsing

Map natural durations to `--age`:

- 1 week / 1周 / 7 days: `--age 1w` or `--age 7d`
- 2 weeks / 2周: `--age 2w`
- 1 month / 1个月: `--age 1mo` (normalized to 30 days)
- N days / N天: `--age Nd`

When the user says "超过[duration]没有关闭", interpret it as Jira issues created on or before the local cutoff date and not closed according to the ZeppOS/Geneva workflow.

## ZeppOS/Geneva status semantics

The Geneva Jira workflow statuses observed from the user's Jira filter are:

```text
Open, In Progress, Reopened, Resolved, Closed, In Review, Pending
```

For stale "not closed" issues, default to the status whitelist excluding `Closed` and use the Jira instance's unresolved literal:

```jql
status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved
```

This is the default because the user's Jira instance rejected the previous `statusCategory`-based JQL, and the user's known-good filter uses `resolution = Unresolved` rather than `resolution IS EMPTY`.

Do not add `assignee in (currentUser())` unless the user asks for "assigned to me", "我的", or explicitly wants current-user scope. Use `--assignee-current-user` for that case.

## JQL construction

Default query for `GENEVA` and `1w` uses an absolute date plus ZeppOS/Geneva status semantics:

```jql
project = GENEVA AND created <= "YYYY-MM-DD" AND status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved
```

The script sorts rows locally by `Created`, ascending by default. It intentionally does not append `ORDER BY` to the default JQL because some Jira parsers report syntax errors at `ORDER BY` when the preceding clause is not accepted.

Date cutoff options:

- Default `--date-mode absolute`: `created <= "YYYY-MM-DD"`
- `--date-mode relative`: `created <= -7d`
- `--date-mode start-of-day`: `created <= startOfDay("-7d")`
- `--date-mode start-of-day-unquoted`: `created <= startOfDay(-7d)`

Non-closed definition options:

- Default `--closed-mode zeppos-statuses`: `status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved`
- `--closed-mode zeppos-statuses-no-resolution`: same status whitelist without a resolution clause
- `--closed-mode status-not-closed`: `status not in (Closed) AND resolution = Unresolved`
- `--closed-mode status-not-closed-no-resolution`: `status not in (Closed)`
- `--closed-mode resolution-unresolved`: `resolution = Unresolved`
- `--closed-mode resolution-empty`: `resolution IS EMPTY`
- `--closed-mode resolution-null`: `resolution = NULL`
- `--closed-mode status-category`: `statusCategory IN ("To Do", "In Progress")`
- `--closed-mode status-category-alias`: `statusCategory IN (New, Indeterminate)`
- `--closed-mode status-category-not-done`: `statusCategory != "Done"`
- `--closed-mode status-category-not-complete`: `statusCategory != Complete`
- `--closed-mode both`: `resolution = Unresolved AND statusCategory IN ("To Do", "In Progress")`

Use `--statuses` to override the ZeppOS open-status whitelist, for example:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w --statuses 'Open,In Progress,Reopened,In Review,Pending'
```

Use `--closed-statuses` with `status-not-closed` modes if additional closed-like statuses appear later.

Use `--extra-jql` to extend the query without editing the script. Use `--include-jql-order` only if the Jira instance accepts the generated query and server-side ordering is required.

## Workflow

1. Parse the user's project key and duration. Default to project `GENEVA` when the user asks for GENEVA or omits project in this workflow.
2. If the user asks for "my Jira", "assigned to me", or "我的", add `--assignee-current-user`.
3. Run the wrapper script when the environment has access to the user's local shell and JiraCLI configuration.
4. If local JiraCLI is unavailable, return the exact command for the user to run locally.
5. Preserve the script's Markdown table output. Do not reformat into bullets unless the user asks.
6. If the user pastes raw JSON from `jira issue list --raw`, save it to a temporary file and run:

```bash
python scripts/query_stale_jiras.py --input-json /path/to/raw.json
```

## Prerequisites and troubleshooting

Consult `references/jira-cli-usage.md` when you need details about JiraCLI setup, `--raw`, `--csv`, `--jql/-q`, configuration files, date cutoff modes, or closed-status semantics.

If the script reports that `jira` cannot be found, ask the user to install `ankitpokhrel/jira-cli`, ensure it is on `PATH`, or pass `--jira-bin /path/to/jira`.

If Jira authentication fails, ask the user to run `jira init` and verify `JIRA_API_TOKEN`, `JIRA_AUTH_TYPE`, or `JIRA_CONFIG_FILE` as appropriate for their Jira installation.

If Jira returns a JQL parse error, ask the user to run `--dry-run` and try these fallback modes in order:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w --dry-run
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode zeppos-statuses-no-resolution --dry-run
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode status-not-closed --dry-run
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode resolution-unresolved --dry-run
```

## Extension pattern

For future scenarios, keep the same structure:

1. Define a natural-language trigger.
2. Translate parameters into conservative JQL.
3. Use `jira issue list --raw -q '<JQL>'` where possible.
4. Parse the raw JSON into a small, explicit Markdown table.
5. Add options rather than hard-coding workflow-specific filters.

Prefer adding new wrapper scripts only when output columns, parsing logic, or JQL generation differ materially from `scripts/query_stale_jiras.py`.
