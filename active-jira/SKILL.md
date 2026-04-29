---
name: active-jira
description: query and operate Active Jira through the local open-source ankitpokhrel/jira-cli command. use when the user asks to search, view, summarize, create, edit, transition, comment on, assign, link, clone, watch, worklog, or inspect Jira issues, epics, sprints, releases, projects, boards, current user, or server info. includes an Active-specific GENEVA stale non-closed Jira reporting scenario as a separate higher-level workflow.
---

# Active Jira

## Overview

Use this skill to answer Jira requests through the user's local `ankitpokhrel/jira-cli` installation. Treat JiraCLI as the basic capability layer, and treat Active/Geneva reporting recipes as higher-level scenarios built on that layer.

The assistant usually cannot access the user's local Jira unless it can run commands in the user's shell and the local JiraCLI config is authenticated. When local execution is unavailable, provide the exact command the user should run and explain how to paste the output back. For generated report scripts, use `--dry-run` to show the generated JQL and command.

## JiraCLI basic capability layer

Prefer the native `jira` command when the user asks for generic Jira information or operations. Consult `references/jira-cli-usage.md` for the full command map, flags, examples, and troubleshooting.

Global conventions:

- Use `jira ... -p PROJECT` to select a project when the user names a project key, or put `project = KEY` directly in JQL for raw searches.
- Use `jira ... -c /path/to/config.yml` or `JIRA_CONFIG_FILE=/path/to/config.yml` when the user has multiple Jira configs.
- Add `--debug` only for troubleshooting.
- For Agent parsing, prefer `--raw` JSON when available. Use `--plain --columns ... --no-headers` for simple shell pipelines.
- Use `--paginate <from>:<limit>` or `--paginate <limit>` when result size matters. JiraCLI fetches at most 100 items at a time for list-style commands.
- Only perform mutating commands when the user clearly asks to create, update, transition, comment, assign, link, delete, add to epic/sprint, close sprint, or log work. For ambiguous requests, query first.

Core query and read commands:

```bash
jira issue list --raw -q '<JQL>'
jira issue list --plain --columns key,assignee,status,created,summary --no-headers -q '<JQL>'
jira issue view ISSUE-1 --raw
jira issue view ISSUE-1 --comments 5
jira epic list --table --plain
jira epic list EPIC-1 --plain --columns type,key,summary,status
jira sprint list --table --plain --columns id,name,start,end,state
jira sprint list --current --plain --columns key,assignee,status,summary
jira release list -p PROJECT
jira project list
jira board list -p PROJECT
jira me
jira serverinfo
```

Common `jira issue list` filters:

```bash
jira issue list -a$(jira me)                 # assigned to me
jira issue list -ax                          # unassigned
jira issue list -w                           # watched by me
jira issue list -s"In Progress" -yHigh       # status and priority
jira issue list -s~Done --created-before -24w -a~x
jira issue list --created week
jira issue list --updated -30m
jira issue list -q 'project = GENEVA AND summary ~ "crash"'
```

Use these mutating commands only for explicit user intent:

```bash
jira issue create -tTask -s"Summary" -b"Description" --no-input
jira issue edit ISSUE-1 -s"New summary" --no-input
jira issue move ISSUE-1 "In Progress" --comment "Started working on it"
jira issue assign ISSUE-1 $(jira me)
jira issue comment add ISSUE-1 "Comment body"
jira issue worklog add ISSUE-1 "1h 30m" --comment "Investigation" --no-input
jira issue link ISSUE-1 ISSUE-2 Blocks
jira issue link remote ISSUE-1 https://example.com "Reference"
jira issue unlink ISSUE-1 ISSUE-2
jira issue clone ISSUE-1 -s"Modified summary"
jira issue watch ISSUE-1 $(jira me)
jira epic create -n"Epic name" -s"Epic summary" --no-input
jira epic add EPIC-1 ISSUE-1 ISSUE-2
jira epic remove ISSUE-1 ISSUE-2
jira sprint add SPRINT_ID ISSUE-1 ISSUE-2
jira sprint close SPRINT_ID
```

High-risk destructive command:

```bash
jira issue delete ISSUE-1
jira issue delete ISSUE-1 --cascade
```

Before deletion, make sure the user explicitly asked for deletion and understands the issue key and cascade scope.

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

When the user says "超过[duration]没有关闭", interpret it as Jira issues created on or before the local cutoff date and not closed according to the Active/Geneva workflow.

## Active/Geneva status semantics

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

Default query for `GENEVA` and `1w` uses an absolute date plus Active/Geneva status semantics:

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

- Default `--closed-mode active-statuses`: `status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved`
- `--closed-mode active-statuses-no-resolution`: same status whitelist without a resolution clause
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

Use `--statuses` to override the Active open-status whitelist, for example:

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

For JiraCLI setup:

```bash
jira init
jira init --installation cloud --server https://example.atlassian.net --login user@example.com --project GENEVA
jira init --installation local --server https://jira.example.com --login username --auth-type bearer --project GENEVA
```

JiraCLI supports basic auth, bearer/PAT, and mtls. For Jira Cloud, export `JIRA_API_TOKEN` before `jira init`. For on-premise PAT, export `JIRA_API_TOKEN` and set `JIRA_AUTH_TYPE=bearer`.

If Jira returns a JQL parse error, ask the user to run `--dry-run` and try these fallback modes in order:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w --dry-run
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode active-statuses-no-resolution --dry-run
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
