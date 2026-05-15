from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SCRIPT = SCRIPTS_DIR / "templates" / "lark_jira_query_alert_card_v1.py"
SPEC = importlib.util.spec_from_file_location("lark_jira_query_alert_card_v1", SCRIPT)
assert SPEC is not None
template = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = template
SPEC.loader.exec_module(template)

from renderers.interactive_card_renderer import validate_interactive_card  # noqa: E402


def match(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "key": "DEMO-1",
        "summary": "Customer escalation blocks release",
        "url": "https://jira.example.com/browse/DEMO-1",
        "created_at": "2026-05-14T08:30:00Z",
        "updated_at": "2026-05-14T08:45:00Z",
        "matched_at": "2026-05-14T09:00:00Z",
        "assignee": "Alice",
        "reporter": "Bob",
        "priority": "High",
        "severity": "P1",
        "status": "Open",
        "fix_versions": "2026.05",
        "labels": "customer-escalation",
        "components": "Checkout",
    }
    payload.update(overrides)
    return payload


def task(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"task_name": "Daily Jira Alert"}
    payload.update(overrides)
    return payload


def card_text(card: dict[str, object]) -> str:
    parts: list[str] = []
    for element in card["elements"]:
        if not isinstance(element, dict):
            continue
        text = element.get("text")
        if isinstance(text, dict):
            parts.append(str(text.get("content", "")))
        for field in element.get("fields", []) if isinstance(element.get("fields"), list) else []:
            if isinstance(field, dict) and isinstance(field.get("text"), dict):
                parts.append(str(field["text"].get("content", "")))
        for child in element.get("elements", []) if isinstance(element.get("elements"), list) else []:
            if isinstance(child, dict):
                parts.append(str(child.get("content", "")))
    return "\n".join(parts)


class LarkJiraQueryAlertCardV1Tests(unittest.TestCase):
    def test_render_complete_fields_as_valid_interactive_card(self) -> None:
        cards = template.render_cards(
            [match()],
            [{"match_reason": "Matches escalation filter", "risk_summary": "Release risk", "suggested_next_step": "Assign owner"}],
            task(),
        )

        self.assertEqual(len(cards), 1)
        card = validate_interactive_card(cards[0])
        text = card_text(card)
        self.assertEqual(card["header"]["title"]["content"], "Daily Jira Alert")
        self.assertEqual(card["header"]["template"], "orange")
        self.assertIn("DEMO-1", text)
        self.assertIn("Customer escalation blocks release", text)
        self.assertIn("[DEMO-1](https://jira.example.com/browse/DEMO-1)", text)
        self.assertIn("2026-05-14 09:00 UTC", text)
        self.assertIn("Alice", text)
        self.assertIn("P1", text)
        self.assertIn("Checkout", text)
        self.assertIn("Release risk", text)
        self.assertIn("Assign owner", text)

    def test_missing_assignee_version_and_priority_use_fallbacks(self) -> None:
        card = template.render_cards(
            [match(assignee="", fix_versions="", priority="", severity="")],
            [{"match_reason": "Matches filter"}],
            task(),
        )[0]

        text = card_text(card)
        self.assertIn("Unassigned", text)
        self.assertIn("**修复版本**\n未设置", text)
        self.assertIn("**优先级/Severity**\n未设置", text)
        self.assertEqual(card["header"]["template"], "blue")

    def test_long_summary_is_truncated(self) -> None:
        card = template.render_cards([match(summary="A" * 500)], [], task())[0]

        first_element = card["elements"][0]
        self.assertLessEqual(len(first_element["text"]["content"]), template.SUMMARY_MAX_LENGTH)
        self.assertTrue(first_element["text"]["content"].endswith("…"))

    def test_missing_llm_summary_uses_rule_fallbacks(self) -> None:
        card = template.render_cards([match(match_reason="Rule matched")], [], task())[0]

        text = card_text(card)
        self.assertIn("命中原因：Rule matched", text)
        self.assertIn("Customer escalation blocks release", text)
        self.assertIn("请责任人确认处理计划", text)

    def test_no_priority_or_severity_uses_neutral_color(self) -> None:
        card = template.render_cards([match(priority="", severity="")], [], task())[0]

        self.assertEqual(card["header"]["template"], "blue")

    def test_task_can_override_header_color_and_default_title_is_used(self) -> None:
        card = template.render_cards([match(priority="", severity="")], [], task(task_name="", card_header_template="green"))[0]

        self.assertEqual(card["header"]["template"], "green")
        self.assertEqual(card["header"]["title"]["content"], "Jira 查询命中提醒")


if __name__ == "__main__":
    unittest.main()
