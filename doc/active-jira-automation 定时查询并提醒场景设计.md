# active-jira-automation 场景一方案设计：新增 Jira 定时查询并提醒

## 1. 文档定位

本文档是 `active-jira-automation` 的场景子方案，描述“按用户自定义筛选条件定时查询 Jira，并在命中时发送飞书群提醒”的业务规则、接入方式和模板约束。

框架公共能力设计见主文档：[active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)。
外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

本文只描述场景一，不重复定义任务管理、调度适配、通用 runner、通用 interactive 卡片校验等框架公共内容。

## 2. 需求评估与设计修正

原方案把场景一理解成“新增 P0 BUG Jira 定时提醒”，这是一个过窄的特化场景。用户的真实目标是：

1. 用户可以用自然语言描述任意合理的 Jira 筛选目标。
2. Agent 在创建任务时引导用户补齐必要信息，并把意图转成明确、可审计的 JQL 或结构化查询规格。
3. 定时器只负责周期触发一个稳定、复用的查询脚本。
4. 查询脚本每次运行时接收任务配置中的 JQL 和运行窗口参数，周期性检查命中数据。
5. 有命中数据时，做轻量分析并把消息卡片发送到指定飞书群。

因此，场景一不应再把 `P0 + Bug` 写死在场景代码、任务模型、模板名称或验收标准中。`P0 Bug` 只能作为用户提示的一个示例，不能成为场景边界。

关键设计调整：

- 从“P0 专用场景”改为“通用 Jira 定时查询提醒场景”。
- 从“场景代码构造固定 P0 查询”改为“Agent 创建期编译查询规格，运行期稳定脚本参数化执行”。
- 从“P0 告警卡片模板”改为“通用 Jira 查询结果提醒卡片模板”。
- 从“只判断新增 P0 Bug”扩展为支持 `created`、`updated`、`snapshot` 三类窗口语义。
- 保留零命中零 Token、去重、检查点、dry-run、interactive 卡片投递等框架约束。

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

1. 通过交互式方式收集任务配置并完成创建。
2. 将用户自然语言筛选条件转成可确认、可存储、可执行的 JQL 或结构化查询规格。
3. 创建一个调度任务，周期性调用稳定复用的查询脚本。
4. 没有命中数据时不调用 LLM、不产生飞书外部副作用。
5. 有命中数据时，对结果做轻量分析与归纳，发送一张或多张固定结构的飞书 interactive 卡片。

## 4. 场景输入与交互引导

### 4.1 必要配置项

创建该任务时，Agent 需要收集或确认以下信息：

| 配置项 | 说明 | 是否可从提示词推断 |
| --- | --- | --- |
| `task_name` | 任务名称 | 可以 |
| `project` / `projects` | Jira 项目 Key，例如 `GENEVA` | 可以 |
| `filter_prompt` | 用户自然语言筛选意图 | 用户必须给出 |
| `query_spec` | 结构化查询规格，包含字段、操作符、值、排序等 | Agent 生成，用户确认 |
| `base_jql` | 不含运行窗口的基础 JQL | Agent 生成，用户确认 |
| `window_mode` | `created`、`updated` 或 `snapshot` | 需要确认或默认 |
| `schedule_type` | 周期查询或单次查询 | 需要确认 |
| `schedule_expr` | 每小时一次、每天 9 点或某个具体时间 | 需要确认 |
| `target_chat_name` | 目标群名称 | 可以从提示词推断 |
| `target_chat_id` | 飞书群稳定 ID，`oc_...` | 运行前必须确认 |
| `notify_policy` | 每条 Jira 单卡片、批量摘要卡片、数量上限 | 可默认 |

### 4.2 推荐追问顺序

1. 筛选目标：要查什么 Jira，哪些字段、状态、标签、版本、负责人、优先级或时间范围。
2. 查询项目：单项目或多项目；如果提示里已有项目 Key，可直接确认。
3. 窗口语义：只看新增、只看更新，还是每次检查当前仍命中的存量数据。
4. 调度方式：周期还是单次；周期表达式或具体执行时间。
5. 推送群组：群名或稳定 `chat_id`。
6. 通知策略：单条发送、批量汇总、最大提醒数量、是否重复提醒存量数据。

### 4.3 默认规则

当用户没有显式指定时，建议采用以下默认：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `window_mode` | `created` | 按“新增”语义查询，最符合提醒场景，避免每轮重复命中存量数据 |
| `lookback_minutes` | `5` | 查询窗口回看 5 分钟，靠去重避免重复发送 |
| `notify_policy.mode` | `per_issue` | 每条 Jira 单独一张卡片，便于群内跟进 |
| `notify_policy.max_issues_per_run` | `20` | 防止异常 JQL 一次刷屏 |
| `llm_policy` | `on-match-only` | 只有命中后才做轻量分析 |
| `sort` | `created ASC` 或 `updated ASC` | 与窗口字段一致 |

### 4.4 创建确认摘要

场景一在创建前应向用户展示固定摘要，至少包括：

- 任务名称
- 场景标识：`jira-scheduled-query-alert`
- Jira 项目范围
- 用户原始筛选意图
- Agent 生成的基础 JQL
- 窗口语义与查询窗口说明
- 调度方式
- 推送目标群
- 通知策略与单次上限
- LLM 策略：仅命中后调用
- 卡片模板版本：`lark-jira-query-alert-card-v1`

只有用户确认摘要后，才允许创建任务和调度器。

## 5. 查询规格与 JQL 生成

### 5.1 两阶段设计

场景一采用两阶段执行：

1. 创建期：Agent 根据用户提示生成 `query_spec` 和 `base_jql`，并让用户确认。
2. 运行期：稳定查询脚本读取任务配置，把 `base_jql` 与运行窗口组合成最终 JQL 后执行。

这里的“注入”指参数化注入 JQL 和窗口参数，不是为每个任务动态生成或修改脚本代码。

### 5.2 查询规格建议

任务定义中建议同时保存自然语言、结构化规格和最终 JQL：

```json
{
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
  "window_mode": "created"
}
```

保存 `query_spec` 的价值是便于审计、后续编辑和字段校验；保存 `base_jql` 的价值是让运行期脚本可以稳定执行。

### 5.3 JQL 生成约束

Agent 生成 JQL 时必须遵守：

- 不把 P0、Bug、项目 Key、状态等业务条件写死在场景代码中。
- 所有用户给出的字段和值必须进入确认摘要。
- 涉及自定义字段时，优先使用已知字段别名；无法确认时提示用户或通过 Jira 字段探测能力确认。
- 不把自然语言直接拼接到 shell 命令；JQL 作为任务 JSON 字段传入查询 runtime。
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

其中 `created_at/updated_at` 用于窗口模式去重；卡片所需的 Summary、负责人、Reporter、Severity、Priority、状态、影响版本、归属团队等详情，应在去重和单轮上限过滤之后，再通过 `active-jira`/本地 `jira issue view <KEY> --raw` 补全。这样零命中、重复命中和超出上限的 Jira 都不会触发详情拉取、LLM 调用或飞书发送。

## 6. 查询窗口、命中与去重规则

### 6.1 窗口模式

| 模式 | 适用场景 | 查询窗口 | 去重建议 |
| --- | --- | --- | --- |
| `created` | 新增 Jira 提醒 | `created >= last_checkpoint - overlap` 且 `created < now` | `task_id + issue_key + created` |
| `updated` | 最近更新 Jira 提醒 | `updated >= last_checkpoint - overlap` 且 `updated < now` | `task_id + issue_key + updated` |
| `snapshot` | 当前仍满足条件的存量巡检 | 不追加窗口 | `task_id + issue_key + base_jql_hash`，默认只首次提醒 |

### 6.2 检查点规则

- 首次运行起点由任务创建时间或显式 `start_at` 决定。
- 正常运行后，将 `last_checkpoint` 更新为本次 `window_end`。
- 查询失败时不推进检查点。
- 使用 `lookback_minutes` 回看窗口降低调度抖动导致的漏数风险。

### 6.3 无命中行为

当查询结果为空时，只执行以下动作：

1. 更新检查点。
2. 写入运行日志。
3. 正常退出。

不得执行：

- LLM 调用
- 卡片渲染
- 飞书发送

## 7. 场景接入主文档的实现映射

场景一应按主文档中的“场景接入契约”接入，建议映射如下：

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

## 8. 场景执行流程

本场景通过框架的通用 runner 执行，场景一只提供接入实现，不单独实现 runner。

建议的执行流程如下：

1. Agent 收集用户筛选意图、项目、窗口语义、调度、群组和通知策略。
2. Agent 生成 `query_spec` 与 `base_jql`，输出创建确认摘要。
3. 用户确认后，任务定义落盘，并通过调度适配层创建定时器。
4. 调度器按计划触发框架通用 runner。
5. runner 读取 `jira-scheduled-query-alert` 的场景接入实现。
6. 查询 runtime 将 `base_jql` 与运行窗口组合成最终 JQL。
7. 通用 Jira 运行时执行查询，只返回 Jira key 与窗口身份字段。
8. 场景根据 key、created/updated 或 base_jql_hash 生成去重键。
9. 通用去重逻辑过滤已发送记录，并按 `notify_policy.max_issues_per_run` 截断。
10. 如有新命中：
    - 调用 `active-jira` 能力按 Jira key 拉取详情。
    - 场景归一化逻辑整理卡片字段。
    - 调用 LLM 生成受控轻量分析。
    - 交给场景模板渲染器生成 `lark-jira-query-alert-card-v1`。
    - 由通用投递层发送 interactive 卡片。
11. 更新检查点、运行日志和投递结果。

重要约束：

- 查询脚本必须是纯确定性逻辑，不依赖 LLM。
- LLM 可以参与创建期 JQL 草拟，但必须经用户确认后落盘。
- 运行期不得让 LLM 修改 JQL、选择群组或决定是否发送。
- 卡片骨架必须由代码生成，不能让 LLM 直接输出整张卡片 JSON。
- LLM 只负责补充少量受控字段，例如“命中原因”“问题摘要”“风险评估”。

## 9. LLM 策略

### 9.1 创建期

创建期可以使用 Agent/LLM 辅助把用户自然语言转成 `query_spec` 和 `base_jql`。但必须满足：

- 展示给用户确认。
- 用户确认后才写入任务定义。
- 落盘后运行期只读配置，不再重新解释用户原始提示。

### 9.2 运行期

- 无命中：不调用 LLM。
- 有命中：按批次调用 1 次 LLM，为多条 Jira 返回结构化分析结果。

### 9.3 允许输出字段

每条 Jira 的 LLM 输出只允许包含：

- `match_reason`
- `problem_summary`
- `risk_assessment`

### 9.4 降级策略

- LLM 不可用时，仍然发送卡片。
- `match_reason` 回退为“命中任务筛选条件”。
- `problem_summary` 回退为 Jira Summary 或 Description 前 1 句。
- `risk_assessment` 回退为“待人工确认影响范围”。

## 10. 飞书 interactive 卡片模板设计

### 10.1 场景模板约束

本场景的飞书卡片必须：

- 使用飞书 IM `interactive` 消息类型。
- 由 `lark-jira-query-alert-card-v1` 模板生成。
- 输出为可直接投递的 interactive card JSON。
- 不允许退化为文本、Markdown 消息或字符画。

### 10.2 推荐的卡片骨架

```json
{
  "config": {
    "wide_screen_mode": true,
    "enable_forward": true
  },
  "header": {
    "template": "red",
    "title": {
      "tag": "plain_text",
      "content": "Jira 查询命中提醒"
    }
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**GENEVA-2034**\\n【FROM 质量平台-意见反馈】Biocharge ..."
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "fields": [
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**Jira 链接**\\n[GENEVA-2034](https://jira.example.com/browse/GENEVA-2034)"
          }
        },
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**创建时间**\\n2026-05-15 14:18"
          }
        },
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**归属团队**\\n质量平台"
          }
        }
      ]
    }
  ]
}
```

### 10.3 字段映射

| 展示区块 | interactive card 组件建议 |
| --- | --- |
| 告警标题 | `header.template` + `header.title`，模板颜色可按 `severity/priority` 或任务配置决定 |
| Jira Key 与 Summary | `div.text` |
| Jira 链接 / 创建时间 / 责任人 / Reporter / 优先级 / 状态 / 影响版本 / 归属团队 | `div.fields` |
| 问题摘要 / 风险评估 | 单独 `div.text` |
| 打开 Jira | 可选 `action.actions[].url` |

### 10.4 字段兜底

| 字段 | 来源 | 兜底规则 |
| --- | --- | --- |
| 标题 | 任务名或固定文案 | `Jira 查询命中提醒` |
| Jira Key | Jira | 无 |
| Summary | Jira | 截断到固定长度 |
| Jira URL | Jira 基础地址 + key | 无法拼接时退化为 key |
| 创建时间 | Jira | `未设置` |
| 责任人 | Jira | `Unassigned` |
| Reporter | Jira | `未设置` |
| 优先级/Severity | Jira | 优先 Severity，缺失时回退 Priority，再缺失为 `未设置` |
| 状态 | Jira | `未设置` |
| 影响版本 | Jira | `未设置` |
| 归属团队 | Jira | `未设置` |
| 问题摘要 | LLM 或规则摘要 | Jira Summary 或 Description 前 1 句 |
| 风险评估 | LLM 或规则摘要 | `待人工确认影响范围` |

## 11. 场景代码接入建议

本场景建议依附框架目录结构落地，不再新增独立的专用 runner。推荐接入点如下：

```text
active-jira-automation/
   scripts/
      run_automation_task.py
      scenarios/
         jira_scheduled_query_alert.py
      templates/
         lark_jira_query_alert_card_v1.py
      renderers/
         interactive_card_renderer.py
```

职责建议：

- `run_automation_task.py`：框架公共 runner。
- `scenarios/jira_scheduled_query_alert.py`：场景一的配置、JQL 组合、字段归一化、去重键和 LLM schema。
- `templates/lark_jira_query_alert_card_v1.py`：场景一的通用提醒卡片模板定义。
- `renderers/interactive_card_renderer.py`：框架公共 interactive 卡片渲染与校验能力。

## 12. 场景一验收标准

首期以“通用 Jira 定时查询提醒跑通”为验收目标，建议满足以下条件：

1. 用户可以通过自然语言创建一个 Jira 定时查询提醒任务，筛选条件不限于 P0 Bug。
2. 创建过程中，Agent 会补齐缺失信息，生成 `base_jql`，并输出确认摘要。
3. 用户确认后，任务创建并可在任务列表中看到。
4. 任务定义中保存 `filter_prompt`、`query_spec`、`base_jql`、`window_mode`、调度配置和目标群。
5. 调度器触发 runner 时：
   - 无命中数据，不调用 LLM，不发送飞书消息。
   - 有命中数据，调用 LLM 生成受控摘要并发送 interactive 卡片。
6. 对同一条 Jira 按窗口模式和去重键不重复推送。
7. 用户可以暂停、恢复、删除该任务。
8. `P0 Bug` 作为样例可以跑通，但不是唯一支持条件。

## 13. 剩余待确认项

外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

对场景一，仍需在实现期确认：

1. JQL 生成时，自定义字段别名到字段 ID 的解析是否复用 `active-jira` 现有能力，还是在自动化创建期增加字段探测步骤。
2. `snapshot` 模式是否默认只首次提醒，还是允许配置重复提醒频率。
3. 单次命中 Jira 数量很多时，是否需要做卡片发送上限、分批或折叠策略。
4. 批量摘要卡片与单 Jira 卡片是否首期都实现，还是首期只实现 `per_issue`。
