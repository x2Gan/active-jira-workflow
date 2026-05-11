# Active Jira Automation Scenario Access Contract

Every scenario registered in `active-jira-automation` must provide these fields:

- `scenario_key`
- `display_name`
- `trigger_examples`
- `config_schema`
- `defaulting_rules`
- `query_builder`
- `result_normalizer`
- `match_identity`
- `llm_policy`
- `llm_output_schema`
- `message_template_key`
- `renderer`
- `delivery_policy`
- `acceptance_cases`

Contract rules:

- scenarios plug into the shared runner
- scenarios do not send Feishu messages directly
- scenarios do not own their own scheduler implementation
- scenarios only contribute business-specific query, normalization, and template behavior