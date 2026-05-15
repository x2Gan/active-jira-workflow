# active-jira-automation P0 设计冻结与外部契约确认

## 1. 文档目标

本文档用于完成 `active-jira-automation` 的 P0 阶段工作：

1. 冻结 OpenClaw 原生宿主模型下的框架与场景一边界。
2. 冻结首期外部依赖契约与执行消息契约。
3. 明确哪些事项在 P0 已经确定，哪些事项延后到实现阶段继续确认。

本文件是 P0 的正式确认记录，供以下文档引用：

- [active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)
- [active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md)
- [openclaw-native-message-templates](../active-jira-automation/references/openclaw-native-message-templates.md)
- [active-jira-automation 专项 TODO](./active-jira-automation-todo.md)

## 2. P0 已冻结结论

### 2.1 框架边界冻结

P0 冻结以下边界，不再在首期实现阶段反复调整：

1. `active-jira-automation` 按 OpenClaw 原生 skill 定位承接以下职责：创建期交互流程、JQL 设计规则、确认摘要格式、定时执行消息契约、共享 runner、检查点、去重、LLM 摘要、飞书 interactive 卡片投递。
2. OpenClaw 是调度、时区、session 生命周期、执行历史、任务 CRUD 与 announce 行为的宿主与唯一事实来源。
3. `active-jira-automation` 不重复承接通用 Jira 字段探测、JQL 教学、飞书认证或通用通讯录能力。
4. 首期 MVP 只接入一个场景：`jira-scheduled-query-alert`。
  - 该结论取代早期“仅接入 `new-p0-bug-alert`”的理解。
  - P0 Bug 仅作为通用查询提醒场景的样例筛选条件。
5. 后续新场景必须按“场景子能力 / 子方案”形式接入共享脚本与模板能力，不允许复制一套新的 runner 或发送链路。
6. `scripts/manage_tasks.py`、`scripts/task_store.py` 和 `scripts/scheduler_adapter.py` 可以作为本地开发或测试 harness 保留，但不再代表 OpenClaw 产品主路径。

### 2.2 OpenClaw 宿主契约冻结

P0 冻结的是“OpenClaw 宿主需要消费哪些结果字段”，而不是仓库内某个本地 scheduler adapter 的调用接口。

首期宿主侧最小任务载荷至少应覆盖以下字段：

| 宿主字段 | P0 结论 | 说明 |
| --- | --- | --- |
| `name` | 必填 | 用户可读任务名，对应 `task_name` |
| `cron` 或 `at` | 二选一 | `recurring` 映射 `cron`，`once` 映射 `at` |
| `tz` | 建议必填 | 默认建议 `Asia/Shanghai` |
| `session` | 必填 | 默认建议 `isolated` |
| `message` | 必填 | 使用确认后的配置生成稳定执行消息 |
| `announce` | 宿主控制 | 若飞书群已收到完整卡片，announce 只保留简短摘要 |
| `channel` / `to` | 按需 | 仅在需要把 announce 结果投递到指定频道时使用 |

冻结说明：

1. P0 不要求仓库内已经真实连通 OpenClaw CLI 或 SDK。
2. P0 也不要求本仓库暴露一个正式的本地调度 API 供 OpenClaw 调用。
3. P0 只要求 skill 输出的确认摘要、执行消息模板和运行时脚本边界固定，便于宿主接入。

### 2.3 定时执行消息契约冻结

P0 冻结以下执行消息规则：

1. OpenClaw 到期时必须向模型注入已确认配置，而不是再次给一个自由提示词让模型二次解释。
2. 执行消息至少应包含：`task_name`、`scenario_key`、`project/projects`、`filter_prompt`、`query_spec`、`base_jql`、`window_mode`、`lookback_minutes`、`schedule_type`、`schedule_expr`、`timezone`、`target_chat_id`、`notify_policy`、`message_template_key`。
3. 执行消息必须显式禁止模型修改 `base_jql`、重新选择目标群或改变消息结构。
4. 如果 OpenClaw 支持结构化 payload 注入，应优先使用结构化字段而不是大段自由文本。
5. 推荐模板见：[openclaw-native-message-templates](../active-jira-automation/references/openclaw-native-message-templates.md)。

### 2.4 飞书发送路径冻结

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

1. 这是首期实现路径，不等于未来必须永久保留 raw API fallback。
2. 如果后续在 `active-lark` 中增加 interactive 卡片发送辅助脚本，只要保持上述输出契约不变，就不影响框架层。
3. 如果 OpenClaw announce 也开启，不应重复发送完整 issue 内容；announce 默认只保留执行摘要。

### 2.5 Jira 字段读取契约冻结

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

### 2.6 首期运行策略冻结

以下策略在 P0 一并冻结：

1. 无命中时不调用 LLM。
2. 无命中时不生成卡片、不发送飞书消息。
3. 无命中时允许 OpenClaw 仅记录或播报简短执行摘要。
4. LLM 仅在命中后按批次调用。
5. LLM 输出只允许场景 schema 中声明的受控字段；通用查询提醒场景首期为 `match_reason`、`problem_summary`、`risk_assessment`。
6. 每个命中 Jira 首期单独发送一张 interactive 卡片。

## 3. P0 后仍保留为实现期确认项的事项

以下事项不再阻塞 P0，但仍需要在后续阶段继续确认：

1. OpenClaw 宿主是否支持结构化 payload 注入，还是只能使用长文本执行消息。
2. OpenClaw announce 结果与飞书卡片投递之间的重复信息策略如何统一。
3. 具体项目里 `来源` 字段的最终配置值是什么。
4. 是否需要在场景一首期就支持标签、组件等复合过滤条件。
5. 单次命中数量过大时是否启用卡片上限、分批发送或消息折叠。

## 4. P0 验收结论

本次 P0 设计冻结与外部契约确认，视为以下事项已完成：

1. OpenClaw 原生宿主模型下的框架公共能力边界已经固定。
2. 首期只接入 `jira-scheduled-query-alert` 已固定。
3. 宿主需要消费的确认摘要和执行消息契约已经固定。
4. 飞书 interactive 卡片首期发送路径已经固定为 raw API fallback。
5. Jira 关键字段的首期读取契约已经固定。

因此，`active-jira-automation` 可以按 OpenClaw 原生 skill 方向进入后续实现阶段。
