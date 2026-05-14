from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "llm_summary_runtime.py"
SPEC = importlib.util.spec_from_file_location("llm_summary_runtime", SCRIPT)
assert SPEC is not None
summary_runtime = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = summary_runtime
SPEC.loader.exec_module(summary_runtime)


class Scenario:
    llm_output_schema = {"symptom_summary": "string", "impact_summary": "string"}


class Provider:
    def __init__(self, result: object = None, *, fail: bool = False) -> None:
        self.result = result
        self.fail = fail
        self.calls = 0

    def summarize(self, matches: list[dict[str, object]], schema: dict[str, object], task: dict[str, object]) -> object:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider unavailable")
        return self.result


class LLMSummaryRuntimeTests(unittest.TestCase):
    def test_no_matches_do_not_call_provider(self) -> None:
        provider = Provider([])
        runtime = summary_runtime.LLMSummaryRuntime(provider)

        result = runtime.summarize([], {}, Scenario())

        self.assertEqual(result, [])
        self.assertEqual(provider.calls, 0)

    def test_valid_provider_schema_is_returned(self) -> None:
        provider = Provider([{"symptom_summary": "现象", "impact_summary": "影响"}])
        runtime = summary_runtime.LLMSummaryRuntime(provider)

        result = runtime.summarize([{"summary": "fallback"}], {}, Scenario())

        self.assertEqual(result, [{"symptom_summary": "现象", "impact_summary": "影响"}])
        self.assertEqual(provider.calls, 1)

    def test_missing_provider_fields_fall_back_per_field(self) -> None:
        provider = Provider([{"symptom_summary": "现象"}])
        runtime = summary_runtime.LLMSummaryRuntime(provider)

        result = runtime.summarize([{"summary": "Jira summary. second sentence"}], {}, Scenario())

        self.assertEqual(result[0]["symptom_summary"], "现象")
        self.assertEqual(result[0]["impact_summary"], "待人工确认影响范围")

    def test_provider_exception_uses_fallbacks(self) -> None:
        provider = Provider(fail=True)
        runtime = summary_runtime.LLMSummaryRuntime(provider)

        result = runtime.summarize([{"description": "Description first. second"}], {}, Scenario())

        self.assertEqual(result, [{"symptom_summary": "Description first.", "impact_summary": "待人工确认影响范围"}])
        self.assertEqual(provider.calls, 1)

    def test_without_provider_uses_summary_or_default_fallback(self) -> None:
        runtime = summary_runtime.LLMSummaryRuntime()

        result = runtime.summarize([{"summary": ""}], {}, Scenario())

        self.assertEqual(result, [{"symptom_summary": "待人工补充", "impact_summary": "待人工确认影响范围"}])


if __name__ == "__main__":
    unittest.main()
