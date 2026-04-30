#!/usr/bin/env python3
"""Generate a stale Jira report, publish it to Lark Docs, and notify a chat."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_GENERATOR = REPO_ROOT / "active-jira-report" / "scripts" / "generate_stale_jira_report.py"
MARKDOWN_PUBLISHER = REPO_ROOT / "active-lark" / "scripts" / "publish_markdown_doc.py"
DOC_URL_PLACEHOLDER = "<LARK_DOC_URL_FROM_CREATE_RESPONSE>"
DOC_TOKEN_PLACEHOLDER = "doxcn_dry_run_placeholder"
URL_RE = re.compile(r"https?://[^\s\"'<>]+")


class PublishError(RuntimeError):
    """Raised for expected command or argument failures."""


@dataclass
class DocInfo:
    url: str | None = None
    token: str | None = None
    doc_type: str = "docx"


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a stale Jira Markdown report, create/update a Lark document, "
            "and optionally send the document link to a Lark chat."
        ),
        epilog=(
            "Unknown options are forwarded to generate_stale_jira_report.py. "
            "Use --dry-run to preview Lark write requests; Jira report generation still runs."
        ),
    )
    parser.add_argument("--project", required=True, help="Jira project key, for example GENEVA.")
    parser.add_argument("--age", required=True, help="Age threshold, for example 1w, 14d, or 30天.")
    parser.add_argument(
        "--report-output",
        help="Markdown report output path. Defaults to reports/<project>-stale-jira-<age>-<timestamp>.md.",
    )
    parser.add_argument("--doc", help="Existing Lark document URL or token. Omit to create a new document.")
    parser.add_argument(
        "--doc-command",
        choices=("append", "overwrite"),
        default="append",
        help="Update command when --doc is supplied.",
    )
    parser.add_argument("--title", help="Report document title. Defaults to '<PROJECT> 长期未处理 Jira 报告'.")
    parser.add_argument("--parent-token", help="Parent folder or wiki-node token for document creation.")
    parser.add_argument("--parent-position", help="Parent position for document creation, for example my_library.")
    parser.add_argument(
        "--publish-as",
        choices=("user", "bot"),
        default="user",
        help="Identity used to create/update the Lark document.",
    )
    parser.add_argument("--chat-id", help="Lark chat ID (oc_xxx). When supplied, send the document link there.")
    parser.add_argument(
        "--grant-chat-view",
        action="store_true",
        help="Grant the target chat view permission on the published document before sending.",
    )
    parser.add_argument(
        "--message-as",
        choices=("bot", "user"),
        default="bot",
        help="Identity used to send the Lark message.",
    )
    parser.add_argument(
        "--message",
        help=(
            "Markdown message template. Supported placeholders: {title}, {project}, {age}, "
            "{doc_url}, {report_path}."
        ),
    )
    parser.add_argument("--idempotency-key", help="Lark message idempotency key.")
    parser.add_argument("--lark-cli", default="lark-cli", help="Path or command name for lark-cli.")
    parser.add_argument("--check-auth", action="store_true", help="Run lark-cli auth status before publishing.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to Lark document, permission, and message write commands.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print command output useful for debugging.")
    return parser.parse_known_args(argv)


def resolve_cli(cli: str) -> str:
    if "/" in cli:
        path = Path(cli).expanduser()
        if path.exists():
            return str(path)
        raise PublishError(f"lark-cli not found: {cli}")

    resolved = shutil.which(cli)
    if not resolved:
        raise PublishError("lark-cli not found on PATH. Run: sh lark-cli.sh install")
    return resolved


def ensure_scripts_exist() -> None:
    missing = [path for path in (REPORT_GENERATOR, MARKDOWN_PUBLISHER) if not path.is_file()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise PublishError(f"Required script not found: {joined}")


def safe_slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    return slug or fallback


def default_report_output(project: str, age: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    project_slug = safe_slug(project.lower(), "project")
    age_slug = safe_slug(age, "age")
    return REPO_ROOT / "reports" / f"{project_slug}-stale-jira-{age_slug}-{timestamp}.md"


def shell_join(cmd: list[str]) -> str:
    return shlex.join(cmd)


def run_command(cmd: list[str], *, verbose: bool, label: str) -> str:
    print("+ " + shell_join(cmd), file=sys.stderr)
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if verbose and result.stdout:
        print(f"# {label} stdout", file=sys.stderr)
        print(result.stdout.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        details = (result.stdout or result.stderr or "").strip()
        if details:
            details = "\n" + details
        raise PublishError(f"{label} failed with exit code {result.returncode}: {shell_join(cmd)}{details}")
    return result.stdout


def validate_forwarded_args(report_args: list[str]) -> None:
    if "--output" in report_args:
        raise PublishError("Use --report-output with this wrapper; --output is reserved for the report generator.")


def build_generator_cmd(
    args: argparse.Namespace,
    report_args: list[str],
    report_path: Path,
) -> list[str]:
    cmd = [
        sys.executable,
        str(REPORT_GENERATOR),
        "--project",
        args.project,
        "--age",
        args.age,
        "--output",
        str(report_path),
    ]
    if args.verbose:
        cmd.append("--verbose")
    cmd.extend(report_args)
    return cmd


def build_publish_cmd(args: argparse.Namespace, report_path: Path, cli: str) -> list[str]:
    cmd = [
        sys.executable,
        str(MARKDOWN_PUBLISHER),
        str(report_path),
        "--lark-cli",
        cli,
        "--as",
        args.publish_as,
    ]
    if args.doc:
        cmd.extend(["--doc", args.doc, "--command", args.doc_command])
    if args.parent_token:
        cmd.extend(["--parent-token", args.parent_token])
    if args.parent_position:
        cmd.extend(["--parent-position", args.parent_position])
    if args.title:
        cmd.extend(["--title", args.title])
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def json_from_text(text: str) -> object | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    start_positions = [pos for pos in (cleaned.find("{"), cleaned.find("[")) if pos >= 0]
    if not start_positions:
        return None
    start = min(start_positions)
    end = max(cleaned.rfind("}"), cleaned.rfind("]"))
    if end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def clean_url(url: str) -> str:
    return url.rstrip(".,;:)]}，。；：）】")


def urls_from_text(text: str) -> list[str]:
    return [clean_url(match.group(0)) for match in URL_RE.finditer(text)]


def token_from_url(url: str | None) -> str | None:
    if not url:
        return None
    for pattern in (
        r"/docx/([^/?#]+)",
        r"/docs/([^/?#]+)",
        r"/doc/([^/?#]+)",
        r"/wiki/([^/?#]+)",
    ):
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def infer_doc_type(url: str | None, token: str | None) -> str:
    if url:
        if "/wiki/" in url:
            return "wiki"
        if "/docx/" in url:
            return "docx"
        if "/docs/" in url or "/doc/" in url:
            return "doc"
    if token:
        if token.startswith("dox"):
            return "docx"
        if token.startswith("doc"):
            return "doc"
        if token.startswith("wik"):
            return "wiki"
    return "docx"


def collect_doc_info(value: object) -> DocInfo:
    urls: list[str] = []
    tokens: list[str] = []
    preferred_token_keys = {
        "document_id",
        "document_token",
        "doc_token",
        "file_token",
        "obj_token",
        "token",
    }

    def walk(node: object, key: str = "") -> None:
        if isinstance(node, dict):
            for raw_key, child in node.items():
                child_key = str(raw_key).lower()
                if isinstance(child, str):
                    urls.extend(urls_from_text(child))
                    if child_key in preferred_token_keys or child_key.endswith("_token"):
                        tokens.append(child)
                else:
                    walk(child, child_key)
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif isinstance(node, str):
            urls.extend(urls_from_text(node))

    walk(value)

    doc_urls = [
        url
        for url in urls
        if any(marker in url for marker in ("/docx/", "/docs/", "/doc/", "/wiki/"))
        or "feishu.cn" in url
        or "larksuite.com" in url
    ]
    url = doc_urls[0] if doc_urls else (urls[0] if urls else None)
    token = token_from_url(url) or (tokens[0] if tokens else None)
    return DocInfo(url=url, token=token, doc_type=infer_doc_type(url, token))


def doc_info_from_text(text: str) -> DocInfo:
    parsed = json_from_text(text)
    if parsed is not None:
        info = collect_doc_info(parsed)
        if info.url or info.token:
            return info
    return collect_doc_info(text)


def merge_doc_info(primary: DocInfo, fallback: DocInfo) -> DocInfo:
    url = primary.url or fallback.url
    token = primary.token or fallback.token or token_from_url(url)
    return DocInfo(url=url, token=token, doc_type=infer_doc_type(url, token) or primary.doc_type or fallback.doc_type)


def build_permission_cmd(args: argparse.Namespace, cli: str, doc_info: DocInfo) -> list[str]:
    if not args.chat_id:
        raise PublishError("--grant-chat-view requires --chat-id.")
    if not doc_info.token:
        raise PublishError("Could not determine document token for permission grant.")

    params = {
        "token": doc_info.token,
        "type": doc_info.doc_type,
        "need_notification": False,
    }
    data = {
        "member_id": args.chat_id,
        "member_type": "openchat",
        "perm": "view",
        "type": "chat",
    }
    cmd = [
        cli,
        "drive",
        "permission.members",
        "create",
        "--as",
        args.publish_as,
        "--params",
        json.dumps(params, ensure_ascii=False),
        "--data",
        json.dumps(data, ensure_ascii=False),
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def render_message(args: argparse.Namespace, report_path: Path, doc_url: str) -> str:
    title = args.title or f"{args.project} 长期未处理 Jira 报告"
    replacements = {
        "{title}": title,
        "{project}": args.project,
        "{age}": args.age,
        "{doc_url}": doc_url,
        "{report_path}": str(report_path),
    }
    if args.message:
        message = args.message
        for key, value in replacements.items():
            message = message.replace(key, value)
        return message
    return (
        f"**{title}**\n\n"
        f"- 项目: {args.project}\n"
        f"- 超时时间: {args.age}\n"
        f"- 飞书文档: {doc_url}"
    )


def default_idempotency_key(args: argparse.Namespace, doc_url: str, report_path: Path) -> str:
    project_slug = safe_slug(args.project.lower(), "project")
    seed = f"{args.project}:{args.age}:{doc_url}:{report_path}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"active-jira-report-{project_slug}-{digest}"


def build_message_cmd(args: argparse.Namespace, cli: str, report_path: Path, doc_url: str) -> list[str]:
    if not args.chat_id:
        raise PublishError("Message send requires --chat-id.")
    message = render_message(args, report_path, doc_url)
    idempotency_key = args.idempotency_key or default_idempotency_key(args, doc_url, report_path)
    cmd = [
        cli,
        "im",
        "+messages-send",
        "--as",
        args.message_as,
        "--chat-id",
        args.chat_id,
        "--markdown",
        message,
        "--idempotency-key",
        idempotency_key,
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def with_dry_run_placeholders(args: argparse.Namespace, info: DocInfo) -> DocInfo:
    if not args.dry_run:
        return info
    return DocInfo(
        url=info.url or DOC_URL_PLACEHOLDER,
        token=info.token or DOC_TOKEN_PLACEHOLDER,
        doc_type=info.doc_type or "docx",
    )


def main(argv: list[str]) -> int:
    args, report_args = parse_args(argv)
    try:
        ensure_scripts_exist()
        validate_forwarded_args(report_args)
        cli = resolve_cli(args.lark_cli)
        if args.check_auth:
            run_command([cli, "auth", "status"], verbose=args.verbose, label="check Lark auth")
        report_path = Path(args.report_output).expanduser() if args.report_output else default_report_output(args.project, args.age)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        title = args.title or f"{args.project} 长期未处理 Jira 报告"
        args.title = title

        run_command(
            build_generator_cmd(args, report_args, report_path),
            verbose=args.verbose,
            label="generate stale Jira report",
        )

        publish_stdout = run_command(
            build_publish_cmd(args, report_path, cli),
            verbose=args.verbose,
            label="publish Lark document",
        )
        existing_info = doc_info_from_text(args.doc or "")
        published_info = doc_info_from_text(publish_stdout)
        doc_info = with_dry_run_placeholders(args, merge_doc_info(published_info, existing_info))

        permission_status = "skipped"
        if args.grant_chat_view:
            run_command(
                build_permission_cmd(args, cli, doc_info),
                verbose=args.verbose or args.dry_run,
                label="grant chat view permission",
            )
            permission_status = "dry-run" if args.dry_run else "granted"

        message_status = "skipped"
        if args.chat_id:
            if not doc_info.url:
                raise PublishError("Could not determine document URL for message send.")
            run_command(
                build_message_cmd(args, cli, report_path, doc_info.url),
                verbose=args.verbose or args.dry_run,
                label="send Lark message",
            )
            message_status = "dry-run" if args.dry_run else "sent"

        print(f"Report: {report_path}")
        print(f"Lark document: {doc_info.url or '(created, URL not found in CLI output)'}")
        if doc_info.token:
            print(f"Lark document token: {doc_info.token}")
        print(f"Chat permission: {permission_status}")
        print(f"Chat message: {message_status}")
        return 0
    except PublishError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
