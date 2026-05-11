# Active Jira Automation Task Lifecycle

Task states:

- `enabled`
- `paused`
- `deleted`

Allowed transitions:

- `create -> enabled`
- `enabled -> paused`
- `paused -> enabled`
- `enabled|paused -> deleted`

Lifecycle rules:

- prefer `task_id` for state-changing operations
- delete is logical by default and should retain historical runtime logs
- no scenario may bypass the shared lifecycle rules