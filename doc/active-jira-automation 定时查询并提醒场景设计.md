# active-jira-automation 场景一方案设计：OpenClaw 原生 Jira 定时查询并提醒

## 1. 文档定位

本文档是 `active-jira-automation` 的场景子方案，描述“按用户自定义筛选条件定时查询 Jira，并在命中时发送飞书群提醒”的业务规则、OpenClaw 宿主接入方式、执行约束和模板规范。

框架公共能力设计见主文档：[active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)。
外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。
OpenClaw 直接可用模板见：[openclaw-native-message-templates](../active-jira-automation/references/openclaw-native-message-templates.md)。

本文只描述场景一，不重复定义通用 Jira 能力、Lark 能力或 OpenClaw 自身的定时任务管理能力。

## 2. 宿主模型与设计修正

场景一现在明确采用 OpenClaw 原生宿主模型。用户的真实目标是：

1. 用户在 OpenClaw 对话中用自然语言描述任意合理的 Jira 筛选目标。
2. OpenClaw 借助本 skill 的交互流程补齐必要信息，并把意图转成明确、可审计的 `query_spec` 和 `base_jql`。
3. OpenClaw 使用自己的原生定时机制保存 cron 或一次性任务、时区、session 和执行历史。
4. OpenClaw 到期时向模型注入已经确认过的任务配置，驱动稳定、复用的共享脚本执行。
5. 有命中数据时，做轻量分析并把消息卡片发送到指定飞书群。

因此，场景一不应再把 `P0 + Bug` 写死在场景代码、模板名称或验收标准中，也不应再把本地 task store、scheduler adapter、pause or resume 状态机当成产品主路径。`P0 Bug` 只能作为用户提示示例，不能成为场景边界。

关键设计调整：

- 从“本地自动化任务框架”改为“OpenClaw 宿主 + skill 业务契约”。
- 从“skill 自己创建调度任务”改为“OpenClaw 依据确认摘要创建原生定时任务”。
- 从“调度适配层接口为主”改为“创建期确认摘要 + 定时执行消息模板为主”。
- 从“场景代码构造固定 P0 查询”改为“创建期编译查询规格，运行期稳定脚本参数化执行”。
- 保留零命中零 Token、去重、检查点、dry-run、interactive 卡片投递等运行约束。

## 3. 场景定位

### 3.1 场景名称

- 场景名称：Jira 定时查询并提醒
- `scenario_key`：`jira-scheduled-query-alert`
- 消息模板：`lark-jira-query-alert-card-v1`

### 3.2 用户意图示例

- 每小时查询一次 Geneva 项目新增的 P0 Bug，并推送到测试告警群。
- 每天上午 10 点检查 GENEVA 里状态还是 Open 的 Release Blocker。
- 每 30 分钟提醒一次最近有更新、且 assignee 为空的线上反馈 Jira。
- 明天早上 9 点检查本周新建且带有 `customer-escalation` 标签的 Jira。
- 每天下班前把今天新建的高优先级 Bug 发到项目值班群。

### 3.3 场景目标

该场景的目标是：

1. 通过 OpenClaw 对话式流程收集并确认任务配置。
2. 将用户自然语言筛选条件转成可确认、可执行的 `query_spec` 与 `base_jql`。
3. 让 OpenClaw 创建一个原生定时任务，周期性触发稳定复用的查询脚本。
4. 没有命中数据时不调用 LLM、不产生飞书外部副作用。
5. 有命中数据时，对结果做轻量分析与归纳，发送固定结构的飞书 interactive 卡片。

## 4. 场景输入与交互引导

### 4.1 业务配置项

创建该任务时，OpenClaw 需要借助本 skill 收集或确认以下业务配置：

| 配置项 | 说明 | 是否可从用户话术推断 |
| --- | --- | --- |
| `task_name` | OpenClaw 中展示的任务名称 | 可以 |
| `project` / `projects` | Jira 项目 Key，例如 `GENEVA` | 可以 |
| `filter_prompt` | 用户自然语言筛选意图 | 用户必须给出 |
| `query_spec` | 结构化查询规格，包含字段、操作符、值、排序等 | OpenClaw 生成，用户确认 |
| `base_jql` | 不含运行窗口的基础 JQL | OpenClaw 生成，用户确认 |
| `window_mode` | `created`、`updated` 或 `snapshot` | 需要确认或默认 |
| `schedule_type` | `recurring` 或 `once` | 需要确认 |
| `schedule_expr` | cron 表达式、相对时间或绝对时间 | 需要确认 |
| `target_chat_name` | 目标群名称 | 可以从提示词推断 |
| `target_chat_id` | 飞书群稳定 ID，`oc_...` | 运行前必须确认 |
| `notify_policy` | 单 Jira 卡片、批量摘要、单轮上限、snapshot 重复策略 | 可默认 |

### 4.2 OpenClaw 宿主元数据

以下字段通常由 OpenClaw 宿主控制，但仍应出现在确认摘要里，以便用户审计最终任务语义：

| 宿主字段 | 默认建议 | 说明 |
| --- | --- | --- |
| `timezone` | `Asia/Shanghai` | 对齐 OpenClaw 的 `tz` 语义 |
| `openclaw_session` | `isolated` | 默认隔离会话，避免执行期重新解释业务意图 |
| `announce_policy` | compact | 如果飞书群已收到完整卡片，OpenClaw announce 只保留简短摘要 |
| `execution_message` | 由模板生成 | 使用已确认配置生成稳定执行消息，不允许自由发挥 |

### 4.3 推荐追问顺序

1. 筛选目标：要查什么 Jira，哪些字段、状态、标签、版本、负责人、优先级或时间范围。
2. 查询项目：单项目或多项目；如果提示里已有项目 Key，可直接确认。
3. 窗口语义：只看新增、只看更新，还是每次检查当前仍命中的存量数据。
4. 调度方式：周期还是单次；cron、相对时间或具体执行时间。
5. 时区：如果用户未指定，默认 `Asia/Shanghai`。
6. 推送群组：群名或稳定 `chat_id`。
7. 通知策略：单条发送、批量汇总、最大提醒数量、是否重复提醒存量数据。

### 4.4 默认规则

当用户没有显式指定时，建议采用以下默认：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `window_mode` | `created` | 按“新增”语义查询，最符合提醒场景，避免每轮重复命中存量数据 |
| `lookback_minutes` | `5` | 查询窗口回看 5 分钟，靠去重避免重复发送 |
| `notify_policy.mode` | `per_issue` | 每条 Jira 单独一张卡片，便于群内跟进 |
| `notify_policy.max_issues_per_run` | `20` | 防止异常 JQL 一次刷屏 |
| `llm_policy` | `on-match-only` | 只有命中后才做轻量分析 |
| `sort` | `created ASC` 或 `updated ASC` | 与窗口字段一致 |
| `timezone` | `Asia/Shanghai` | 对齐 OpenClaw 常见使用场景 |
| `openclaw_session` | `isolated` | 降低上下文漂移风险 |

### 4.5 创建确认摘要

场景一在创建前应向用户展示固定摘要，至少包括：

- 任务名称
- 场景标识：`jira-scheduled-query-alert`
- Jira 项目范围
- 用户原始筛选意图
- `query_spec` 摘要或 JSON
- Agent 生成的基础 `base_jql`
- 窗口语义与查询窗口说明
- 调度方式
- 时区
- OpenClaw session 模式
- 推送目标群
- 通知策略与单次上限
- LLM 策略：仅命中后调用
- 卡片模板版本：`lark-jira-query-alert-card-v1`

创建期确认摘要的推荐格式见：[openclaw-native-message-templates](../active-jira-automation/references/openclaw-native-message-templates.md)。

只有用户确认摘要后，才允许 OpenClaw 创建原生定时任务。

## 5. 查询规格与 JQL 生成

### 5.1 两阶段设计

场景一采用两阶段执行：

1. 创建期：OpenClaw 根据用户提示生成 `query_spec` 和 `base_jql`，并让用户确认。
2. 运行期：稳定查询脚本读取确认后的任务配置，把 `base_jql` 与运行窗口组合成最终 JQL 后执行。

这里的“注入”指参数化注入 JQL 和窗口参数，不是为每个任务动态生成或修改脚本代码。

### 5.2 查询规格建议

OpenClaw 侧保存的确认任务规格建议同时包含自然语言、结构化规格和最终 JQL：

```json
{
  "task_name": "Geneva P0 Bug Alert",
  "filter_prompt": "每小时查询一次 GENEVA 新增的 P0 Bug",
  "query_spec": {
    "projects": ["GENEVA"],
    "clauses": [
      {"field": "issuetype", "op": "=", "value": "Bug"},
      {"field": "customfield_10401", "alias": "Severity", "op": "=", "value": "P0"}
    ],
    "order_by": [{"field": "created", "direction": "ASC"}]
  },
  "base_jql": "project = GENEVA AND issuetype = Bug AND \"Severity\" = P0",
  "window_mode": "created",
  "schedule_type": "recurring",
  "schedule_expr": "0 * * * *",
  "timezone": "Asia/Shanghai",
  "target_chat_id": "oc_xxx"
}
```

保存 `query_spec` 的价值是便于审计、后续编辑和字段校验；保存 `base_jql` 的价值是让运行期脚本可以稳定执行。

### 5.3 JQL 生成约束

OpenClaw 在创建期生成 JQL 时必须遵守：

- 不把 P0、Bug、项目 Key、状态等业务条件写死在场景代码中。
- 所有用户给出的字段和值必须进入确认摘要。
- 涉及自定义字段时，优先使用已知字段别名；无法确认时提示用户或通过 Jira 字段探测能力确认。
- 不把自然语言直接拼接到 shell 命令；JQL 作为任务配置字段传入查询 runtime。
- 运行窗口由 runtime 追加，避免用户 JQL 与检查点逻辑互相覆盖。

### 5.4 最终 JQL 组合

运行期最终 JQL 建议按以下方式生成：

```text
(<base_jql>)
AND <window_field> >= "<window_start>"
AND <window_field> < "<window_end>"
ORDER BY <window_field> ASC
```

其中：

- `window_mode = created` 时，`window_field = created`。
- `window_mode = updated` 时，`window_field = updated`。
- `window_mode = snapshot` 时，不追加时间窗口，只执行 `base_jql`，但必须依赖去重和通知策略避免重复刷屏。

### 5.5 命中查询与详情补全分层

运行期查询脚本只负责回答“本轮命中了哪些 Jira”，推荐输出最小命中对象：

```json
[
  {"key": "GENEVA-2034", "created_at": "2026-05-15T06:18:00Z", "updated_at": "2026-05-15T06:30:00Z"}
]
```

其中 `created_at` 或 `updated_at` 用于窗口模式去重；卡片所需的 Summary、负责人、Reporter、Severity、Priority、状态、影响版本、归属团队等详情，应在去重和单轮上限过滤之后，再通过 `active-jira` 或本地 `jira issue view <KEY> --raw` 补全。这样零命中、重复命中和超出上限的 Jira 都不会触发详情拉取、LLM 调用或飞书发送。

## 6. 查询窗口、命中与去重规则

### 6.1 窗口模式

| 模式 | 适用场景 | 查询窗口 | 去重建议 |
| --- | --- | --- | --- |
| `created` | 新增 Jira 提醒 | `created >= last_checkpoint - overlap` 且 `created < now` | `task_id + issue_key + created` |
| `updated` | 最近更新 Jira 提醒 | `updated >= last_checkpoint - overlap` 且 `updated < now` | `task_id + issue_key + updated` |
| `snapshot` | 当前仍满足条件的存量巡检 | 不追加窗口 | `task_id + issue_key + base_jql_hash`，默认只首次提醒 |

### 6.2 检查点规则

- 首次运行起点由 OpenClaw 创建任务时间、显式 `start_at` 或宿主侧初始状态决定。
- 正常运行后，将 `last_checkpoint` 更新为本次 `window_end`。
- 查询失败时不推进检查点。
- 使用 `lookback_minutes` 回看窗口降低调度抖动导致的漏数风险。

### 6.3 无命中行为

当查询结果为空时，只执行以下动作：

1. 更新检查点。
2. 写入运行日志或宿主侧执行结果。
3. 正常退出。

不得执行：

- LLM 调用
- 卡片渲染
- 飞书发送

## 7. OpenClaw 宿主侧任务创建与执行契约

### 7.1 宿主字段映射

本场景建议把以下结果交给 OpenClaw 定时机制管理：

| 场景结果 | OpenClaw 宿主语义 | 说明 |
| --- | --- | --- |
| `task_name` | `name` | 用户可读任务名 |
| `schedule_type=recurring` | `cron` | 使用 cron 表达式 |
| `schedule_type=once` | `at` | 使用一次性执行时间 |
| `timezone` | `tz` | 默认建议 `Asia/Shanghai` |
| `openclaw_session` | `session` | 默认建议 `isolated` |
| `execution_message` | `message` | 使用已确认配置生成的稳定执行消息 |
| `announce_policy` | `announce` / `channel` | 如同时向飞书群投递卡片，announce 只保留简短摘要 |

这里表达的是宿主字段映射，不要求本仓库必须封装 OpenClaw CLI。

### 7.2 定时执行消息约束

定时执行消息必须满足：

- 明确说明当前执行的是 `jira-scheduled-query-alert`。
- 注入已确认的 `filter_prompt`、`query_spec`、`base_jql`、`window_mode`、`schedule_type`、`schedule_expr`、`timezone`、`target_chat_id`、`notify_policy`。
- 禁止模型重新解释用户意图、修改 `base_jql`、重新选择群组或改变消息结构。
- 明确要求优先使用共享脚本，而不是在执行期重新创造一套临时逻辑。

推荐消息格式见：[openclaw-native-message-templates](../active-jira-automation/references/openclaw-native-message-templates.md)。

### 7.3 建议执行流程

1. OpenClaw 收集用户筛选意图、项目、窗口语义、调度、时区、群组和通知策略。
2. OpenClaw 生成 `query_spec` 与 `base_jql`，输出创建确认摘要。
3. 用户确认后，OpenClaw 创建原生定时任务。
4. OpenClaw 到期时向模型注入稳定执行消息。
5. 共享 runtime 将 `base_jql` 与运行窗口组合成最终 JQL。
6. 通用 Jira 运行时执行查询，只返回 Jira key 与窗口身份字段。
7. 场景根据 key、created、updated 或 base_jql_hash 生成去重键。
8. 通用去重逻辑过滤已发送记录，并按 `notify_policy.max_issues_per_run` 截断。
9. 如有新命中：
   - 调用 `active-jira` 能力按 Jira key 拉取详情。
   - 场景归一化逻辑整理卡片字段。
   - 调用 LLM 生成受控轻量分析。
   - 交给场景模板渲染器生成 `lark-jira-query-alert-card-v1`。
   - 由通用投递层发送 interactive 卡片。
10. 更新检查点、运行日志和投递结果。

重要约束：

- 查询脚本必须是纯确定性逻辑，不依赖 LLM。
- LLM 可以参与创建期 JQL 草拟，但必须经用户确认后才能成为执行配置。
- 运行期不得让 LLM 修改 JQL、选择群组或决定是否发送。
- 卡片骨架必须由代码生成，不能让 LLM 直接输出整张卡片 JSON。
- LLM 只负责补充少量受控字段，例如“命中原因”“问题摘要”“风险评估”。

## 8. 场景接入实现与可复用资产

### 8.1 场景接入主文档的实现映射

场景一按主文档中的“场景接入契约”接入，建议映射如下：

| 接入项 | 场景一实现 |
| --- | --- |
| `scenario_key` | `jira-scheduled-query-alert` |
| `display_name` | Jira 定时查询并提醒 |
| `config_schema` | `project/projects`、`filter_prompt`、`query_spec`、`base_jql`、`window_mode`、`schedule_type`、`schedule_expr`、`target_chat_id`、`notify_policy` |
| `defaulting_rules` | 默认 `window_mode=created`、`lookback_minutes=5`、`notify_policy.mode=per_issue` |
| `query_builder` | 将 `base_jql` 与运行窗口组合成最终 JQL |
| `result_normalizer` | 归一化 Jira Key、Summary、URL、创建时间、责任人、Reporter、Priority、Severity、Status、Affects Version、归属团队、命中原因 |
| `match_identity` | 根据 `window_mode` 生成稳定去重键 |
| `llm_policy` | `on-match-only` |
| `llm_output_schema` | `match_reason`、`problem_summary`、`risk_assessment` |
| `message_template_key` | `lark-jira-query-alert-card-v1` |
| `renderer` | 输出飞书 interactive card JSON |
| `delivery_policy` | 支持单条卡片、批量摘要、dry-run、幂等发送和单次上限 |

宿主字段如 `timezone`、`openclaw_session`、`announce_policy` 不属于场景业务 schema，本场景只要求这些值在创建摘要和执行消息中可审计。

### 8.2 可复用脚本资产

本场景建议依附框架目录结构落地，不再新增独立专用 runner。推荐资产如下：

```text
active-jira-automation/
   scripts/
      run_automation_task.py
      jira_query_runtime.py
      scenarios/
         jira_scheduled_query_alert.py
      templates/
         lark_jira_query_alert_card_v1.py
      renderers/
         interactive_card_renderer.py
```

职责建议：

- `run_automation_task.py`：共享 deterministic runner，适合本地联调或宿主编排调用。
- `jira_query_runtime.py`：JQL 组合、窗口计算、检查点与查询身份字段处理。
- `scenarios/jira_scheduled_query_alert.py`：场景配置、字段归一化、去重键和 LLM schema。
- `templates/lark_jira_query_alert_card_v1.py`：通用提醒卡片模板定义。
- `renderers/interactive_card_renderer.py`：interactive 卡片渲染与校验能力。

`scripts/manage_tasks.py`、`scripts/task_store.py` 和 `scripts/scheduler_adapter.py` 可以保留为本地开发或测试 harness，但不再是 OpenClaw 生产主路径。

## 9. 场景一验收标准

首期以“OpenClaw 原生宿主下的通用 Jira 定时查询提醒跑通”为验收目标，建议满足以下条件：

1. 用户可以通过 OpenClaw 对话创建一个 Jira 定时查询提醒任务，筛选条件不限于 P0 Bug。
2. 创建过程中，OpenClaw 会补齐缺失信息，生成 `query_spec`、`base_jql` 和确认摘要。
3. 用户确认后，OpenClaw 创建原生定时任务，并可通过 OpenClaw 原生能力查看、编辑或删除。
4. OpenClaw 创建出的任务配置中，保留 `filter_prompt`、`query_spec`、`base_jql`、`window_mode`、调度配置、时区、session 和目标群信息。
5. 定时执行时：
   - 无命中数据，不调用 LLM，不发送飞书消息。
   - 有命中数据，调用 LLM 生成受控摘要并发送 interactive 卡片。
6. 对同一条 Jira 按窗口模式和去重键不重复推送。
7. 执行期不重新解释用户原始意图，不修改 `base_jql` 或目标群。
8. `P0 Bug` 作为样例可以跑通，但不是唯一支持条件。

## 10. 剩余待确认项

外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

对场景一，仍需在实现期确认：

1. OpenClaw 宿主是否支持结构化 payload 注入；如果支持，是否优先替代长文本执行消息。
2. `snapshot` 模式是否默认只首次提醒，还是允许配置重复提醒频率。
3. 单次命中 Jira 数量很多时，是否需要做卡片发送上限、分批或折叠策略。
4. 批量摘要卡片与单 Jira 卡片是否首期都实现，还是首期只实现 `per_issue`。
5. 当飞书群已收到完整卡片时，OpenClaw announce 是否统一退化为简短执行摘要。
