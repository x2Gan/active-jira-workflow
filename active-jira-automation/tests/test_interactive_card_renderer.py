from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "renderers" / "interactive_card_renderer.py"
SPEC = importlib.util.spec_from_file_location("interactive_card_renderer", SCRIPT)
assert SPEC is not None
renderer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = renderer
SPEC.loader.exec_module(renderer)


def valid_card() -> dict[str, object]:
    return renderer.build_card(
        "新增 P0 严重 BUG 提醒",
        [
            {"tag": "div", "text": {"tag": "lark_md", "content": "**GENEVA-1**\\nsummary"}},
            {"tag": "hr"},
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": "**Jira**\\nGENEVA-1"}},
                    {"is_short": True, "text": {"tag": "plain_text", "content": "Open"}},
                ],
            },
            {"tag": "note", "elements": [{"tag": "plain_text", "content": "Reporter: Alice"}]},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开 Jira"},
                        "url": "https://jira.example.com/browse/GENEVA-1",
                    }
                ],
            },
        ],
    )


class InteractiveCardRendererTests(unittest.TestCase):
    def test_validate_accepts_supported_card_subset(self) -> None:
        card = valid_card()

        self.assertIs(renderer.validate_interactive_card(card), card)

    def test_validate_rejects_missing_header(self) -> None:
        card = valid_card()
        card.pop("header")

        with self.assertRaises(renderer.InteractiveCardValidationError):
            renderer.validate_interactive_card(card)

    def test_validate_rejects_empty_elements(self) -> None:
        card = valid_card()
        card["elements"] = []

        with self.assertRaises(renderer.InteractiveCardValidationError):
            renderer.validate_interactive_card(card)

    def test_validate_rejects_illegal_element_tag(self) -> None:
        card = valid_card()
        card["elements"] = [{"tag": "img", "img_key": "abc"}]

        with self.assertRaises(renderer.InteractiveCardValidationError):
            renderer.validate_interactive_card(card)

    def test_text_node_escapes_dynamic_lark_markdown(self) -> None:
        node = renderer.text_node("GENEVA <1> *bold* `code`")

        self.assertEqual(node["content"], "GENEVA &lt;1&gt; \\*bold\\* \\`code\\`")

    def test_text_node_truncates_dynamic_content(self) -> None:
        node = renderer.text_node("abcdef", max_length=4)

        self.assertEqual(node["content"], "abc…")


if __name__ == "__main__":
    unittest.main()
