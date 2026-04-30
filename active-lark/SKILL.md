---
name: active-lark
description: operate Lark/Feishu through the official local lark-cli command. use when the user asks to configure or authenticate Lark CLI, inspect auth/profile status, create/read/update/search Lark docs, Drive files, Wiki nodes, Sheets, Base records, calendar events, tasks, contacts, IM messages, mail, meetings/minutes, OKR, approval, attendance, whiteboards, slides, events, or raw Lark OpenAPI endpoints, including publishing Jira Markdown reports to Feishu documents.
---

# Active Lark

## Overview

Use this skill for generic Lark/Feishu access through the official local `lark-cli` installation. This is the low-level Lark capability layer: configure auth, inspect schemas, call shortcut commands, use generated API commands, or fall back to raw OpenAPI calls.

When local execution is unavailable, provide the exact command the user should run and explain how to paste the output back. For data extraction, prefer `--format json` plus `--jq`, or `--format table` only when the user wants a readable table.

## Reference map

Consult these bundled references only when needed:

- `references/lark-cli-usage.md`: install/auth, three-layer command system, global flags, command map, output, pagination, schema/API usage, safety rules, and troubleshooting.
- `references/lark-cli-shortcuts.md`: shortcut catalog and common commands for docs, Drive, IM, calendar, contacts, Sheets, Base, tasks, mail, meetings, Wiki, and other domains.

Use `scripts/publish_markdown_doc.py` when publishing a local Markdown file, such as a Jira report, into a Lark document or appending/overwriting an existing document. Run it with `--dry-run` first when target location, identity, or content is uncertain.

## Global conventions

- Use the local `lark-cli` binary. If it is missing, run `sh lark-cli.sh doctor` or ask the user to run `sh lark-cli.sh install`.
- Before private-resource operations, check status with `lark-cli auth status` or `lark-cli auth status --verify`.
- Prefer shortcut commands prefixed with `+` for Agent work. They are curated, safer, and easier to parse than low-level API commands.
- Use generated API commands when a shortcut does not expose a needed endpoint. Use `lark-cli schema <service.resource.method>` first.
- Use raw `lark-cli api METHOD /open-apis/...` only when neither a shortcut nor generated API command covers the request.
- Prefer `--api-version v2` for `docs +create`, `docs +fetch`, and `docs +update`.
- Prefer file-backed content arguments such as `--content @report.md` or stdin `--content -` instead of shell command substitution for long Markdown.
- Use `--as user` for personal resources such as private docs, calendar, mail, tasks, contacts, and message search. Use `--as bot` only when the target resource and bot permissions are clear.
- Do not switch, rename, or remove profiles unless the user explicitly asks. `lark-cli profile --help` warns Agents not to switch or remove profiles by default.
- Do not store App Secret, access token, refresh token, authorization URL, or private Lark content in repository files or logs.

## Mutation policy

Only perform mutating commands when the user clearly asks to create, update, send, reply, invite, assign, upload, move, delete, import/export, grant permission, approve/reject, or subscribe.

Use `--dry-run` before a mutation when any of these are unclear:

- target user, chat, calendar, document, sheet, Base table, Wiki space, or Drive folder;
- message/email/document body;
- identity type (`--as user` vs `--as bot`);
- permission scope or visibility;
- destructive operation such as delete, move, overwrite, logout, profile removal, or config removal.

High-risk operations need especially clear user intent: `drive +delete`, `wiki +delete-space`, `docs +update --command overwrite`, `mail +send --confirm-send`, `im +messages-send`, `calendar +create`, approval decisions, permission grants, and `config remove`.

## Quick command patterns

Setup and auth:

```bash
sh lark-cli.sh doctor
sh lark-cli.sh bootstrap
lark-cli doctor --offline
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status --verify
lark-cli auth check --scope '<scope>'
```

Docs and Jira report publishing:

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content @doc/active-jira-report.md
lark-cli docs +fetch --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --doc-format markdown --format json
lark-cli docs +update --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --command append --doc-format markdown --content @appendix.md
python active-lark/scripts/publish_markdown_doc.py doc/active-jira-report.md --dry-run
python active-lark/scripts/publish_markdown_doc.py doc/active-jira-report.md
```

Search and resolve targets before sending:

```bash
lark-cli contact +search-user --query 'Alice' --format table
lark-cli im +chat-search --query 'project group' --format table
lark-cli docs +search --query 'weekly report' --format table
lark-cli drive +search --query 'release notes' --format table
```

Send or update only after confirmation:

```bash
lark-cli im +messages-send --chat-id 'oc_xxx' --text 'hello' --dry-run
lark-cli im +messages-send --chat-id 'oc_xxx' --text 'hello' --idempotency-key '<stable-key>'
lark-cli calendar +create --summary 'Review' --start '2026-05-01T10:00:00+08:00' --end '2026-05-01T10:30:00+08:00' --attendee-ids 'ou_xxx' --dry-run
lark-cli task +create --summary 'Follow up' --assignee 'ou_xxx' --due 'date:2026-05-02' --dry-run
```

Schema and raw API fallback:

```bash
lark-cli schema
lark-cli schema im.messages.create --format pretty
lark-cli api GET /open-apis/calendar/v4/calendars --format json
lark-cli api POST /open-apis/im/v1/messages --params '{"receive_id_type":"chat_id"}' --data '{"receive_id":"oc_xxx","msg_type":"text","content":"{\"text\":\"Hello\"}"}' --dry-run
```

## Workflow

1. Identify whether the request is read-only, mutating, or administrative.
2. Check `lark-cli` presence and auth if the command needs live access.
3. Resolve human names to stable IDs before using them in follow-up commands: users are usually `ou_...`; chats are usually `oc_...`; message IDs are usually `om_...`; Wiki and document tokens vary by resource type.
4. Choose the narrowest command layer: shortcut, generated API command, then raw API.
5. For reads, use `--format json`, `--format table`, `--page-all`, `--page-limit`, and `--jq` as needed.
6. For writes, show or run a dry-run when the target or side effect is meaningful, then execute after the user's intent is clear.
7. Summarize results with stable links/tokens and call out any auth, scope, or permission gap.

## Troubleshooting

If `lark-cli` is missing, use the repository wrapper:

```bash
sh lark-cli.sh install
sh lark-cli.sh config
sh lark-cli.sh login
sh lark-cli.sh status
```

If a command fails due to missing scopes, run:

```bash
lark-cli auth status --verify
lark-cli auth scopes
lark-cli auth login --domain docs,drive,im --recommend
```

If a command shape is uncertain, inspect help and schema:

```bash
lark-cli <domain> --help
lark-cli <domain> <shortcut> --help
lark-cli schema <service.resource.method> --format pretty
```
