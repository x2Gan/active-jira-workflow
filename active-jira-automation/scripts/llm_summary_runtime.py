#!/usr/bin/env python3
"""LLM summary runtime with schema guardrails and fallback behavior."""

from __future__ import annotations

import re
from typing import Any, Protocol


SUMMARY_FIELDS = ("symptom_summary", "impact_summary")
DEFAULT_SYMPTOM_FALLBACK = "待人工补充"
DEFAULT_IMPACT_FALLBACK = "待人工确认影响范围"


class SummaryProvider(Protocol):
    def summarize(self, matches: list[dict[str, Any]], schema: dict[str, Any], task: dict[str, Any]) -> Any:
        """Return provider-specific structured summaries."""


def first_sentence(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return ""
    match = re.search(r"([。！？.!?])", text)
    if not match:
        return text
    return text[: match.end()]


def fallback_summary(match: dict[str, Any]) -> dict[str, str]:
    symptom = first_sentence(match.get("summary")) or first_sentence(match.get("description")) or DEFAULT_SYMPTOM_FALLBACK
    return {
        "symptom_summary": symptom,
        "impact_summary": DEFAULT_IMPACT_FALLBACK,
    }


def normalize_provider_item(item: Any, fallback: dict[str, str]) -> dict[str, str]:
    if not isinstance(item, dict):
        return fallback
    normalized: dict[str, str] = {}
    for field in SUMMARY_FIELDS:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            normalized[field] = value.strip()
        else:
            normalized[field] = fallback[field]
    return normalized


class LLMSummaryRuntime:
    """Batch summarize matched Jira records through an optional provider."""

    def __init__(self, provider: SummaryProvider | None = None) -> None:
        self.provider = provider

    def summarize(self, matches: list[dict[str, Any]], task: dict[str, Any], scenario: Any) -> list[dict[str, str]]:
        if not matches:
            return []
        fallbacks = [fallback_summary(match) for match in matches]
        if self.provider is None:
            return fallbacks
        try:
            raw = self.provider.summarize(matches, getattr(scenario, "llm_output_schema", {}), task)
        except Exception:
            return fallbacks
        if isinstance(raw, dict) and isinstance(raw.get("summaries"), list):
            raw_items = raw["summaries"]
        elif isinstance(raw, list):
            raw_items = raw
        else:
            return fallbacks
        summaries: list[dict[str, str]] = []
        for index, fallback in enumerate(fallbacks):
            item = raw_items[index] if index < len(raw_items) else {}
            summaries.append(normalize_provider_item(item, fallback))
        return summaries
