#!/usr/bin/env python3
"""Publish a Markdown file to Lark Docs through the official lark-cli."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update a Lark document from a local Markdown file."
    )
    parser.add_argument("markdown_file", help="Markdown file to publish")
    parser.add_argument(
        "--doc",
        help="Existing Lark document URL or token. If omitted, a new doc is created.",
    )
    parser.add_argument(
        "--command",
        choices=("append", "overwrite"),
        default="append",
        help="Update command when --doc is supplied.",
    )
    parser.add_argument(
        "--parent-token",
        help="Parent folder or wiki-node token for docs +create.",
    )
    parser.add_argument(
        "--parent-position",
        help="Parent position for docs +create, for example my_library.",
    )
    parser.add_argument(
        "--title",
        help="Prepend this as an H1 heading before creating/updating the document.",
    )
    parser.add_argument(
        "--as",
        dest="as_identity",
        choices=("user", "bot"),
        default="user",
        help="Identity type passed to lark-cli.",
    )
    parser.add_argument(
        "--lark-cli",
        default="lark-cli",
        help="Path or command name for lark-cli.",
    )
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="Run lark-cli auth status before publishing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to lark-cli so no document is changed.",
    )
    return parser.parse_args()


def resolve_cli(cli: str) -> str:
    if "/" in cli:
        path = Path(cli)
        if path.exists():
            return str(path)
        raise SystemExit(f"lark-cli not found: {cli}")

    resolved = shutil.which(cli)
    if resolved:
        return resolved
    raise SystemExit("lark-cli not found on PATH. Run: sh lark-cli.sh install")


def content_payload(markdown_file: Path, title: str | None) -> str:
    if not markdown_file.is_file():
        raise SystemExit(f"Markdown file not found: {markdown_file}")

    original = markdown_file.read_text(encoding="utf-8")
    if not title:
        return original

    title_line = f"# {title.strip()}\n\n"
    return original if original.lstrip().startswith("# ") else title_line + original


def print_command(cmd: list[str]) -> None:
    print("+ " + " ".join(shlex.quote(part) for part in cmd), file=sys.stderr)


def main() -> int:
    args = parse_args()
    cli = resolve_cli(args.lark_cli)

    if args.check_auth:
        auth_cmd = [cli, "auth", "status"]
        print_command(auth_cmd)
        auth_result = subprocess.run(auth_cmd, check=False)
        if auth_result.returncode != 0:
            return auth_result.returncode

    markdown_file = Path(args.markdown_file).expanduser()
    content = content_payload(markdown_file, args.title)

    if args.doc:
        cmd = [
            cli,
            "docs",
            "+update",
            "--api-version",
            "v2",
            "--as",
            args.as_identity,
            "--doc",
            args.doc,
            "--command",
            args.command,
            "--doc-format",
            "markdown",
            "--content",
            "-",
        ]
    else:
        cmd = [
            cli,
            "docs",
            "+create",
            "--api-version",
            "v2",
            "--as",
            args.as_identity,
            "--doc-format",
            "markdown",
            "--content",
            "-",
        ]
        if args.parent_token:
            cmd.extend(["--parent-token", args.parent_token])
        if args.parent_position:
            cmd.extend(["--parent-position", args.parent_position])

    if args.dry_run:
        cmd.append("--dry-run")

    print_command(cmd)
    print(f"# content stdin: {markdown_file}", file=sys.stderr)
    result = subprocess.run(cmd, input=content, text=True, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
