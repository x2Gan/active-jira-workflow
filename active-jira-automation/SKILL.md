---
name: active-jira-automation
description: manage scenario-based Jira automation tasks for Active teams. use when the user asks to create, list, pause, resume, or delete Jira automation tasks, or to set up scheduled or one-time Jira checks that notify a Feishu/Lark group. supports the jira-scheduled-query-alert scenario, where a natural language Jira filter is confirmed as base_jql and window_mode before scheduling.
---

# Active Jira Automation

## Overview

Use this skill for Jira workflows that should run as reusable automation tasks rather than as one-off reports or manual Jira commands. This skill provides the automation control layer on top of the sibling `active-jira` and `active-lark` skills.

Current scope:

- Create automation tasks
- List existing automation tasks
- Pause, resume, and delete automation tasks
- Register and run scenario-based automation workflows
- Send Feishu/Lark interactive cards when a supported scenario matches

Current supported scenario:

- `jira-scheduled-query-alert`: run a user-confirmed Jira query on a schedule or once, then notify a target Feishu/Lark chat when matching issues are found

## Responsibility Boundary

- Keep generic Jira querying, field lookup, and raw JiraCLI usage in `../active-jira`.
- Keep generic Lark auth, chat lookup, raw API usage, and generic delivery capabilities in `../active-lark`.
- Keep automation task state, scenario registry, runner orchestration, checkpointing, dedupe, dry-run, and interactive card policy in this skill.
- Do not create a separate runner per scenario; scenarios plug into the shared runtime.

Consult these references when needed:

- `references/automation-framework.md`
- `references/task-lifecycle.md`
- `references/scenario-access-contract.md`

## Trigger Examples

- "帮我创建一个 Geneva 项目新增 P0 BUG Jira 提醒任务"
- "每小时检查一次 GENEVA 里状态仍然 Open 的 Release Blocker，并推送到测试告警群"
- "每天 10 点把本周新建且带 customer-escalation 标签的 Jira 发到项目群"
- "列出当前所有 Jira 自动任务"
- "暂停 task_id 为 geneva-p0-bug-alert 的自动提醒"
- "恢复这个 Jira 自动任务"
- "删除这个 Jira 自动化任务"

## Core Workflows

### 1. Create automation task

Use this workflow when the user wants a recurring or one-time Jira automation task.

Recommended process:

1. Identify the target scenario.
2. Collect only the missing required fields.
3. Normalize the natural language filter into `query_spec` and `base_jql`.
4. Confirm `window_mode` and scheduling semantics.
5. Resolve a chat name into a stable `oc_...` chat ID before creation when possible.
6. Show a confirmation summary before any write-side effect.
7. Create the task definition and pass scheduling work to the scheduler adapter.

P6 creation guardrails:

- 追问顺序 must be: filter target, project scope, `window_mode`, schedule, `target_chat_id` or group name, then notification policy.
- Build `query_spec` and `base_jql` during creation, but treat them as a proposal until the user accepts the confirmation summary.
- The confirmation summary must be explicit enough that the user can audit the exact Jira scope, final `base_jql`, `window_mode`, schedule, `target_chat`, and message policy.
- Do not call `manage_tasks.py create`, write task JSON, or create a scheduler job before the user confirms the summary.
- If the user only provides a group name, resolve it to a stable `target_chat_id` before creation or stop and ask for the ID.

For `jira-scheduled-query-alert`, collect or confirm in this order:

- filter target: what Jira issues to match, including issue type, status, label, version, assignee, priority, severity, or other fields
- project scope: `project` or `projects`
- window semantics: `window_mode`
- schedule: `schedule_type` and `schedule_expr`
- delivery target: `target_chat_id` or a resolvable group name
- notification policy: `notify_policy.mode`, max issues per run, and whether snapshot matches may repeat

Generate and confirm:

- `filter_prompt`: the user's original natural language intent
- `query_spec`: auditable structured query clauses
- `base_jql`: the base JQL without runtime window clauses
- `window_mode`: `created`, `updated`, or `snapshot`
- `lookback_minutes`: overlap window for scheduled runs, when applicable

The confirmation summary should include:

- task name
- scenario key: `jira-scheduled-query-alert`
- project scope
- original filter intent
- generated `base_jql`
- `window_mode` and query window explanation
- schedule type and expression
- target chat
- notification policy and max issues per run
- LLM policy: on-match only
- message template version: `lark-jira-query-alert-card-v1`

Only create the task after the user confirms the summary. Do not write a task whose `base_jql`, `window_mode`, or target chat is still ambiguous.

Window semantics:

- `created`: alert on newly created Jira issues. Runtime appends a `created` window to `base_jql`.
- `updated`: alert on recently updated Jira issues. Runtime appends an `updated` window to `base_jql`.
- `snapshot`: inspect the current set of issues matching `base_jql`. Runtime does not append a time window; dedupe and `notify_policy` must prevent unwanted repeat alerts.

### 2. List, pause, resume, delete

Use these workflows when the user wants to manage an existing automation task.

Rules:

- Prefer `task_id` for pause, resume, and delete.
- If the user only gives a task name, operate directly only when it resolves to exactly one task.
- Treat delete as destructive: show the task summary first and require explicit confirmation.

### 3. Run supported scenario logic

Current supported scenario: `jira-scheduled-query-alert`.

Execution rules:

- Build final runtime JQL from confirmed `base_jql` plus the `window_mode` query window.
- Query and dedupe deterministically before any LLM call.
- Do not call LLM when there are no matches.
- For matches, allow LLM to produce only limited summary fields.
- The final outgoing Feishu/Lark message must be an `interactive` card.
- Use `--dry-run` before delivery when the target or payload is still being validated.

## Safety Rules

- Do not let LLM decide the target chat, query rule, or message structure.
- Do not mutate Jira issues unless the user explicitly asks for Jira writes.
- Do not fall back to plain text or Markdown when a scenario requires an interactive card.
- Keep scenario behavior consistent with the shared task lifecycle and shared runner.
