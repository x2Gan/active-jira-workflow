# Lark CLI Usage Notes

These notes summarize the official `@larksuite/cli` behavior this skill relies on. They are based on the official `larksuite/cli` README, npm metadata, and local `lark-cli` 1.0.22 help output.

## Required local setup

The user must have Node.js with `npm` and `npx`, then install the official CLI:

```bash
npm install -g @larksuite/cli
npx skills add larksuite/cli -y -g
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

This repository also includes a setup wrapper:

```bash
sh lark-cli.sh doctor
sh lark-cli.sh install
sh lark-cli.sh config
sh lark-cli.sh login
sh lark-cli.sh status
sh lark-cli.sh update
sh lark-cli.sh bootstrap
```

The official `config init --new` and `auth login --recommend` flows may block until the user completes a browser authorization step. For Agent use, pass the verification URL to the user when the CLI prints one.

## Command system

`lark-cli` has three command layers:

1. Shortcuts: curated commands prefixed with `+`, such as `docs +create` or `im +messages-send`.
2. Generated API commands: service/resource/method commands generated from Lark OpenAPI metadata, such as `calendar events instance_view`.
3. Raw API calls: `lark-cli api METHOD /open-apis/...` for endpoints not covered above.

Prefer this order unless the user explicitly asks for a raw API call.

## Global flags

Common flags from `lark-cli --help`:

```text
--params <json>       URL/query parameters JSON
--data <json>         request body JSON
--as <type>           identity type: user | bot | auto
--format <fmt>        json | ndjson | table | csv | pretty
--page-all            automatically paginate through all pages
--page-size <N>       page size
--page-limit <N>      max pages with --page-all
--page-delay <MS>     delay between pages
-o, --output <path>   output file path for binary responses
--jq <expr>, -q       jq expression to filter JSON output
--dry-run             print request without executing
--profile <name>      use a specific profile
```

Agent output rules:

- Use `--format json` for summarization and structured extraction.
- Use `--format table` only for user-facing inspection.
- Use `--page-all --page-limit N` when asking for a complete but bounded list.
- Use `--jq` for stable field extraction instead of brittle shell text parsing.
- Use `--dry-run` before writes when the target or effect is not fully pinned down.

## Top-level command map

```text
lark-cli api         Generic Lark API requests
lark-cli approval    Approval instance and task management
lark-cli attendance  Attendance record query
lark-cli auth        OAuth credentials and authorization management
lark-cli base        Base table, field, record, view, dashboard, workflow, form, role, permission management
lark-cli calendar    Calendar, event, and attendee management
lark-cli config      Global CLI configuration management
lark-cli contact     Contacts operations
lark-cli docs        Document and content operations
lark-cli doctor      CLI health check
lark-cli drive       File, comment, permission, and upload management
lark-cli event       Consume and manage real-time events
lark-cli im          Message and group chat management
lark-cli mail        Email, draft, folder, and contacts management
lark-cli minutes     Minutes content and metadata retrieval
lark-cli okr         OKR objectives, key results, alignments, indicators, progresses
lark-cli profile     Manage configuration profiles
lark-cli schema      View API method parameters, types, and scopes
lark-cli sheets      Spreadsheet operations
lark-cli slides      Presentations
lark-cli task        Task, task list, and subtask management
lark-cli update      Update lark-cli
lark-cli vc          Video conference and meeting note management
lark-cli whiteboard  Create and edit boards
lark-cli wiki        Wiki space and node management
```

## Auth, config, and profiles

Core auth commands:

```bash
lark-cli config init --new
lark-cli config init --app-id '<cli_xxx>' --app-secret-stdin --brand feishu
lark-cli config show
lark-cli config default-as
lark-cli config strict-mode
lark-cli auth login
lark-cli auth login --recommend
lark-cli auth login --domain docs,drive,im --recommend
lark-cli auth login --scope 'calendar:calendar:read'
lark-cli auth login --domain calendar --no-wait
lark-cli auth login --device-code '<device-code>'
lark-cli auth status
lark-cli auth status --verify
lark-cli auth check --scope '<scope>'
lark-cli auth scopes
lark-cli auth list
lark-cli auth logout
```

Profile commands:

```bash
lark-cli profile list
lark-cli profile add
lark-cli profile use '<name>'
lark-cli profile rename '<old>' '<new>'
lark-cli profile remove '<name>'
```

Do not switch, rename, or remove profiles unless the user explicitly asks.

## Docs v1 and v2 caveat

`docs +create`, `docs +fetch`, and `docs +update` default to v1 in CLI 1.0.22, and v1 help may show different flags. Prefer v2 for new work and inspect v2 help when unsure:

```bash
lark-cli docs +create --api-version v2 --help
lark-cli docs +fetch --api-version v2 --help
lark-cli docs +update --api-version v2 --help
```

Important v2 patterns:

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content @report.md
lark-cli docs +fetch --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --doc-format markdown --format json
lark-cli docs +update --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --command append --doc-format markdown --content @appendix.md
```

Content flags support `@file` and `-` for stdin. Prefer those forms over `--content "$(cat file.md)"` for long reports.

## Schema introspection

Use schema before generated API or raw API work:

```bash
lark-cli schema
lark-cli schema calendar.events.instance_view --format pretty
lark-cli schema im.messages.delete --format pretty
```

Schema output is useful for:

- required URL parameters and request body fields;
- supported identity types;
- required scopes;
- response shapes for `--jq` extraction.

## Raw API

Use raw API calls only when shortcuts and generated commands do not cover the task:

```bash
lark-cli api GET /open-apis/calendar/v4/calendars --format json
lark-cli api POST /open-apis/im/v1/messages \
  --params '{"receive_id_type":"chat_id"}' \
  --data '{"receive_id":"oc_xxx","msg_type":"text","content":"{\"text\":\"Hello\"}"}' \
  --dry-run
```

`--params` and `--data` support `-` for stdin. `--file` supports multipart upload.

## Identity rules

Use `--as user` when the operation is scoped to the user's private resources or user-only APIs:

- personal docs and Drive search;
- contacts search;
- message search;
- calendar and mail;
- user tasks.

Use `--as bot` when the user asks the app/bot to act and the bot has the necessary resource access:

- bot sending to a known chat;
- bot uploading/downloading resources it can access;
- automation against app-owned resources.

Use `--as auto` only when a raw API or generated command can choose safely. For shortcut commands, use the default only after checking help.

## Risk labels

Shortcut help prints risk labels such as `Risk: read` or `Risk: write`.

Treat these as execution gates:

- `read`: safe to run when the user asks for information and auth is available.
- `write`: run only when the user clearly requests the side effect. Use `--dry-run` when details are ambiguous.

High-risk examples:

```bash
lark-cli drive +delete --dry-run
lark-cli wiki +delete-space --dry-run
lark-cli docs +update --api-version v2 --command overwrite --dry-run
lark-cli mail +send --confirm-send --dry-run
lark-cli im +messages-send --dry-run
lark-cli config remove
lark-cli profile remove
lark-cli auth logout
```

## Troubleshooting

Install or PATH problem:

```bash
command -v lark-cli
npm list -g @larksuite/cli --depth=0
npm config get prefix
sh lark-cli.sh doctor
```

Auth or scope problem:

```bash
lark-cli doctor --offline
lark-cli auth status --verify
lark-cli auth scopes
lark-cli auth login --domain docs,drive,im --recommend
```

Command shape problem:

```bash
lark-cli <domain> --help
lark-cli <domain> <shortcut> --help
lark-cli schema <service.resource.method> --format pretty
```

Pagination problem:

```bash
lark-cli docs +search --query 'report' --page-size 20 --format json
lark-cli task +search --query 'follow up' --page-all --page-limit 5 --format json
lark-cli api GET /open-apis/calendar/v4/calendars --page-all --page-limit 5 --format json
```
