# ankitpokhrel/jira-cli usage notes

These notes summarize the JiraCLI behavior this skill relies on.

## Required local setup

- The user must have the open-source `ankitpokhrel/jira-cli` executable available as `jira`, or provide a path via `--jira-bin`.
- The user must authenticate and configure JiraCLI before querying, normally with `jira init`.
- For Jira Cloud, JiraCLI uses `JIRA_API_TOKEN` plus `jira init`.
- For Jira Server/Data Center, JiraCLI supports basic auth, bearer/PAT, and mtls depending on configuration.
- Multiple Jira configurations can be selected with `JIRA_CONFIG_FILE` or `jira ... -c /path/to/config.yaml`.

## Commands used by this skill

JiraCLI issue searches are performed with:

```bash
jira issue list --raw -q '<JQL>'
```

Relevant JiraCLI behaviors:

- `jira issue list` searches issues and sorts by `created` descending by default.
- `--raw` outputs raw JSON, which is the preferred input to the bundled parser.
- `--csv` also exists, but JSON is more stable for extracting nested assignee and status fields.
- `--jql` / `-q` executes raw JQL.
- Project scoping can also be done with `-p PROJECT`, but this skill includes `project = PROJECT` directly in JQL.

## Default stale GENEVA query

For a user request like "query GENEVA issues older than 1 week that are not closed", build a ZeppOS/Geneva-specific query:

```jql
project = GENEVA AND created <= "YYYY-MM-DD" AND status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved
```

This status list is based on the user's known Geneva Jira statuses:

```text
Open, In Progress, Reopened, Resolved, Closed, In Review, Pending
```

`Closed` is excluded from the default status whitelist. The default also uses `resolution = Unresolved` because the user's known-good Jira filter uses that literal and the user's Jira instance rejected `statusCategory`-based JQL.

For 1 month, normalize to 30 days before calculating the absolute cutoff date.

The wrapper sorts results locally by `Created` instead of adding `ORDER BY` by default. This avoids confusing Jira parser errors that point at `ORDER BY` when the preceding date, status, or category clause is incompatible with the Jira instance.

## Date cutoff modes

The wrapper supports four date modes:

- `absolute`: `created <= "YYYY-MM-DD"` (default and most portable)
- `relative`: `created <= -7d`
- `start-of-day`: `created <= startOfDay("-7d")`
- `start-of-day-unquoted`: `created <= startOfDay(-7d)`

Use `--dry-run` to see the generated JQL before executing.

## Non-closed definitions

The wrapper supports these modes:

- `zeppos-statuses`: `status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved` (default)
- `zeppos-statuses-no-resolution`: default status whitelist without the resolution clause
- `status-not-closed`: `status not in (Closed) AND resolution = Unresolved`
- `status-not-closed-no-resolution`: `status not in (Closed)`
- `resolution-unresolved`: `resolution = Unresolved`
- `resolution-empty`: `resolution IS EMPTY`
- `resolution-null`: `resolution = NULL`
- `status-category`: `statusCategory IN ("To Do", "In Progress")`
- `status-category-alias`: `statusCategory IN (New, Indeterminate)`
- `status-category-not-done`: `statusCategory != "Done"`
- `status-category-not-complete`: `statusCategory != Complete`
- `both`: `resolution = Unresolved AND statusCategory IN ("To Do", "In Progress")`

Prefer `zeppos-statuses` for Geneva unless the user provides a different working Jira filter.

## Assignee filters

Do not add assignee filtering by default. If the user asks for "my Jira", "assigned to me", or "我的", add:

```bash
--assignee-current-user
```

This appends:

```jql
assignee in (currentUser())
```

For explicit assignees, use comma-separated values:

```bash
--assignee 'alice,bob@example.com'
```

## Troubleshooting JQL parse errors

If Jira reports an error near `ORDER BY`, the root cause is often the previous clause, not the ordering itself. Run:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w --dry-run
```

Then try simpler alternatives:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode zeppos-statuses-no-resolution
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode status-not-closed
python scripts/query_stale_jiras.py --project GENEVA --age 1w --closed-mode resolution-unresolved
```

If a status is renamed, pass the current status list explicitly:

```bash
python scripts/query_stale_jiras.py --project GENEVA --age 1w --statuses 'Open,In Progress,Reopened,Resolved,In Review,Pending'
```

## Output contract

Always present results as a Markdown table with these columns:

| Jira | Assignee | Status | Created | Summary |
| --- | --- | --- | --- | --- |

If there are no rows, show the table header plus a single `_No matching Jira issues._` row.
