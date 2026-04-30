# Lark CLI Shortcut Catalog

This reference lists high-value shortcut commands from local `lark-cli` 1.0.22 help output. Shortcuts are prefixed with `+` and are usually the best choice for Agent work.

## Documents

Command map:

```text
lark-cli docs +create
lark-cli docs +fetch
lark-cli docs +media-download
lark-cli docs +media-insert
lark-cli docs +media-preview
lark-cli docs +media-upload
lark-cli docs +search
lark-cli docs +update
lark-cli docs +whiteboard-update
```

Common commands:

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content @report.md
lark-cli docs +create --api-version v2 --doc-format markdown --content @report.md --parent-position my_library
lark-cli docs +fetch --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --doc-format markdown --format json
lark-cli docs +fetch --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --scope outline --format json
lark-cli docs +fetch --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --scope keyword --keyword 'risk|todo' --context-before 1 --context-after 2 --format json
lark-cli docs +update --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --command append --doc-format markdown --content @appendix.md --dry-run
lark-cli docs +update --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --command str_replace --pattern 'old' --content 'new' --dry-run
lark-cli docs +search --query 'weekly report' --format table
```

Notes:

- Prefer v2 for new document work.
- `--content` supports `@file` and `-` for stdin.
- `docs +fetch --detail with-ids` is useful before block-level edits.
- Use `--command append` for report publishing unless overwrite was requested.

## Drive

Command map:

```text
lark-cli drive +add-comment
lark-cli drive +apply-permission
lark-cli drive +create-folder
lark-cli drive +create-shortcut
lark-cli drive +delete
lark-cli drive +download
lark-cli drive +export
lark-cli drive +export-download
lark-cli drive +import
lark-cli drive +move
lark-cli drive +search
lark-cli drive +task_result
lark-cli drive +upload
```

Common commands:

```bash
lark-cli drive +search --query 'release notes' --format table
lark-cli drive +upload --file ./report.pdf --folder-token '<FOLDER_TOKEN>' --dry-run
lark-cli drive +download --help
lark-cli drive +export --doc-type docx --file-extension pdf --token '<DOC_TOKEN>' --output-dir ./out
lark-cli drive +apply-permission --help
lark-cli drive +delete --help
```

Use `drive +export` for local copies of docs, docx, sheets, and bitables. Use `drive +delete` only after explicit user confirmation.

## Instant Messaging

Command map:

```text
lark-cli im +chat-create
lark-cli im +chat-messages-list
lark-cli im +chat-search
lark-cli im +chat-update
lark-cli im +messages-mget
lark-cli im +messages-reply
lark-cli im +messages-resources-download
lark-cli im +messages-search
lark-cli im +messages-send
lark-cli im +threads-messages-list
```

Resolve targets before sending:

```bash
lark-cli contact +search-user --query 'Alice' --format table
lark-cli im +chat-search --query 'project group' --format table
lark-cli im +chat-messages-list --chat-id 'oc_xxx' --format json
lark-cli im +messages-search --query 'release risk' --format json
```

Send and reply:

```bash
lark-cli im +messages-send --chat-id 'oc_xxx' --text 'hello' --dry-run
lark-cli im +messages-send --user-id 'ou_xxx' --markdown @message.md --idempotency-key '<stable-key>' --dry-run
lark-cli im +messages-reply --help
lark-cli im +messages-mget --help
lark-cli im +threads-messages-list --help
```

Use `--idempotency-key` for sends that could be retried. Do not send to a group or user name before resolving and confirming the stable `oc_` or `ou_` target.

## Calendar

Command map:

```text
lark-cli calendar +agenda
lark-cli calendar +create
lark-cli calendar +freebusy
lark-cli calendar +room-find
lark-cli calendar +rsvp
lark-cli calendar +suggestion
lark-cli calendar +update
```

Common commands:

```bash
lark-cli calendar +agenda --start '2026-05-01T00:00:00+08:00' --end '2026-05-01T23:59:59+08:00' --format table
lark-cli calendar +freebusy --user-id 'ou_xxx' --start '2026-05-01T10:00:00+08:00' --end '2026-05-01T11:00:00+08:00' --format json
lark-cli calendar +create --summary 'Review' --start '2026-05-01T10:00:00+08:00' --end '2026-05-01T10:30:00+08:00' --attendee-ids 'ou_xxx,ou_yyy' --dry-run
lark-cli calendar +update --help
lark-cli calendar +rsvp --help
```

Use ISO 8601 timestamps with timezone offsets. Query free/busy before scheduling when the user asks to find a time.

## Contacts

Command map:

```text
lark-cli contact +get-user
lark-cli contact +search-user
```

Common commands:

```bash
lark-cli contact +search-user --query 'Alice' --format table
lark-cli contact +search-user --queries 'Alice,Bob' --format json
lark-cli contact +search-user --user-ids 'ou_xxx,me' --format json
lark-cli contact +search-user --query 'Zhang San' --has-chatted --exclude-external-users --format table
lark-cli contact +get-user
lark-cli contact +get-user --help
```

Use `open_id` values from search results for follow-up commands.

## Sheets

Command map:

```text
lark-cli sheets +create
lark-cli sheets +read
lark-cli sheets +write
lark-cli sheets +append
lark-cli sheets +find
lark-cli sheets +replace
lark-cli sheets +export
lark-cli sheets +add-dimension
lark-cli sheets +insert-dimension
lark-cli sheets +delete-dimension
lark-cli sheets +move-dimension
lark-cli sheets +update-dimension
lark-cli sheets +merge-cells
lark-cli sheets +unmerge-cells
lark-cli sheets +set-style
lark-cli sheets +batch-set-style
lark-cli sheets +set-dropdown
lark-cli sheets +get-dropdown
lark-cli sheets +update-dropdown
lark-cli sheets +delete-dropdown
lark-cli sheets +create-filter-view
lark-cli sheets +list-filter-views
lark-cli sheets +update-filter-view
lark-cli sheets +delete-filter-view
lark-cli sheets +create-float-image
lark-cli sheets +write-image
```

Common commands:

```bash
lark-cli sheets +create --title 'Jira report' --headers '["Jira","Assignee","Status","Created","Summary"]' --dry-run
lark-cli sheets +read --url '<SHEET_URL>' --range 'A1:E20'
lark-cli sheets +write --url '<SHEET_URL>' --range 'A1:B2' --values '[["Name","Status"],["Alice","Open"]]' --dry-run
lark-cli sheets +append --help
lark-cli sheets +find --help
lark-cli sheets +export --help
```

Use JSON 2D arrays for `--values` and initial `--data`.

## Base

Command groups:

```text
base:       +base-create, +base-get, +base-copy
tables:     +table-list, +table-create, +table-get, +table-update, +table-delete
fields:     +field-list, +field-create, +field-get, +field-update, +field-delete, +field-search-options
records:    +record-list, +record-get, +record-search, +record-upsert, +record-batch-create, +record-batch-update, +record-delete, +record-history-list, +record-share-link-create, +record-upload-attachment
views:      +view-list, +view-create, +view-get, +view-rename, +view-delete, +view-set-filter, +view-set-sort, +view-set-group, +view-set-visible-fields
dashboards: +dashboard-list, +dashboard-create, +dashboard-block-list, +dashboard-block-create, +dashboard-arrange
forms:      +form-list, +form-create, +form-get, +form-update, +form-delete, +form-questions-list
roles:      +role-list, +role-create, +role-get, +role-update, +role-delete
workflow:   +workflow-list, +workflow-create, +workflow-get, +workflow-update, +workflow-enable, +workflow-disable
```

Common commands:

```bash
lark-cli base +table-list --base-token '<BASE_TOKEN>' --format table
lark-cli base +field-list --base-token '<BASE_TOKEN>' --table-id '<TABLE_ID_OR_NAME>' --format table
lark-cli base +record-list --base-token '<BASE_TOKEN>' --table-id '<TABLE_ID_OR_NAME>' --field-id 'Name' --field-id 'Status' --limit 100 --format json
lark-cli base +record-search --base-token '<BASE_TOKEN>' --table-id '<TABLE_ID_OR_NAME>' --json '{"keyword":"Alice","search_fields":["Name"]}'
lark-cli base +record-upsert --base-token '<BASE_TOKEN>' --table-id '<TABLE_ID_OR_NAME>' --json '{"Name":"Alice","Status":"Open"}' --dry-run
```

Field values in `--json` can use field names or field IDs. Prefer reading fields first when the table schema is unknown.

## Tasks

Command map:

```text
lark-cli task +assign
lark-cli task +comment
lark-cli task +complete
lark-cli task +create
lark-cli task +followers
lark-cli task +get-my-tasks
lark-cli task +get-related-tasks
lark-cli task +reminder
lark-cli task +reopen
lark-cli task +search
lark-cli task +set-ancestor
lark-cli task +subscribe-event
lark-cli task +tasklist-create
lark-cli task +tasklist-members
lark-cli task +tasklist-search
lark-cli task +tasklist-task-add
lark-cli task +update
```

Common commands:

```bash
lark-cli task +get-my-tasks --format table
lark-cli task +search --query 'release' --completed=false --page-all --page-limit 5 --format json
lark-cli task +create --summary 'Follow up' --description 'Check stale Jira report' --assignee 'ou_xxx' --due 'date:2026-05-02' --dry-run
lark-cli task +complete --task-id '<TASK_ID>' --dry-run
lark-cli task +comment --help
lark-cli task +assign --help
```

Use `--idempotency-key` for creates that might be retried.

## Mail

Command map:

```text
lark-cli mail +triage
lark-cli mail +message
lark-cli mail +messages
lark-cli mail +thread
lark-cli mail +draft-create
lark-cli mail +draft-edit
lark-cli mail +send
lark-cli mail +reply
lark-cli mail +reply-all
lark-cli mail +forward
lark-cli mail +share-to-chat
lark-cli mail +watch
lark-cli mail +signature
lark-cli mail +template-create
lark-cli mail +template-update
lark-cli mail +send-receipt
lark-cli mail +decline-receipt
```

Common commands:

```bash
lark-cli mail +triage --query 'release' --format table
lark-cli mail +message --help
lark-cli mail +thread --help
lark-cli mail +send --help
lark-cli mail +reply --help
```

Mail send/reply/forward shortcuts usually save drafts by default. Use `--confirm-send` only after the user explicitly asks to send.

## Meetings and minutes

Command map:

```text
lark-cli vc +search
lark-cli vc +recording
lark-cli vc +notes
lark-cli minutes +search
lark-cli minutes +download
```

Common commands:

```bash
lark-cli vc +search --help
lark-cli vc +notes --help
lark-cli minutes +search --help
lark-cli minutes +download --help
```

Use meeting IDs, minute tokens, or calendar event IDs depending on what the user provides. Fetch summaries/todos/transcripts only when the user has access.

## Wiki

Command map:

```text
lark-cli wiki +node-create
lark-cli wiki +move
lark-cli wiki +delete-space
```

Common commands:

```bash
lark-cli wiki +node-create --help
lark-cli wiki +move --help
lark-cli wiki +delete-space --help
```

Moving nodes and deleting spaces are high-risk mutations. Use `--dry-run` if available and require explicit confirmation.

## Slides, whiteboard, OKR, approval, attendance, and events

Slides:

```bash
lark-cli slides +create --help
lark-cli slides +media-upload --help
lark-cli slides +replace-slide --help
```

Whiteboard:

```bash
lark-cli whiteboard +query --help
lark-cli whiteboard +update --help
```

OKR:

```bash
lark-cli okr +cycle-list --help
lark-cli okr +cycle-detail --help
lark-cli okr +progress-create --help
lark-cli okr +progress-list --help
```

Approval:

```bash
lark-cli approval tasks --help
lark-cli approval instances --help
```

Attendance:

```bash
lark-cli attendance user_tasks --help
```

Events:

```bash
lark-cli event list
lark-cli event schema '<EVENT_KEY>'
lark-cli event consume '<EVENT_KEY>'
lark-cli event status
lark-cli event stop
```

Event consumers can run until stopped. Do not start long-running consumers unless the user asks for live event monitoring.
