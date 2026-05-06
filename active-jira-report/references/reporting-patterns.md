# Active Jira reporting patterns

Use this file when the user asks for a formatted Jira report or for rule-based issue creation that should follow project conventions.

## 1. Defect creation checklist

Minimum fields to capture:

- project key
- issue type
- summary
- description
- priority or severity
- assignee or owner

Frequently needed project fields:

- labels
- component
- fix version or affected version
- epic
- sprint
- environment
- reproduce steps
- expected result
- actual result
- device or app version
- custom project fields

Safe creation pattern:

1. Check similar issues from the same project and issue type.
2. Reuse the same vocabulary for labels, components, and severity.
3. Only pass `--custom` values that can be justified from project evidence or explicit user input.
4. If the user wants help drafting before creation, provide a filled field table plus the exact `jira issue create` command.

## 2. Common report shapes

### Status rollup

Use when the user wants a fast operational picture.

Recommended fields:

- total issues
- by status
- by assignee
- blockers
- overdue or stale items

Suggested output shape:

```markdown
## Scope

project = GENEVA, updated in last 7 days

## Summary

- Total: 18
- Open: 6
- In Progress: 5
- In Review: 3
- Pending: 2
- Resolved: 2

## Risks

- ISSUE-1 Owner A 12 days open API regression
- ISSUE-7 Owner B blocked by firmware dependency

## Action items

- Confirm owner for ISSUE-4
- Close or re-triage stale resolved issues
```

### Assignee rollup

Use when the report is owner-centric.

Recommended columns:

- assignee
- open count
- in-progress count
- blocked count
- highest-risk issue

### Release risk report

Use when the user mentions a release, milestone, or ship readiness.

Focus on:

- blockers
- unresolved high-priority issues
- issues without assignee
- issues reopened recently
- issues updated long ago but still not closed

### Stale issue report

Use when the request is based on age thresholds such as "超过 1 周未关闭".

Preferred output:

- Use `scripts/generate_stale_jira_report.py` after extracting explicit `project` and `age` from the user's trigger phrase.
- Do not rely on default project or default age values for stale reports; ask if either trigger parameter is missing.
- Ensure all pages are fetched before reporting totals because `jira issue list` is capped at 100 issues per page.
- Add an opening Highlight after query info for PM/PL reporting. It should list the issues that most deserve immediate repair or ownership confirmation, with a concise reason based on urgency, status risk, unassigned ownership, and overdue duration.
- Group the full issue list by `归属Team`; include group-level count, status distribution, urgency distribution, unassigned-owner count, average overdue days, oldest issue, and assignee Top 3 before listing every Jira in that group.
- Produce the project-required table shape from `SKILL.md` inside each team group, including ranking, Severity/urgency, overdue duration, status, owner, issue summary, and comment summary.
- Add the fixed summary section at the end of the document with total stale issues, status distribution, urgency distribution, unassigned count, oldest issue, assignee Top 5, oldest-issue Top 5, comment policy, urgency source, and `归属Team` source.

## 3. Report writing rules

- Be explicit about scope and time window.
- Put the key numbers near the top.
- Mention blockers before routine progress.
- Keep recommendations short and actionable.
- Do not mix inferred conclusions into the factual issue list without labeling them.

## 4. Example user prompts

- "按 GENEVA 项目要求整理一个 Jira 周报"
- "把这些 Jira 按 owner 汇总一下，给我一个适合汇报的版本"
- "创建一个 bug Jira，按项目规范把字段补齐"
- "帮我做一个 release risk report，突出 blocker 和高优先级未关闭项"
