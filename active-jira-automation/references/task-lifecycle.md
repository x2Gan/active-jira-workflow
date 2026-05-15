# Active Jira Automation Task Lifecycle

This reference describes task lifecycle under the default OpenClaw host model.

Source of truth:

- OpenClaw is the source of truth for scheduled job creation, pause or resume, deletion, execution history, and current host status.
- `active-jira-automation` is the source of truth for business task specification, confirmation summary, execution message, and shared runtime behavior.

Host-facing task states:

- `enabled`
- `paused`
- `deleted`

Allowed transitions:

- `create -> enabled`
- `enabled -> paused`
- `paused -> enabled`
- `enabled|paused -> deleted`

Lifecycle rules:

- prefer host job ID or unique task name for state-changing operations
- delete is logical by default and should retain host execution history plus runtime logs when available
- no scenario may bypass the shared lifecycle rules
- editing a task means regenerating the business confirmation summary before the host updates its scheduled job
- if a non-OpenClaw host cannot express pause or resume directly, it must map to an equivalent enable or disable behavior without changing scenario semantics

Creation rules:

- do not create a scheduled job before the user confirms the summary
- treat `query_spec`, `base_jql`, `window_mode`, `target_chat_id`, and schedule fields as immutable inputs for the execution message once confirmed
- default to `session isolated` for scheduled execution unless the user explicitly asks for persistent memory

Execution rules:

- scheduled execution must run from confirmed configuration, not from a fresh reinterpretation of the user's intent
- if there are no matches, do not call LLM or send Feishu messages
- if there are matches, use the shared runner and approved interactive card template