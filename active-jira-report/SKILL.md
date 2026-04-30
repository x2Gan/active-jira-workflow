---
name: active-jira-report
description: create project-specific Jira reports and rule-based Jira issue drafts for Active teams. use when the user asks for formatted Jira summaries, stale or long-unhandled issue reports such as "帮我查询 GENEVA 项目超过 1 周未处理的 Jira 情况", weekly or release reports, issue rollups by assignee or status, project-specific report templates, or creation of new bug Jira issues with required fields, custom fields, labels, components, or other project conventions.
---

# Active Jira Report

## Overview

Use this skill for Jira workflows that are shaped by project rules rather than by raw Jira mechanics. Typical cases include formatted status reports, release or sprint rollups, stale issue summaries, and creating new defects or tasks with project-specific fields filled according to local conventions.

This skill assumes the generic Jira command layer is available through the sibling `active-jira` skill. In practice, use local `jira` commands directly here, and read `../active-jira/references/jira-cli-usage.md` when you need exact CLI syntax.

For Active Jira field IDs, required-field rules, and legal enum values, read `references/active-jira-rules.md` before drafting or validating Jira creation/editing guidance. The same rules are duplicated in the sibling `active-jira` skill because `doc/` is not available to skills at runtime.

Keep this skill focused on:

- Project-specific report structures and summarization rules
- Rule-based issue creation flows
- Field-filling conventions and custom field discovery
- Reusable Markdown report formats for teams

Script boundary:

- Keep generic Jira mechanics and reusable base-query helpers in `../active-jira`.
- Treat `../active-jira/scripts/query_stale_jiras.py` as a base stale-query/JQL helper, not as a complete project-report generator.
- Do not move that script into this skill unless it becomes report-specific and stops being useful as a generic Jira helper.
- Use `scripts/generate_stale_jira_report.py` for deterministic long-unhandled Jira reports. It has no default project or age; pass both from the user's trigger phrase.
- Use `scripts/publish_stale_jira_report_to_lark.py` when the user asks to publish a long-unhandled Jira report to a Lark/Feishu document or send the document link to a known Lark chat.

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
- Prefer the frozen field and enum rules in `references/active-jira-rules.md` over repeated metadata queries during normal operation.
- For Active Bug creation, require `project`, `issuetype`, `summary`, `security`, `customfield_10401`, `customfield_10404`, and `customfield_11000`.
- Use `customfield_10401` for Severity, `customfield_10800` for Products, and `customfield_10716` for 问题概率. Do not use raw/legacy fields such as `customfield_11400` or `customfield_10312` in create/edit commands unless Jira metadata has just confirmed they are editable.
- Do not rely on fixed enum values for dynamic fields such as project, versions, fix versions, components, Products, planned version, status, user fields, parent, or epic link. For existing issues, read actual values with `python active-jira/scripts/query_jira_field_options.py issue <ISSUE-KEY> --fields ...`, which uses local `jira issue view --raw`; before creating issues, query legal options with `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields ... --match <keyword>`, which uses Jira REST metadata because JiraCLI does not expose stable createmeta/editmeta commands.
- Treat `security` and `customfield_11801` as sensitive fields: do not freeze their concrete values in reports or auto-fill them during issue preparation unless the user explicitly requests that work.
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

Execution contract:

- This workflow must produce a rule-compliant report, not just a raw query table.
- Never trust a single `jira issue list` call as complete when result size matters. JiraCLI list commands page at 100 issues; fetch all pages before reporting totals.
- Do not use the current `query_stale_jiras.py` table as the final report when the required fields include Severity, overdue duration, ranking, or comments. Use `generate_stale_jira_report.py` for the full report.
- Project and age are mandatory trigger parameters. Do not silently default to `GENEVA`, `1w`, or the JiraCLI default project; if either is missing, ask one focused question before running the report generator.
- Prefer read-only commands. Do not create, edit, transition, comment on, or assign Jira issues unless the user explicitly requests a mutation.

Parameter extraction:

- `project`: Jira project key such as `GENEVA`, extracted from the user's trigger phrase. If absent, ask one focused question.
- `age`: threshold such as `7d`, `1w`, `14d`, `1mo`, or Chinese inputs like `30天` and `1周`, extracted from the user's trigger phrase. Treat 1 week as 7 days and 1 month as 30 days. If absent, ask one focused question.
- Optional filters: assignee, status, component, version, label, or extra JQL from the user.

Default "unhandled" definition:

- Created before the age cutoff.
- Not closed or not complete.
- For GENEVA, default to `status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved`.
- For other projects, prefer the project's known status convention. If unknown, use `status not in (Closed) AND resolution = Unresolved`.

After extracting `project` and `age`, use the report generator:

```bash
python active-jira-report/scripts/generate_stale_jira_report.py --project <PROJECT> --age <AGE>
```

Useful explicit examples:

```bash
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 14d --assignee-current-user
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1mo --dry-run
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w --output reports/geneva-stale-jira.md
```

Useful generator options:

- `--output <FILE>`: write the Markdown report to a file instead of stdout.
- `--comments none|top|all`: default is `none`; use `top --comments-top <N>` for only the highest-risk rows.
- `--enrich-details missing-severity|all|none`: default is `missing-severity`, so Priority does not prevent fetching a missing true Severity field.
- `--severity-field <FIELD_OR_PATH>`: add a project-specific Severity field path when known.
- `--highlight-limit <N>`: default is `5`; controls how many issues appear in the opening Highlight.
- `--input-json <FILE_OR_->`: generate a report from saved Jira raw JSON without querying live Jira, useful for testing or replay.

### 4. Publish long-unhandled Jira report to Lark

Use this workflow only when the user explicitly asks to create a Lark/Feishu document, send a message, grant document permission, or otherwise publish outside Jira. Publishing and messaging are external side effects.

Recommended command for creating a document and returning its URL:

```bash
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py --project <PROJECT> --age <AGE>
```

Recommended dry-run before sending to a chat:

```bash
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py \
  --project GENEVA \
  --age 1w \
  --chat-id oc_xxx \
  --grant-chat-view \
  --dry-run
```

Execute without `--dry-run` only after the target chat is clear:

```bash
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py \
  --project GENEVA \
  --age 1w \
  --chat-id oc_xxx \
  --grant-chat-view
```

Publishing behavior:

- The script writes a local Markdown report first, defaulting to `reports/<project>-stale-jira-<age>-<timestamp>.md`.
- It creates a new Lark document by default; pass `--doc <DOC_URL_OR_TOKEN> --doc-command append|overwrite` to update an existing document.
- Pass `--parent-token` or `--parent-position` when the document must be created in a specific Drive folder or Wiki location.
- `--chat-id oc_xxx` sends the published document link with `lark-cli im +messages-send --as bot`.
- `--grant-chat-view` grants the target chat view permission before sending, using the published document token.
- Unknown options are forwarded to `generate_stale_jira_report.py`, so report filters such as `--comments top`, `--assignee-current-user`, or `--input-json` still work.

Safety rules:

- Do not guess a Lark chat. Resolve it first with `lark-cli im +chat-search --query '<name>'` or ask the user for a stable `oc_...` chat ID.
- Run `--dry-run` before the first send to a new chat or when document permission is uncertain.
- If `lark-cli` reports missing IM scopes, ask the user to authorize the exact scopes shown by the CLI or use bot identity only when the bot is already configured for that chat.
- Do not make a document public by default. Prefer granting view permission to the explicit target chat when needed.

Always keep query provenance in the report: query time, command, project, age threshold, and generated JQL.

The generator performs the two-stage query process internally:

1. Generate and inspect the JQL with `--dry-run`.
2. Fetch all matching issues with explicit JiraCLI pagination, 100 at a time:

```bash
jira issue list --raw --paginate 0:100 -q '<JQL>'
jira issue list --raw --paginate 100:100 -q '<JQL>'
jira issue list --raw --paginate 200:100 -q '<JQL>'
```

Continue until a page returns fewer than 100 issues. Merge the raw JSON pages into one working set before computing counts, sorting, or summaries. If the generator fails, report the failed command and generated JQL rather than inventing results.

If the script table does not include all required report fields, enrich each matching issue with read-only detail commands:

```bash
jira issue view <ISSUE-KEY> --raw
jira issue view <ISSUE-KEY> --comments 5
```

Only read fields needed for the report: issue key, created time, assignee, status, Severity/Priority, Summary, Description, and recent comments. Do not create, edit, transition, comment on, or assign Jira issues unless the user explicitly requests that mutation.

Field discovery and enrichment:

- Inspect several representative issues with `jira issue view <ISSUE-KEY> --raw` before finalizing Severity mapping, especially when the target project differs from the frozen Active Jira rules.
- Prefer a true Jira `Severity` field. If field names are not exposed, look for project evidence in custom fields; in the current Active Jira rules, `customfield_10401.value` is the Severity field, but confirm it if Jira rejects the value or the project metadata differs.
- Fall back to `Priority` only when no usable Severity field is present.
- For large result sets, collect complete base fields for all issues, then enrich only the fields that are mandatory for the report. Comments may be sampled or limited by policy, but Severity and sorting inputs must be stable for every listed issue.
- If comments are too expensive to fetch for every issue, state the comment policy in the report and use `-` for issues whose comments were not fetched.

Data handling rules:

- Query time: record local execution time as `YYYY-MM-DD HH:mm:ss <timezone>`.
- Overdue days: compute `query time - created time`, in days, with one decimal place; sort by the raw numeric value when needed.
- Urgency: prefer Jira `Severity`; fall back to `Priority`; if neither exists, mark `未设置`.
- Severity order: `P0 > P1 > P2 > P3 > P4 > 未设置/未知`. Preserve non-P values such as `Blocker`, `Critical`, `High`, `Medium`, and `Low`; map them only when project evidence or Jira priority order supports the mapping.
- Issue summary: prefer `Summary`; summarize `Description` into one sentence under about 80 Chinese characters when needed. If description is absent, use `Summary`.
- Comment summary: optional by default. Include it when the user asks, the issue count is small, or comments contain obvious risk signals such as blockers, waiting, dependency, or confirmation needed; otherwise use `-`.
- Highlight: place it near the beginning, immediately after query info and before the full Jira list. It should help a PM or PL quickly see which issues most deserve immediate repair or ownership confirmation. Select Highlight issues by comprehensive risk: urgency rank first, then status risk (`Reopened`, `Open`, `In Progress`, `Pending`, `Resolved`, `In Review`), then unassigned issues, then longer overdue duration. Include a short reason for each highlighted issue.
- Count integrity: report totals only after all pages have been fetched. If pagination fails midway, report the partial status explicitly instead of presenting a final total.

Report format:

```markdown
# <PROJECT> 长期未处理 Jira 报告

## 查询信息

- 查询时间: <YYYY-MM-DD HH:mm:ss timezone>
- 项目: <PROJECT>
- 超时时间: <AGE>
- 命令: `<command>`
- JQL: `<jql>`

## Highlight

建议 PL/项目经理优先推动以下 Jira 的修复或责任确认；排序依据为紧急程度、状态风险、是否未分配责任人和超期天数。

| Jira | 紧急程度 | 超期天数 | 状态 | 责任人 | 推荐理由 | 摘要 |
| --- | --- | --- | --- | --- | --- | --- |

## Jira 清单

| 排序 | Jira | Severity/紧急程度 | 创建时间 | 超期时长(天) | 状态 | 责任人 | 问题摘要 | 评论摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 汇总

总数: <count>
状态分布: <status count list>
紧急程度: <urgency count list>
未分配: <count>
最久未处理: <issue key>，<days> 天

### 责任人数量 Top 5

| 责任人 | 数量 |
| --- | --- |

### 最久未处理 Top 5

| Jira | 紧急程度 | 超期天数 | 状态 | 责任人 | 摘要 |
| --- | --- | --- | --- | --- | --- |

<comment policy>；紧急程度来源: <severity/priority source>。
```

Place the summary at the end of the generated document, after the full Jira list, so readers can inspect the details first and then scan aggregate numbers. The summary must include total count, status distribution, urgency distribution, unassigned count, oldest issue, assignee Top 5 excluding `Unassigned`, oldest-issue Top 5, comment policy, and urgency source. Sort status distribution by count descending; sort urgency distribution by the same urgency rank used by the issue table.

The opening Highlight is a short decision aid, not a replacement for the full table. Keep it concise enough for PM/PL reporting, and use facts already available in the report: Jira key, urgency, overdue days, status, owner, summary, and a one-sentence reason. If no matching issues exist, keep the Highlight section and state that no issue needs immediate follow-up.

Sort the Jira table by severity first (`P0` first), then earlier created time, then issue key for stable output. Make Jira keys clickable when a base URL is available; otherwise show the key. If no matching issues exist, still output the query info, empty table, and end-of-document summary, and state that no matching Jira issues were found. If JiraCLI fails, report the failed command and reason, then provide the copyable JQL or command instead of inventing results.

Final validation checklist:

- Query provenance is present: time, project, age threshold, command, and JQL.
- Opening Highlight exists after query info and contains the most urgent issues plus concise reasons.
- Pagination was completed or any incomplete pagination is disclosed.
- End-of-document summary contains total count, status distribution, urgency distribution, unassigned count, oldest issue, assignee Top 5, oldest-issue Top 5, comment policy, and urgency source.
- Table has exactly the required nine columns.
- Severity source is documented or inferable, and sorting follows Severity, created time, then Jira key.
- Comment-summary policy is clear when comments are omitted or partially fetched.

## Report formatting rules

- Default to Markdown output unless the user asks for another format.
- Prefer concise sections over long prose.
- Group by status, assignee, or risk only when that grouping helps decision-making.
- Call out blockers and overdue items explicitly.
- Separate facts from suggestions: report what Jira says first, then add recommendations.
- If there are no matching issues, say so clearly and keep the empty table when the workflow expects one.

## References

- Read `references/active-jira-rules.md` for Active Jira field IDs, issue-type required fields, categories, enum values, and raw-field caveats.
- Read `references/reporting-patterns.md` for reusable report shapes, defect-creation checklists, and field-filling rules.
- Read `../active-jira/references/jira-cli-usage.md` when you need exact JiraCLI command syntax.

## Safety and escalation

- Do not create or edit Jira issues unless the user explicitly asks for that mutation.
- For project-specific required fields, inspect comparable issues before guessing.
- If the team appears to use a strict reporting template, mirror it closely instead of inventing a new format.
- If the user request mixes generic Jira operations and formatted reporting, it is fine to use both `active-jira` and `active-jira-report` guidance in the same turn.
