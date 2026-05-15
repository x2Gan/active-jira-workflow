# active-jira-automation P0 设计冻结与外部契约确认

## 1. 文档目标

本文档用于完成 `active-jira-automation` 的 P0 阶段工作：

1. 冻结框架与场景一的边界。
2. 冻结首期外部依赖契约。
3. 明确哪些事项在 P0 已经确定，哪些事项延后到实现阶段继续确认。

本文件是 P0 的正式确认记录，供以下文档引用：

- [active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)
- [active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md)
- [active-jira-automation 专项 TODO](./active-jira-automation-todo.md)

## 2. P0 已冻结结论

### 2.1 框架边界冻结

P0 冻结以下边界，不再在首期实现阶段反复调整：

1. `active-jira-automation` 只承接自动化任务框架能力：任务管理、场景接入、统一 runner、检查点、去重、LLM 摘要、飞书 interactive 卡片投递。
2. `active-jira-automation` 不重复承接通用 Jira 字段探测、JQL 教学、飞书认证或通用通讯录能力。
3. 首期 MVP 只接入一个场景：`jira-scheduled-query-alert`。
   - 该结论取代早期“仅接入 `new-p0-bug-alert`”的理解。
   - P0 Bug 仅作为通用查询提醒场景的样例筛选条件。
4. 后续新场景必须按“场景子能力 / 子方案”形式接入框架，不允许复制一套新的 runner 或发送链路。

### 2.2 Openclaw 调度契约冻结

仓库当前没有 Openclaw 的真实接口实现，因此 P0 冻结的是“框架侧调度适配契约”，而不是某个具体 Openclaw SDK/CLI 的最终调用细节。

首期调度适配层对上必须暴露以下稳定接口：

1. `create_task(task_id, schedule_type, schedule_expr, runner_command, metadata)`
2. `pause_task(scheduler_task_id)`
3. `resume_task(scheduler_task_id)`
4. `delete_task(scheduler_task_id)`
5. `get_status(scheduler_task_id)`

其中：

- `runner_command` 固定指向框架统一入口：

```sh
python active-jira-automation/scripts/run_automation_task.py --task-id <TASK_ID>
```

- `metadata` 至少应包含：
  - `task_id`
  - `scenario_key`
  - `project`
  - `target_chat_id`
- 调度适配层返回值至少应包含：
  - `scheduler_task_id`
  - `status`
  - 可选 `next_run_at`

冻结规则：

- P0 不要求仓库内已经真实连通 Openclaw。
- P0 只要求框架侧接口固定，P3/P6 再做真实联调。

### 2.3 飞书发送路径冻结

首期飞书 interactive 卡片发送路径冻结为：

1. 由 `active-jira-automation` 生成合法的 interactive card JSON。
2. 由 `active-lark` 提供 raw API fallback 发送。
3. 首期目标接口固定为：

```text
POST /open-apis/im/v1/messages
```

发送契约冻结为：

- `receive_id_type = chat_id`
- `receive_id = oc_...`
- `msg_type = interactive`
- `content = <stringified interactive card JSON>`

冻结说明：

- 这是首期实现路径，不等于未来必须永久保留 raw API fallback。
- 如果后续在 `active-lark` 中增加 interactive 卡片发送辅助脚本，只要保持上述输出契约不变，就不影响框架层。

### 2.4 Jira 字段读取契约冻结

P0 对场景一涉及的关键字段做如下冻结：

| 业务字段 | 冻结读取规则 |
| --- | --- |
| Severity | 优先读取 `customfield_10401` |
| Priority | 回退读取 `priority` |
| Fix Version/s | 读取 `fixVersions` |
| 归属Team | 优先读取场景显式配置的 `team_field`；未配置时回退到常见字段名和 `customfield_11801`；只读展示，不固化枚举值 |
| 来源 | 不在框架层硬编码全局唯一字段 ID；冻结为场景可配置字段路径 `source_field_path` 或候选列表；未配置或读取失败时显示 `未设置` |

补充规则：

1. `Severity` 是缺陷风险判断的主字段，`Priority` 只作为回退或补充展示字段。
2. `归属Team` 属于组织归属敏感字段，只读展示，不在规则文档中固化具体枚举值。
3. `来源` 在当前仓库中没有可复用的全局稳定字段 ID 证据，因此 P0 冻结为“场景配置项”，不在框架层硬编码。

### 2.5 首期运行策略冻结

以下策略在 P0 一并冻结：

1. 无命中时不调用 LLM。
2. 无命中时不生成卡片、不发送飞书消息。
3. LLM 仅在命中后按批次调用。
4. LLM 输出只允许场景 schema 中声明的受控字段；通用查询提醒场景首期为 `match_reason`、`problem_summary`、`risk_assessment`。
5. 每个命中 Jira 首期单独发送一张 interactive 卡片。

## 3. P0 后仍保留为实现期确认项的事项

以下事项不再阻塞 P0，但仍需要在后续阶段继续确认：

1. Openclaw 的真实接口、鉴权方式和错误码如何映射到 `scheduler_adapter.py`。
2. 具体项目里 `来源` 字段的最终配置值是什么。
3. 是否需要在场景一首期就支持标签、组件等复合过滤条件。
4. 单次命中数量过大时是否启用卡片上限、分批发送或消息折叠。

## 4. P0 验收结论

本次 P0 设计冻结与外部契约确认，视为以下事项已完成：

1. 框架公共能力边界已经固定。
2. 首期只接入 `jira-scheduled-query-alert` 已固定。
3. 调度适配层的框架侧接口已经固定。
4. 飞书 interactive 卡片首期发送路径已经固定为 raw API fallback。
5. Jira 关键字段的首期读取契约已经固定。

因此，`active-jira-automation` 可以进入 P1 骨架实现阶段。
