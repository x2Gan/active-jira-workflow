#!/usr/bin/env python3
"""Helpers for rendering and validating Feishu/Lark interactive cards."""

from __future__ import annotations

import html
from typing import Any


ALLOWED_ELEMENT_TAGS = {"div", "hr", "note", "action"}
ALLOWED_TEXT_TAGS = {"plain_text", "lark_md"}
ALLOWED_ACTION_TAGS = {"button"}


class InteractiveCardValidationError(ValueError):
    """Raised when a card does not match the supported interactive subset."""


def truncate_text(value: str, max_length: int | None = None) -> str:
    if max_length is None or len(value) <= max_length:
        return value
    if max_length <= 1:
        return value[:max_length]
    return value[: max_length - 1] + "…"


def escape_lark_md(value: Any) -> str:
    text = "" if value is None else str(value)
    escaped = html.escape(text, quote=False)
    for char in ("\\", "`", "*", "_", "~"):
        escaped = escaped.replace(char, "\\" + char)
    return escaped


def safe_text(value: Any, *, fallback: str = "-", max_length: int | None = None, markdown: bool = True) -> str:
    text = fallback if value in (None, "", [], {}) else str(value)
    text = truncate_text(text, max_length)
    return escape_lark_md(text) if markdown else text


def text_node(
    content: Any,
    *,
    tag: str = "lark_md",
    fallback: str = "-",
    max_length: int | None = None,
    escape: bool = True,
) -> dict[str, str]:
    if tag not in ALLOWED_TEXT_TAGS:
        raise InteractiveCardValidationError(f"unsupported text tag: {tag}")
    if tag == "lark_md" and escape:
        value = safe_text(content, fallback=fallback, max_length=max_length, markdown=True)
    else:
        raw = fallback if content in (None, "", [], {}) else str(content)
        value = truncate_text(raw, max_length)
    return {"tag": tag, "content": value}


def validate_text_node(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise InteractiveCardValidationError(f"{path} must be an object")
    tag = value.get("tag")
    content = value.get("content")
    if tag not in ALLOWED_TEXT_TAGS:
        raise InteractiveCardValidationError(f"{path}.tag must be one of: {', '.join(sorted(ALLOWED_TEXT_TAGS))}")
    if not isinstance(content, str) or not content:
        raise InteractiveCardValidationError(f"{path}.content must be a non-empty string")


def validate_div(element: dict[str, Any], path: str) -> None:
    has_text = "text" in element
    has_fields = "fields" in element
    if not has_text and not has_fields:
        raise InteractiveCardValidationError(f"{path} must contain text or fields")
    if has_text:
        validate_text_node(element["text"], f"{path}.text")
    if has_fields:
        fields = element["fields"]
        if not isinstance(fields, list) or not fields:
            raise InteractiveCardValidationError(f"{path}.fields must be a non-empty list")
        for index, field in enumerate(fields):
            field_path = f"{path}.fields[{index}]"
            if not isinstance(field, dict):
                raise InteractiveCardValidationError(f"{field_path} must be an object")
            validate_text_node(field.get("text"), f"{field_path}.text")
            if "is_short" in field and not isinstance(field["is_short"], bool):
                raise InteractiveCardValidationError(f"{field_path}.is_short must be a boolean")


def validate_note(element: dict[str, Any], path: str) -> None:
    children = element.get("elements")
    if not isinstance(children, list) or not children:
        raise InteractiveCardValidationError(f"{path}.elements must be a non-empty list")
    for index, child in enumerate(children):
        validate_text_node(child, f"{path}.elements[{index}]")


def validate_action(element: dict[str, Any], path: str) -> None:
    actions = element.get("actions")
    if not isinstance(actions, list) or not actions:
        raise InteractiveCardValidationError(f"{path}.actions must be a non-empty list")
    for index, action in enumerate(actions):
        action_path = f"{path}.actions[{index}]"
        if not isinstance(action, dict):
            raise InteractiveCardValidationError(f"{action_path} must be an object")
        if action.get("tag") not in ALLOWED_ACTION_TAGS:
            raise InteractiveCardValidationError(f"{action_path}.tag must be button")
        validate_text_node(action.get("text"), f"{action_path}.text")
        if "url" in action and not isinstance(action["url"], str):
            raise InteractiveCardValidationError(f"{action_path}.url must be a string")
        if "value" in action and not isinstance(action["value"], dict):
            raise InteractiveCardValidationError(f"{action_path}.value must be an object")


def validate_element(element: Any, index: int) -> None:
    path = f"elements[{index}]"
    if not isinstance(element, dict):
        raise InteractiveCardValidationError(f"{path} must be an object")
    tag = element.get("tag")
    if tag not in ALLOWED_ELEMENT_TAGS:
        raise InteractiveCardValidationError(f"{path}.tag is unsupported: {tag}")
    if tag == "div":
        validate_div(element, path)
    elif tag == "note":
        validate_note(element, path)
    elif tag == "action":
        validate_action(element, path)


def validate_interactive_card(card: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(card, dict):
        raise InteractiveCardValidationError("card must be an object")
    config = card.get("config")
    if not isinstance(config, dict):
        raise InteractiveCardValidationError("config must be an object")
    header = card.get("header")
    if not isinstance(header, dict):
        raise InteractiveCardValidationError("header must be an object")
    validate_text_node(header.get("title"), "header.title")
    elements = card.get("elements")
    if not isinstance(elements, list) or not elements:
        raise InteractiveCardValidationError("elements must be a non-empty list")
    for index, element in enumerate(elements):
        validate_element(element, index)
    return card


def build_card(header_title: str, elements: list[dict[str, Any]], *, template: str = "red") -> dict[str, Any]:
    card = {
        "config": {"wide_screen_mode": True, "enable_forward": True},
        "header": {"template": template, "title": text_node(header_title, tag="plain_text", escape=False)},
        "elements": elements,
    }
    return validate_interactive_card(card)
