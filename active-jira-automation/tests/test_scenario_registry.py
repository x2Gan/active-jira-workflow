from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scenario_registry.py"
SPEC = importlib.util.spec_from_file_location("scenario_registry", SCRIPT)
assert SPEC is not None
scenario_registry = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = scenario_registry
SPEC.loader.exec_module(scenario_registry)


def make_spec(key: str = "jira-scheduled-query-alert") -> object:
    return scenario_registry.ScenarioSpec(
        scenario_key=key,
        display_name="Jira 定时查询并提醒",
        trigger_examples=("帮我创建一个 Geneva 项目新增 P0 BUG Jira 提醒任务",),
        config_schema={"project": {"required": True}},
        defaulting_rules="use issue_type=Bug and severity=P0 by default",
        query_builder="build Jira scheduled query alert",
        result_normalizer="normalize Jira fields",
        match_identity="task_id + issue_key + issue_created_at",
        llm_policy="on-match-only",
        llm_output_schema={"symptom_summary": "string", "impact_summary": "string"},
        message_template_key="lark-jira-query-alert-card-v1",
        renderer="interactive renderer",
        delivery_policy="one card per match",
        acceptance_cases=("create and resolve scenario successfully",),
    )


class ScenarioRegistryTests(unittest.TestCase):
    def test_register_and_get_scenario(self) -> None:
        registry = scenario_registry.ScenarioRegistry()
        spec = make_spec()

        registry.register(spec)

        self.assertEqual(registry.get("jira-scheduled-query-alert").display_name, spec.display_name)
        self.assertEqual(registry.list_keys(), ["jira-scheduled-query-alert"])

    def test_register_duplicate_scenario_fails(self) -> None:
        registry = scenario_registry.ScenarioRegistry()
        spec = make_spec()
        registry.register(spec)

        with self.assertRaises(scenario_registry.ScenarioRegistryError):
            registry.register(spec)

    def test_get_unknown_scenario_fails(self) -> None:
        registry = scenario_registry.ScenarioRegistry()

        with self.assertRaises(scenario_registry.ScenarioRegistryError):
            registry.get("missing-scenario")

    def test_validate_rejects_blank_key(self) -> None:
        registry = scenario_registry.ScenarioRegistry()
        spec = make_spec(key="   ")

        with self.assertRaises(scenario_registry.ScenarioRegistryError):
            registry.register(spec)
