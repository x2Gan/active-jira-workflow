#!/usr/bin/env python3
"""Shared registry for active-jira-automation scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any


class ScenarioRegistryError(RuntimeError):
    """Raised when scenario registration or lookup fails."""


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_key: str
    display_name: str
    trigger_examples: tuple[str, ...]
    config_schema: dict[str, Any]
    defaulting_rules: Any
    query_builder: Any
    result_normalizer: Any
    match_identity: Any
    llm_policy: str
    llm_output_schema: dict[str, Any]
    message_template_key: str
    renderer: Any
    delivery_policy: Any
    acceptance_cases: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_scenario_spec(spec: ScenarioSpec) -> None:
    if not spec.scenario_key.strip():
        raise ScenarioRegistryError("scenario_key must not be blank")
    if not spec.display_name.strip():
        raise ScenarioRegistryError("display_name must not be blank")
    if not spec.trigger_examples:
        raise ScenarioRegistryError("trigger_examples must not be empty")
    if not spec.config_schema:
        raise ScenarioRegistryError("config_schema must not be empty")
    if not spec.llm_policy.strip():
        raise ScenarioRegistryError("llm_policy must not be blank")
    if not spec.message_template_key.strip():
        raise ScenarioRegistryError("message_template_key must not be blank")
    if not spec.acceptance_cases:
        raise ScenarioRegistryError("acceptance_cases must not be empty")


class ScenarioRegistry:
    """In-memory registry for scenario specs.

    This is intentionally minimal for P1: it provides registration, lookup,
    and a validation entrypoint for the scenario access contract.
    """

    def __init__(self) -> None:
        self._specs: dict[str, ScenarioSpec] = {}

    def register(self, spec: ScenarioSpec) -> None:
        validate_scenario_spec(spec)
        if spec.scenario_key in self._specs:
            raise ScenarioRegistryError(f"scenario already registered: {spec.scenario_key}")
        self._specs[spec.scenario_key] = spec

    def get(self, scenario_key: str) -> ScenarioSpec:
        try:
            return self._specs[scenario_key]
        except KeyError as exc:
            raise ScenarioRegistryError(f"unknown scenario: {scenario_key}") from exc

    def list_keys(self) -> list[str]:
        return sorted(self._specs)

    def validate_registered(self) -> None:
        for spec in self._specs.values():
            validate_scenario_spec(spec)


def register_default_scenarios(registry: ScenarioRegistry) -> ScenarioRegistry:
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from scenarios.jira_scheduled_query_alert import get_scenario_spec

    registry.register(get_scenario_spec())
    return registry


def default_registry() -> ScenarioRegistry:
    return register_default_scenarios(ScenarioRegistry())
