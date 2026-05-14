#!/usr/bin/env python3
"""Feishu/Lark interactive card delivery runtime."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from renderers.interactive_card_renderer import (  # noqa: E402
    InteractiveCardValidationError,
    validate_interactive_card,
)


class LarkDeliveryError(RuntimeError):
    """Raised when an interactive card cannot be delivered safely."""


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def serialize_interactive_content(card: dict[str, Any]) -> str:
    validate_interactive_card(card)
    return stable_json(card)


def generate_idempotency_key(card: dict[str, Any], target: dict[str, Any], *, prefix: str = "jira-auto") -> str:
    seed = stable_json({"card": card, "target": target.get("chat_id")})
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}-{digest}"


def build_send_request(card: dict[str, Any], target: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
    chat_id = target.get("chat_id")
    if not isinstance(chat_id, str) or not chat_id.strip():
        raise LarkDeliveryError("target.chat_id is required")
    return {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": serialize_interactive_content(card),
        "uuid": idempotency_key,
    }


def build_raw_api_command(
    request: dict[str, Any],
    *,
    lark_cli: str = "lark-cli",
    identity: str = "bot",
    dry_run: bool = False,
) -> list[str]:
    cmd = [
        lark_cli,
        "api",
        "POST",
        "/open-apis/im/v1/messages",
        "--params",
        stable_json({"receive_id_type": "chat_id"}),
        "--data",
        stable_json(request),
        "--as",
        identity,
        "--format",
        "json",
    ]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def default_command_runner(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise LarkDeliveryError(f"lark-cli failed with exit code {proc.returncode}: {err}")
    output = (proc.stdout or "").strip()
    if not output:
        return {"returncode": proc.returncode}
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return {"returncode": proc.returncode, "stdout": output}
    return parsed if isinstance(parsed, dict) else {"returncode": proc.returncode, "data": parsed}


class LarkDeliveryRuntime:
    """Validate and deliver interactive card payloads through Lark raw API."""

    def __init__(
        self,
        *,
        lark_cli: str = "lark-cli",
        identity: str = "bot",
        command_runner: Callable[[list[str]], dict[str, Any]] | None = None,
    ) -> None:
        self.lark_cli = lark_cli
        self.identity = identity
        self.command_runner = command_runner or default_command_runner

    def deliver(
        self,
        cards: list[dict[str, Any]],
        target: dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(cards, list):
            raise LarkDeliveryError("cards must be a list")
        messages: list[dict[str, Any]] = []
        for card in cards:
            try:
                validate_interactive_card(card)
            except InteractiveCardValidationError as exc:
                raise LarkDeliveryError(f"invalid interactive card: {exc}") from exc
            idempotency_key = generate_idempotency_key(card, target)
            request = build_send_request(card, target, idempotency_key)
            cmd = build_raw_api_command(request, lark_cli=self.lark_cli, identity=self.identity, dry_run=dry_run)
            if dry_run:
                response: dict[str, Any] = {"dry_run": True}
            else:
                response = self.command_runner(cmd)
            messages.append(
                {
                    "idempotency_key": idempotency_key,
                    "request": request,
                    "command": cmd,
                    "response": response,
                }
            )
        return {
            "dry_run": dry_run,
            "target": {"chat_id": target.get("chat_id"), "chat_name": target.get("chat_name")},
            "card_count": len(cards),
            "sent_count": 0 if dry_run else len(cards),
            "messages": messages,
        }
