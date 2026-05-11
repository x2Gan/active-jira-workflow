---
name: active-jira-automation
description: manage scenario-based Jira automation tasks for Active teams. use when the user asks to create, list, pause, resume, or delete Jira automation tasks, or to set up scheduled or one-time Jira checks that notify a Feishu/Lark group, such as alerting a chat when new P0 bug Jira issues are created.
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

- `new-p0-bug-alert`: query newly created P0 bug Jira issues and notify a target Feishu/Lark chat

## Responsibility Boundary

- Keep generic Jira querying, field lookup, and raw JiraCLI usage in `../active-jira`.
- Keep generic Lark auth, chat lookup, raw API usage, and generic delivery capabilities in `../active-lark`.
- Keep automation task state, scenario registry, runner orchestration, checkpointing, and interactive card policy in this skill.
- Do not create a separate runner per scenario; scenarios plug into the shared runtime.

Consult these references when needed:

- `references/automation-framework.md`
- `references/task-lifecycle.md`
- `references/scenario-access-contract.md`

## Trigger Examples

- "帮我创建一个 Geneva 项目新增 P0 BUG Jira 提醒任务"
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
3. Normalize the request into structured task config.
4. Resolve a chat name into a stable `oc_...` chat ID before creation when possible.
5. Show a confirmation summary before any write-side effect.
6. Create the task definition and pass scheduling work to the scheduler adapter.

For `new-p0-bug-alert`, collect or confirm:

- `project`
- `query_rule`
- `schedule_type`
- `schedule_expr`
- `target_chat_id` or a resolvable group name

The confirmation summary should include:

- task name
- scenario key
- project
- query rule
- schedule type and expression
- target chat
- LLM policy
- message template version

### 2. List, pause, resume, delete

Use these workflows when the user wants to manage an existing automation task.

Rules:

- Prefer `task_id` for pause, resume, and delete.
- If the user only gives a task name, operate directly only when it resolves to exactly one task.
- Treat delete as destructive: show the task summary first and require explicit confirmation.

### 3. Run supported scenario logic

Current supported scenario: `new-p0-bug-alert`.

Execution rules:

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