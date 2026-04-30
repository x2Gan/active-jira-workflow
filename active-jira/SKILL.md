---
name: active-jira
description: query and operate Active Jira through the local open-source ankitpokhrel/jira-cli command. use when the user asks to search, view, summarize, create, edit, transition, comment on, assign, link, clone, watch, worklog, or inspect Jira issues, epics, sprints, releases, projects, boards, current user, or server info.
---

# Active Jira

## Overview

Use this skill for generic Jira access through the user's local `ankitpokhrel/jira-cli` installation. This is the low-level Jira capability layer: query issues, inspect metadata, create or edit records, transition workflow state, and return structured output.

When local execution is unavailable, provide the exact command the user should run and explain how to paste the output back. For data extraction, prefer machine-readable output such as `--raw` JSON.

Project-specific reporting workflows, defect templates, and summary formats belong in the separate `active-jira-report` skill. Keep this skill focused on reusable Jira primitives.

## JiraCLI basic capability layer

Consult `references/jira-cli-usage.md` for the full command map, flags, examples, and troubleshooting.
For Active Jira field IDs, required-field rules, and legal enum values, consult `references/active-jira-rules.md` before creating or editing issues. Prefer that frozen reference over repeatedly querying Jira metadata during normal skill use.

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

## Active field rules

Use `references/active-jira-rules.md` whenever the user asks for issue creation, issue editing, field extraction, or validation against Active Jira field conventions.

Important fixed rules from that reference:

- Use field IDs for custom fields, for example `customfield_10401` for Severity, `customfield_10404` for 报修平台, and `customfield_11000` for 发现问题阶段.
- Do not use observed raw/legacy fields for create/edit unless Jira metadata is refreshed and confirms they are editable. In particular, use `customfield_10800` for Products instead of raw `customfield_11400`, and use `customfield_10716` for 问题概率 instead of raw `customfield_10312`.
- For Active Bug creation, required fields are `project`, `issuetype`, `summary`, `security`, `customfield_10401`, `customfield_10404`, and `customfield_11000`.
- For Epic creation, also include `customfield_10103` / Epic Name. For Sub-task creation, also include `parent`.
- Do not use frozen enum values for dynamic fields such as `project`, `versions`, `fixVersions`, `components`, `customfield_10800`, `customfield_12700`, `status`, user fields, `parent`, or `customfield_10101`.
- Do not freeze or auto-fill sensitive access-control or org-ownership values such as `security` or `customfield_11801`; only query and fill them when the user explicitly asks.
- For an existing Jira, read actual values with `python active-jira/scripts/query_jira_field_options.py issue <ISSUE-KEY> --fields project,versions,fixVersions,customfield_10800,customfield_12700,status`; the helper uses local `jira issue view --raw` for this path.
- Before creating a new Jira, query and match legal values with `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields versions,fixVersions,customfield_10800,customfield_12700 --match <keyword>`; the helper uses Jira REST metadata here because JiraCLI does not expose stable createmeta/editmeta commands.
- Search visible projects with `python active-jira/scripts/query_jira_field_options.py projects --match <keyword>`; the helper uses local `jira project list` for this path.
- Only refresh Jira metadata when the project changes, a dynamic field is needed, Jira rejects a documented value, or the user explicitly asks for a metadata refresh.

## Workflow

1. Identify whether the user wants read-only access or a mutation.
2. Use `jira ... --raw` when the output will be summarized or transformed.
3. For list-style output, choose the smallest stable column set that answers the question.
4. For writes, prefer explicit arguments over interactive prompts so the action is reproducible.
5. If the request is actually a project-specific report, rule-based defect creation flow, or formatted status summary, switch to the `active-jira-report` skill instead of bloating this one.

## Prerequisites and troubleshooting

Consult `references/jira-cli-usage.md` when you need details about JiraCLI setup, `--raw`, `--csv`, `--jql/-q`, configuration files, or command-specific flags.

If `jira` cannot be found, ask the user to install `ankitpokhrel/jira-cli`, ensure it is on `PATH`, or pass `-c` / `JIRA_CONFIG_FILE` as needed.

If Jira authentication fails, ask the user to run `jira init` and verify `JIRA_API_TOKEN`, `JIRA_AUTH_TYPE`, or `JIRA_CONFIG_FILE` as appropriate for their Jira installation.

For JiraCLI setup:

```bash
jira init
jira init --installation cloud --server https://example.atlassian.net --login user@example.com --project GENEVA
jira init --installation local --server https://jira.example.com --login username --auth-type bearer --project GENEVA
```

JiraCLI supports basic auth, bearer/PAT, and mtls. For Jira Cloud, export `JIRA_API_TOKEN` before `jira init`. For on-premise PAT, export `JIRA_API_TOKEN` and set `JIRA_AUTH_TYPE=bearer`.
