from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SCRIPT = SCRIPTS_DIR / "lark_delivery_runtime.py"
SPEC = importlib.util.spec_from_file_location("lark_delivery_runtime", SCRIPT)
assert SPEC is not None
delivery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = delivery
SPEC.loader.exec_module(delivery)


def card() -> dict[str, object]:
    return {
        "config": {"wide_screen_mode": True, "enable_forward": True},
        "header": {"template": "red", "title": {"tag": "plain_text", "content": "P0 Alert"}},
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "**GENEVA-1**"}}],
    }


class LarkDeliveryRuntimeTests(unittest.TestCase):
    def test_dry_run_returns_request_and_does_not_call_runner(self) -> None:
        calls: list[list[str]] = []
        runtime = delivery.LarkDeliveryRuntime(command_runner=lambda cmd: calls.append(cmd) or {"ok": True})

        result = runtime.deliver([card()], {"chat_id": "oc_123", "chat_name": "告警群"}, dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["sent_count"], 0)
        self.assertEqual(calls, [])
        message = result["messages"][0]
        self.assertEqual(message["request"]["receive_id"], "oc_123")
        self.assertEqual(message["request"]["msg_type"], "interactive")
        self.assertIn("--dry-run", message["command"])

    def test_invalid_payload_is_rejected_before_command_runner(self) -> None:
        calls: list[list[str]] = []
        runtime = delivery.LarkDeliveryRuntime(command_runner=lambda cmd: calls.append(cmd) or {"ok": True})
        bad_card = {"config": {}, "header": {"title": {"tag": "plain_text", "content": "x"}}, "elements": []}

        with self.assertRaises(delivery.LarkDeliveryError):
            runtime.deliver([bad_card], {"chat_id": "oc_123"})

        self.assertEqual(calls, [])

    def test_idempotency_key_is_stable_for_same_card_and_target(self) -> None:
        first = delivery.generate_idempotency_key(card(), {"chat_id": "oc_123"})
        second = delivery.generate_idempotency_key(card(), {"chat_id": "oc_123"})
        third = delivery.generate_idempotency_key(card(), {"chat_id": "oc_other"})

        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertTrue(first.startswith("jira-auto-"))

    def test_real_delivery_assembles_raw_api_command_and_target_params(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(cmd: list[str]) -> dict[str, object]:
            calls.append(cmd)
            return {"message_id": "om_123"}

        runtime = delivery.LarkDeliveryRuntime(lark_cli="lark-cli-test", command_runner=fake_runner)

        result = runtime.deliver([card()], {"chat_id": "oc_123"})

        self.assertEqual(result["sent_count"], 1)
        self.assertEqual(calls[0][:4], ["lark-cli-test", "api", "POST", "/open-apis/im/v1/messages"])
        params = json.loads(calls[0][calls[0].index("--params") + 1])
        data = json.loads(calls[0][calls[0].index("--data") + 1])
        content = json.loads(data["content"])
        self.assertEqual(params, {"receive_id_type": "chat_id"})
        self.assertEqual(data["receive_id"], "oc_123")
        self.assertEqual(data["msg_type"], "interactive")
        self.assertEqual(content["header"]["title"]["content"], "P0 Alert")
        self.assertIn("uuid", data)

    def test_missing_target_chat_id_fails(self) -> None:
        runtime = delivery.LarkDeliveryRuntime(command_runner=lambda cmd: {"ok": True})

        with self.assertRaises(delivery.LarkDeliveryError):
            runtime.deliver([card()], {})


if __name__ == "__main__":
    unittest.main()
