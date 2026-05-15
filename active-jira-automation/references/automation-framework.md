# Active Jira Automation Framework

Use this reference for the shared framework contract of `active-jira-automation`.

Default host model:

- OpenClaw is the default host runtime for this skill.
- OpenClaw owns schedule persistence, timezone, session lifecycle, announce behavior, and job history.
- `active-jira-automation` owns business prompting, JQL design rules, reusable runtime scripts, checkpointing, dedupe, and Feishu interactive card policy.
- Other platforms may integrate later, but they should map onto the same host contract rather than redefine business flow.

Framework responsibilities:

- OpenClaw-facing creation workflow and confirmation summary contract
- scenario registration and lookup
- shared runner orchestration
- checkpointing and dedupe
- Feishu interactive card policy
- deterministic execution message contract for scheduled runs

Keep these boundaries stable:

- generic Jira mechanics stay in `../active-jira`
- generic Lark mechanics stay in `../active-lark`
- automation runtime stays in `active-jira-automation/scripts`
- host job CRUD, status, and execution history stay in the host platform, with OpenClaw as the default implementation

Compatibility note:

- local task store, scheduler adapter, and task CRUD scripts may exist as development or test harnesses
- those harnesses are not the product path and must not redefine the host contract

Current MVP scope:

- one supported scenario: `jira-scheduled-query-alert`
- one shared runner
- one OpenClaw-first host contract
- one interactive card delivery contract
- one set of OpenClaw-native message templates
