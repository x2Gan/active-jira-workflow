---
name: active-jira-automation
description: openclaw-native Jira automation skill for Active teams. use when the user wants OpenClaw to guide the creation of a reusable Jira scheduled check, design auditable JQL from natural language, and run deterministic shared scripts that notify a Feishu/Lark group when issues match.
---

# Active Jira Automation

## Overview

Use this skill when the user wants OpenClaw itself to create and run a Jira automation task through its native scheduling and session model. This skill does not own the scheduler, persistent cron store, or OpenClaw session lifecycle. Instead, it provides the OpenClaw-facing creation workflow, JQL design rules, execution prompt contract, and reusable scripts for deterministic runtime execution.

Current scope:

- Guide the user through OpenClaw-native task creation
- Turn natural language filter intent into auditable `query_spec` and `base_jql`
- Produce a confirmation summary that OpenClaw can turn into a scheduled job
- Provide deterministic reusable scripts for query execution, dedupe, rendering, and Lark delivery
- Support the `jira-scheduled-query-alert` scenario

Current supported scenario:

- `jira-scheduled-query-alert`: OpenClaw collects and normalizes the user's Jira filter and schedule, confirms the task spec, then runs the shared runtime on schedule and sends Feishu/Lark interactive cards when matches are found

## OpenClaw Host Model

- OpenClaw owns schedule persistence, cron or at semantics, timezone handling, session type, retries, and announce behavior.
- This skill owns the interview flow, JQL proposal rules, confirmation summary, runtime invariants, and reusable scripts.
- Prefer OpenClaw `session isolated` for scheduled execution of this skill. Use a named persistent session only when the user explicitly wants memory across runs.
- Treat OpenClaw's scheduled job message as a stable execution contract. It must reference confirmed task fields; it must not ask the model to reinterpret the user's intent from scratch.
- If the scheduled run already posts to a target Lark group, keep OpenClaw announce output compact. Do not duplicate full issue content in two places unless the user asks for it.

## Responsibility Boundary

- Keep generic Jira querying, field lookup, and raw JiraCLI usage in `../active-jira`.
- Keep generic Lark auth, chat lookup, raw API usage, and generic delivery capabilities in `../active-lark`.
- Keep scenario-specific JQL normalization, query and runtime invariants, dedupe identity, and interactive card rendering policy in this skill.
- Do not make this skill the source of truth for cron jobs, pause or resume state, or scheduler history. Those belong to OpenClaw.
- Treat `scripts/manage_tasks.py`, `scripts/task_store.py`, and `scripts/scheduler_adapter.py` as local development or test harnesses, not the primary OpenClaw product path.

Consult these references when needed:

- `references/automation-framework.md`
- `references/task-lifecycle.md`
- `references/scenario-access-contract.md`
- `../doc/active-jira-automation 定时查询并提醒场景设计.md`

## Trigger Examples

- "帮我在 OpenClaw 里创建一个每小时检查 Geneva 新增 P0 Bug 的定时任务"
- "每周一早上汇总 GENEVA 一周未关闭的 blocker，并推到项目群"
- "每天 10 点提醒本周新建且带 customer-escalation 标签的 Jira"
- "把这个 Jira 自动提醒改成 snapshot 模式"
- "查看这个 OpenClaw Jira 定时任务的执行配置"
- "删除这个 OpenClaw Jira 提醒"

## Core Workflows

### 1. OpenClaw-native creation workflow

Use this workflow when the user wants OpenClaw to create a recurring or one-time Jira automation task.

Recommended process:

1. Identify the target scenario.
2. Collect only the missing required fields.
3. Normalize the natural language filter into `query_spec` and `base_jql`.
4. Confirm `window_mode`, schedule, timezone, and delivery target.
5. Show a fixed confirmation summary before any scheduler write.
6. After user confirmation, ask OpenClaw to create the scheduled job using its native scheduling mechanism.
7. Store or serialize only the confirmed task spec needed by the execution prompt.

Creation guardrails:

- 追问顺序 must be: filter target, project scope, `window_mode`, schedule, timezone, `target_chat_id` or group name, then notification policy.
- Build `query_spec` and `base_jql` during creation, but treat them as a proposal until the user accepts the confirmation summary.
- The confirmation summary must be explicit enough that the user can audit the exact Jira scope, final `base_jql`, `window_mode`, schedule, timezone, target chat, OpenClaw session mode, and message policy.
- Do not ask the scheduled execution prompt to regenerate JQL, resolve a chat, or decide whether to notify.
- If the user only provides a group name, resolve it to a stable `target_chat_id` before creation or stop and ask for the ID.
- Default to OpenClaw `session isolated` for this scenario.

For `jira-scheduled-query-alert`, collect or confirm in this order:

- filter target: what Jira issues to match, including issue type, status, label, version, assignee, priority, severity, or other fields
- project scope: `project` or `projects`
- window semantics: `window_mode`
- schedule: `schedule_type` and `schedule_expr`
- timezone: default `Asia/Shanghai` unless the user explicitly wants another timezone
- delivery target: `target_chat_id` or a resolvable group name
- notification policy: `notify_policy.mode`, max issues per run, and whether snapshot matches may repeat

Generate and confirm:

- `task_name`: user-facing OpenClaw job name
- `filter_prompt`: the user's original natural language intent
- `query_spec`: auditable structured query clauses
- `base_jql`: the base JQL without runtime window clauses
- `window_mode`: `created`, `updated`, or `snapshot`
- `lookback_minutes`: overlap window for scheduled runs, when applicable
- `schedule_type` and `schedule_expr`
- `timezone`
- `openclaw_session`: default `isolated`
- `target_chat_id`
- `notify_policy`

The confirmation summary should include:

- task name
- scenario key: `jira-scheduled-query-alert`
- project scope
- original filter intent
- generated `base_jql`
- `window_mode` and query window explanation
- schedule type and expression
- timezone
- OpenClaw session mode
- target chat
- notification policy and max issues per run
- LLM policy: on-match only
- message template version: `lark-jira-query-alert-card-v1`

Only create the OpenClaw scheduled job after the user confirms the summary.

Window semantics:

- `created`: alert on newly created Jira issues. Runtime appends a `created` window to `base_jql`.
- `updated`: alert on recently updated Jira issues. Runtime appends an `updated` window to `base_jql`.
- `snapshot`: inspect the current set of issues matching `base_jql`. Runtime does not append a time window; dedupe and `notify_policy` must prevent unwanted repeat alerts.

### 2. OpenClaw management workflow

Use this workflow when the user wants to inspect, edit, pause, resume, run, or delete an existing scheduled Jira automation task.

Rules:

- Let OpenClaw remain the source of truth for job listing, status, execution history, pause or resume, and deletion.
- Use the skill only to interpret or regenerate the business payload: `query_spec`, `base_jql`, `window_mode`, target chat, card policy, or execution prompt.
- Treat delete as destructive: show the task summary first and require explicit confirmation.
- For edits, regenerate the confirmation summary and only then ask OpenClaw to update the scheduled job.

### 3. Scheduled execution workflow

Current supported scenario: `jira-scheduled-query-alert`.

Execution rules:

- Build final runtime JQL from confirmed `base_jql` plus the `window_mode` query window.
- Query only Jira keys plus window identity fields (`created_at`/`updated_at`) first.
- Dedupe and apply `notify_policy.max_issues_per_run` before fetching details.
- Fetch card fields by Jira key through the active-jira layer or local `jira issue view <KEY> --raw`.
- Do not call LLM when there are no matches.
- For matches, allow LLM to produce only limited summary fields.
- The final outgoing Feishu/Lark message must be an `interactive` card.
- Use `--dry-run` before delivery when the target or payload is still being validated.

## OpenClaw Prompt Contract

### Creation-phase prompt contract

When OpenClaw is guiding the user, the conversation must:

- ask only for missing required fields
- propose `query_spec` and `base_jql`, never silently finalize them
- present a fixed confirmation summary before creating a schedule
- mention the exact execution mode OpenClaw will use

### Scheduled execution prompt contract

Prefer a scheduled message with this structure:

```text
你正在执行 active-jira-automation 的 jira-scheduled-query-alert 定时任务。
这是已确认配置，不允许重新解释用户意图，不允许修改 JQL、群组或消息结构。

task_name: <TASK_NAME>
scenario_key: jira-scheduled-query-alert
project: <PROJECT_OR_PROJECTS>
filter_prompt: <ORIGINAL_INTENT>
query_spec: <JSON_OBJECT>
base_jql: <CONFIRMED_BASE_JQL>
window_mode: <created|updated|snapshot>
lookback_minutes: <INT>
schedule_type: <recurring|once>
schedule_expr: <EXPR>
timezone: <IANA_TZ>
target_chat_id: <oc_xxx>
notify_policy: <JSON_OBJECT>
message_template_key: lark-jira-query-alert-card-v1

执行要求：
1. 仅使用确认后的配置运行共享脚本。
2. 先进行确定性 Jira 查询与去重，再决定是否需要调用 LLM。
3. 命中后输出或发送 interactive card；未命中则返回无命中摘要。
4. 不得改写 base_jql，不得重新选择 target_chat_id。
```

If OpenClaw supports structured payload injection, prefer structured fields over free-form text. The goal is a stable execution contract, not a creative prompt.

## JQL Design Rules

- `base_jql` contains only business filters. Never bake runtime `created` or `updated` windows into `base_jql`.
- `query_spec` must remain auditable and should capture the same intent as `base_jql`.
- Use `window_mode=created` by default for reminder-style tasks unless the user clearly asks for updated or snapshot semantics.
- Default `lookback_minutes=5` to absorb scheduler jitter; rely on dedupe rather than widening the JQL semantics.
- For `snapshot` tasks, require an explicit `notify_policy.repeat_snapshot` decision or document the default.
- Resolve ambiguous user language into explicit Jira clauses before confirmation.

## Reusable Assets

Use these scripts as reusable building blocks inside OpenClaw-hosted flows:

- `scripts/scenarios/jira_scheduled_query_alert.py`: scenario contract, config schema, defaulting rules, normalizer, identity, renderer binding
- `scripts/jira_query_runtime.py`: final JQL construction and query window handling
- `scripts/run_automation_task.py`: shared deterministic runner entrypoint for local or host-driven execution
- `scripts/templates/lark_jira_query_alert_card_v1.py`: interactive card rendering
- `scripts/lark_delivery_runtime.py`: Lark delivery runtime
- `scripts/llm_summary_runtime.py`: constrained match-summary generation

## Safety Rules

- Do not let LLM decide the target chat, query rule, or message structure.
- Do not mutate Jira issues unless the user explicitly asks for Jira writes.
- Do not fall back to plain text or Markdown when a scenario requires an interactive card.
- Keep scheduled execution deterministic: confirmed config in, shared scripts out.
- Do not treat local task store state as authoritative when OpenClaw already owns the job.
- If the host cannot resolve a stable `target_chat_id`, stop and ask rather than scheduling an ambiguous job.
