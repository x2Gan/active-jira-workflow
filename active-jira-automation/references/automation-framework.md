# Active Jira Automation Framework

Use this reference for the shared framework contract of `active-jira-automation`.

Framework responsibilities:

- task lifecycle management
- scenario registration and lookup
- shared runner orchestration
- checkpointing and dedupe
- Feishu interactive card policy

Keep these boundaries stable:

- generic Jira mechanics stay in `../active-jira`
- generic Lark mechanics stay in `../active-lark`
- automation runtime stays in `active-jira-automation/scripts`

Current MVP scope:

- one supported scenario: `jira-scheduled-query-alert`
- one shared runner
- one scheduler adapter contract
- one interactive card delivery contract
