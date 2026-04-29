# ankitpokhrel/jira-cli usage notes

These notes summarize the JiraCLI behavior this skill relies on. They are based on the official `ankitpokhrel/jira-cli` README and local JiraCLI v1.7.0 help output.

## Required local setup

- The user must have the open-source `ankitpokhrel/jira-cli` executable available as `jira`, or provide a path via `--jira-bin`.
- The user must authenticate and configure JiraCLI before querying, normally with `jira init`.
- For Jira Cloud, JiraCLI uses `JIRA_API_TOKEN` plus `jira init`.
- For Jira Server/Data Center, JiraCLI supports basic auth, bearer/PAT, and mtls depending on configuration.
- Multiple Jira configurations can be selected with `JIRA_CONFIG_FILE` or `jira ... -c /path/to/config.yaml`.
- Global project selection is available with `jira ... -p PROJECT`. Raw JQL may also include `project = PROJECT`.
- Global debug output is available with `--debug`.

Setup examples:

```bash
jira init
jira init --installation cloud --server https://example.atlassian.net --login user@example.com --project GENEVA
jira init --installation local --server https://jira.example.com --login username --auth-type bearer --project GENEVA
JIRA_CONFIG_FILE=./local_jira_config.yaml jira issue list
jira issue list -c ./local_jira_config.yaml
```

Utility commands:

```bash
jira version
jira me
jira serverinfo
jira completion zsh
jira man --generate --output /tmp/man-jira-cli
```

## Command map

Top-level commands:

```text
jira board       list boards
jira epic        list/create epics, add/remove issues from epics
jira issue       list/view/create/edit/assign/move/comment/worklog/link/clone/watch/delete issues
jira open        open a project or issue URL
jira project     list projects
jira release     list project versions
jira sprint      list/add/close sprints
jira completion  generate shell completion
jira init        initialize config
jira man         generate man pages
jira me          print configured Jira user
jira serverinfo  print Jira instance info
jira version     print JiraCLI version
```

Issue subcommands:

```text
jira issue list
jira issue view ISSUE-KEY
jira issue create
jira issue edit ISSUE-KEY
jira issue assign ISSUE-KEY ASSIGNEE
jira issue move ISSUE-KEY STATE
jira issue comment add ISSUE-KEY [COMMENT_BODY]
jira issue worklog add ISSUE-KEY TIME_SPENT
jira issue link INWARD_ISSUE_KEY OUTWARD_ISSUE_KEY ISSUE_LINK_TYPE
jira issue link remote ISSUE_KEY WEBLINK_URL WEBLINK_TITLE
jira issue unlink INWARD_ISSUE_KEY OUTWARD_ISSUE_KEY
jira issue clone ISSUE-KEY
jira issue watch ISSUE-KEY WATCHER
jira issue delete ISSUE-KEY [--cascade]
```

Epic, sprint, release, project, and board subcommands:

```text
jira epic list [EPIC-KEY]
jira epic create
jira epic add EPIC-KEY ISSUE-1 [...ISSUE-N]
jira epic remove ISSUE-1 [...ISSUE-N]
jira sprint list [SPRINT_ID]
jira sprint add SPRINT_ID ISSUE-1 [...ISSUE-N]
jira sprint close SPRINT_ID
jira release list
jira project list
jira board list
```

## Agent output rules

- Prefer `--raw` JSON for data extraction and summarization.
- Prefer `--plain --columns ... --no-headers` for simple tabular shell pipelines.
- Use `--csv` when the user asks for CSV or spreadsheet import.
- Use interactive/TUI output only when the user is expected to operate it directly.
- Do not mutate Jira unless the user explicitly requests the mutation.
- Treat `jira issue delete` and `jira issue delete --cascade` as destructive and require a very clear user request.
- In filter flags, `~` negates a value, and `x` usually means empty/unassigned for fields like assignee.
- Date filters accept `today`, `week`, `month`, `year`, absolute dates like `yyyy-mm-dd` or `yyyy/mm/dd`, and relative periods with `w`, `d`, `h`, or `m`, for example `-10d`.

Interactive navigation:

```text
arrow keys or j/k/h/l  navigate
g / G                  top / bottom
Ctrl-f / Ctrl-b        page down / page up
v                      view selected issue
m                      transition selected issue
Enter                  open selected issue in browser
c                      copy issue URL
Ctrl-k                 copy issue key
w or Tab               switch focus in explorer views
Ctrl-r or F5           refresh
?                      help
q / Esc / Ctrl-c       quit
```

## Issue search and query

Primary Agent search pattern:

```bash
jira issue list --raw -q '<JQL>'
```

Relevant JiraCLI behaviors:

- `jira issue list` searches issues and sorts by `created` descending by default.
- `--raw` outputs raw JSON, which is the preferred input to the bundled parser.
- `--csv` exists, but JSON is more stable for extracting nested assignee and status fields.
- `--jql` / `-q` executes raw JQL.
- Project scoping can also be done with `-p PROJECT`, but this skill includes `project = PROJECT` directly in JQL.
- An optional positional text argument searches like the Jira UI search box.
- `--paginate <from>:<limit>` or `--paginate <limit>` controls paging; max 100 at a time.
- `--order-by FIELD` and `--reverse` control sorting.

Common issue search commands:

```bash
jira issue list
jira issue list "Feature Request"
jira issue list --created -7d
jira issue list --created week
jira issue list --updated -30m
jira issue list --created-before -24w
jira issue list -q 'project IS NOT EMPTY'
jira issue list -q 'project = GENEVA AND summary ~ "cli"'
jira issue list -pXYZ -w
jira issue list --history
```

Common filters:

```bash
jira issue list -tBug
jira issue list -s"To Do"
jira issue list -s~Done
jira issue list -yHigh
jira issue list -R"Won't do"
jira issue list -a$(jira me)
jira issue list -a"User A" -r"User B"
jira issue list -ax
jira issue list -a~x
jira issue list -CBackend
jira issue list -lbackend -l"high-prio"
jira issue list -P EPIC-1
```

Plain, CSV, and raw output:

```bash
jira issue list --plain
jira issue list --plain --no-headers
jira issue list --plain --no-truncate
jira issue list --plain --columns key,assignee,status,created,summary
jira issue list --plain --columns key,status --delimiter '|'
jira issue list --raw
jira issue list --csv
```

Columns accepted by `issue list --columns`:

```text
TYPE, KEY, SUMMARY, STATUS, ASSIGNEE, REPORTER, PRIORITY, RESOLUTION, CREATED, UPDATED, LABELS
```

## Issue read and mutate commands

View issue:

```bash
jira issue view ISSUE-1
jira issue view ISSUE-1 --comments 5
jira issue view ISSUE-1 --plain
jira issue view ISSUE-1 --raw
```

Create issue:

```bash
jira issue create
jira issue create -pPRJ -tBug -s"New Bug" -yHigh -lbug -lurgent -b"Bug description" --no-input
jira issue create -tStory -s"Issue with custom fields" --custom story-points=3
jira issue create -tStory -s"Epic during creation" -PEPIC-42
jira issue create --template /path/to/template.tmpl
jira issue create --template -
echo "Description from stdin" | jira issue create -s"Summary" -tTask
jira issue create --raw
```

Edit issue:

```bash
jira issue edit ISSUE-1
jira issue edit ISSUE-1 -s"New Bug" -yHigh -lbug -lurgent -CBackend -b"Bug description"
jira issue edit ISSUE-1 -s"New updated summary" --no-input
echo "Description from stdin" | jira issue edit ISSUE-1 -s"New updated summary" --no-input
jira issue edit ISSUE-1 --label -urgent --component -BE --fix-version -v1.0
```

Assign issue:

```bash
jira issue assign ISSUE-1 "Jon Doe"
jira issue assign ISSUE-1 jon@domain.tld
jira issue assign ISSUE-1 $(jira me)
jira issue assign ISSUE-1 default
jira issue assign ISSUE-1 x
```

Transition issue:

```bash
jira issue move ISSUE-1 "In Progress"
jira issue move ISSUE-1 Done
jira issue move ISSUE-1 "In Progress" --comment "Started working on it"
jira issue move ISSUE-1 Done -RFixed -a$(jira me)
```

Comment:

```bash
jira issue comment add ISSUE-1 "My comment"
jira issue comment add ISSUE-1 $'Supports\n\nNew line'
jira issue comment add ISSUE-1 "My comment" --internal
jira issue comment add ISSUE-1 --template /path/to/template.tmpl
jira issue comment add ISSUE-1 --template -
echo "Comment from stdin" | jira issue comment add ISSUE-1
```

Worklog:

```bash
jira issue worklog add ISSUE-1 "2d 1h 30m" --no-input
jira issue worklog add ISSUE-1 "10m" --comment "This is a comment" --no-input
jira issue worklog add ISSUE-1 3h --started "2022-01-01 09:30:00" --timezone "Europe/Berlin"
jira issue worklog add ISSUE-1 "1h 30m" --started "2022-01-01T09:30:00.000+0200" --new-estimate 0h
```

Link, unlink, clone, watch, delete:

```bash
jira issue link ISSUE-1 ISSUE-2 Blocks
jira issue link remote ISSUE-1 https://example.com "Example text"
jira issue unlink ISSUE-1 ISSUE-2
jira issue clone ISSUE-1
jira issue clone ISSUE-1 -s"Modified summary" -yHigh -a$(jira me)
jira issue clone ISSUE-1 -H"find me:replace with me"
jira issue watch ISSUE-1 $(jira me)
jira issue delete ISSUE-1
jira issue delete ISSUE-1 --cascade
```

## Epic commands

Epics default to an explorer view. Use `--table`, `--plain`, or `--raw` for Agent-readable output.

```bash
jira epic list
jira epic list --table
jira epic list --table --plain
jira epic list --table --plain --columns key,summary,status
jira epic list -r$(jira me) -sOpen
jira epic list EPIC-1
jira epic list EPIC-1 --plain --columns type,key,summary,status
jira epic list EPIC-1 -ax -yHigh
jira epic list EPIC-1 --order-by rank --reverse
```

Create and manage epic membership:

```bash
jira epic create
jira epic create -n"Epic name" -s"Everything" -yHigh -lbug -lurgent -b"Epic description" --no-input
jira epic create -pPRJ -n"Amazing epic" -s"Epic summary" --custom story-points=3
jira epic add EPIC-1 ISSUE-1 ISSUE-2
jira epic remove ISSUE-1 ISSUE-2
```

`jira epic add` and `jira epic remove` accept up to 50 issues at once.

## Sprint commands

Sprints default to an explorer view. Use `--table`, `--plain`, or `--raw` for Agent-readable output. By default, sprint list filters sprint state to active and closed unless a different `--state` is provided.

```bash
jira sprint list
jira sprint list --table
jira sprint list --table --plain --columns id,name,start,end,state
jira sprint list --state future,active
jira sprint list --current
jira sprint list --prev
jira sprint list --next
jira sprint list SPRINT_ID
jira sprint list SPRINT_ID --plain --columns type,key,summary,status,assignee
jira sprint list SPRINT_ID -yHigh -a$(jira me)
jira sprint list SPRINT_ID --order-by rank --reverse
jira sprint list --current --show-all-issues
```

Manage sprint membership and completion:

```bash
jira sprint add SPRINT_ID ISSUE-1 ISSUE-2
jira sprint close SPRINT_ID
```

`jira sprint add` accepts up to 50 issues at once.

Sprint list columns:

```text
For sprint list: ID, NAME, START, END, COMPLETE, STATE
For sprint issues: TYPE, KEY, SUMMARY, STATUS, ASSIGNEE, REPORTER, PRIORITY, RESOLUTION, CREATED, UPDATED, LABELS
```

## Release, project, board, open, user, server commands

```bash
jira release list
jira release list -p PROJECT
jira project list
jira board list -p PROJECT
jira open
jira open ISSUE-1
jira open ISSUE-1 --no-browser
jira me
jira serverinfo
```

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
