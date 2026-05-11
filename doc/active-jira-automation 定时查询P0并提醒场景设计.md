# active-jira-automation 场景一方案设计：新增 P0 BUG Jira 定时提醒

## 1. 文档定位

本文档是 `active-jira-automation` 的场景子方案，专门描述“新增 P0 BUG Jira 定时提醒”这一场景的业务规则、接入方式和模板约束。

框架公共能力设计见主文档：[active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)。
P0 设计冻结与外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

本文只描述场景一，不重复定义任务管理、调度适配、通用 runner、通用 interactive 卡片校验等框架公共内容。

## 2. 场景定位

### 2.1 场景名称

- 场景名称：新增 P0 BUG Jira 定时提醒
- `scenario_key`：`new-p0-bug-alert`
- 消息模板：`lark-p0-bug-card-v1`

### 2.2 用户意图示例

- 帮我创建一个 Geneva 项目新增 P0 BUG Jira 提醒任务。
- 每小时查询一次 GENEVA 新增的 P0 Bug，并推送到测试告警群。
- 帮我做一个单次提醒，今晚 8 点检查今天新增的 P0 Jira。

### 2.3 场景目标

该场景的目标是：

1. 通过交互式方式收集任务配置并完成创建。
2. 定时查询本周期内新增且命中的 P0 BUG Jira。
3. 没有命中数据时不调用 LLM、不产生飞书外部副作用。
4. 有命中数据时，为每条 Jira 发送一张固定结构的飞书 interactive 卡片。

## 3. 场景输入与交互引导

### 3.1 必要配置项

创建该任务时，Agent 需要收集或确认以下信息：

| 配置项 | 说明 | 是否可从提示词推断 |
| --- | --- | --- |
| `project` | Jira 项目，例如 `GENEVA` | 可以 |
| `query_rule` | 识别规则，例如 `P0 + Bug` | 可以部分推断 |
| `schedule_type` | 周期查询或单次查询 | 需要确认 |
| `schedule_expr` | 每小时一次、每天 9 点或某个具体时间 | 需要确认 |
| `target_chat_name` | 目标群名称 | 需要解析 |
| `target_chat_id` | 飞书群稳定 ID，`oc_...` | 运行前必须确认 |

### 3.2 推荐追问顺序

1. 项目。
2. 识别规则。
3. 周期还是单次。
4. 具体时间表达式。
5. 推送群组。

### 3.3 创建确认摘要

场景一在创建前应向用户展示固定摘要，至少包括：

- 任务名称
- 场景标识：`new-p0-bug-alert`
- Jira 项目
- 查询规则
- 查询窗口说明
- 调度方式
- 推送目标群
- LLM 策略：仅命中后调用
- 卡片模板版本：`lark-p0-bug-card-v1`

## 4. 场景接入主文档的实现映射

场景一应按主文档中的“场景接入契约”接入，建议映射如下：

| 接入项 | 场景一实现 |
| --- | --- |
| `scenario_key` | `new-p0-bug-alert` |
| `display_name` | 新增 P0 BUG Jira 定时提醒 |
| `config_schema` | `project`、`query_rule`、`schedule_type`、`schedule_expr`、`target_chat_id` |
| `defaulting_rules` | 默认将 `P0 + Bug` 识别为 `issue_type=Bug` + `severity=P0` 或 `priority=Highest` |
| `query_builder` | 构造“新增 + P0 + Bug”的结构化查询规则 |
| `result_normalizer` | 归一化 Jira Key、Summary、URL、创建时间、责任人、Team、Severity、Status、FixVersion、DueDate、Reporter、Source |
| `match_identity` | `task_id + issue_key + issue_created_at` |
| `llm_policy` | `on-match-only` |
| `llm_output_schema` | `symptom_summary`、`impact_summary` |
| `message_template_key` | `lark-p0-bug-card-v1` |
| `renderer` | 输出飞书 interactive card JSON |
| `delivery_policy` | 每个命中 Jira 单独发一张卡片，支持 dry-run 与幂等发送 |

## 5. 查询与命中规则

### 5.1 基础识别规则

“新增 P0 BUG Jira”不应只保留自然语言描述，而应落地为结构化查询条件。首期建议包括：

- `issue_type in (Bug)`
- `severity = P0` 或 `priority = Highest`
- 支持附加规则：标签、组件、来源字段、业务线字段

### 5.2 新增判定规则

本场景中的“新增”建议定义为：

- `created > last_checkpoint`
- `created <= current_run_time`

为避免调度抖动造成漏数，建议引入重叠回看窗口：

- 实际查询窗口：`created >= last_checkpoint - 5 minutes`
- 去重唯一键：`task_id + issue_key + issue_created_at`

### 5.3 无命中行为

当查询结果为空时，只执行以下动作：

1. 更新检查点。
2. 写入运行日志。
3. 正常退出。

不得执行：

- LLM 调用
- 卡片渲染
- 飞书发送

## 6. 场景执行流程

本场景通过框架的通用 runner 执行，场景一只提供接入实现，不单独实现 runner。

建议的执行流程如下：

1. Agent 收集配置并创建任务。
2. 调度器按计划触发框架通用 runner。
3. runner 读取 `new-p0-bug-alert` 的场景接入实现。
4. 由场景查询构造器生成本次查询规则。
5. 由通用 Jira 运行时执行查询。
6. 由场景归一化逻辑整理字段。
7. 由通用去重逻辑过滤已发送记录。
8. 如有命中：
    - 调用 LLM 生成受控摘要。
    - 交给场景模板渲染器生成 `lark-p0-bug-card-v1`。
    - 由通用投递层发送 interactive 卡片。
9. 更新检查点、运行日志和投递结果。

重要约束：

- 查询脚本必须是纯确定性逻辑，不依赖 LLM。
- 卡片骨架必须由代码生成，不能让 LLM 直接输出整张卡片 JSON。
- 发送链路必须满足飞书 IM interactive 卡片要求。
- LLM 只负责补充少量受控字段，例如“问题现象摘要”“影响评估摘要”。

## 7. LLM 策略

### 7.1 调用时机

- 无命中：不调用 LLM。
- 有命中：按批次调用 1 次 LLM，为多条 Jira 返回结构化摘要结果。

### 7.2 允许输出字段

每条 Jira 的 LLM 输出只允许包含：

- `symptom_summary`
- `impact_summary`

### 7.3 降级策略

- LLM 不可用时，仍然发送卡片。
- `symptom_summary` 回退为 Jira Summary 或 Description 前 1 句。
- `impact_summary` 回退为 `待人工确认影响范围`。

## 8. 飞书 interactive 卡片模板设计

### 8.1 场景模板约束

本场景的飞书卡片必须：

- 使用飞书 IM `interactive` 消息类型。
- 由 `lark-p0-bug-card-v1` 模板生成。
- 输出为可直接投递的 interactive card JSON。
- 不允许退化为文本、Markdown 消息或字符画。

### 8.2 推荐的卡片骨架

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
         "content": "新增 P0 严重 BUG 提醒"
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
                  "content": "**创建时间**\\n2026-05-11 14:18"
               }
            }
         ]
      }
   ]
}
```

### 8.3 字段映射

| 展示区块 | interactive card 组件建议 |
| --- | --- |
| 红色告警标题 | `header.template = red` + `header.title` |
| Jira Key 与 Summary | `div.text` |
| Jira 链接 / 创建时间 / 责任人 / Team / 优先级 / 状态 / 修复版本 / 截止日期 | `div.fields` |
| 智能分析摘要 | `div.text` 或单独两个 `div` |
| 报告人 / 来源 | `note.elements` |
| 打开 Jira | 可选 `action.actions[].url` |

### 8.4 字段兜底

| 字段 | 来源 | 兜底规则 |
| --- | --- | --- |
| 标题 | 固定文案 | `新增 P0 严重 BUG 提醒` |
| Jira Key | Jira | 无 |
| Summary | Jira | 截断到固定长度 |
| Jira URL | Jira 基础地址 + key | 无法拼接时退化为 key |
| 创建时间 | Jira | 本地时区格式化 |
| 责任人 | Jira | `Unassigned` |
| 归属 Team | Jira 自定义字段 | `未设置` |
| 优先级/Severity | Jira | 优先 Severity，缺失时回退 Priority |
| 状态 | Jira | 无 |
| 修复版本 | Jira | `未设置` |
| 截止日期 | Jira | `未设置` |
| 问题现象 | LLM 或规则摘要 | `待人工补充` |
| 影响评估 | LLM 或规则摘要 | `待人工确认影响范围` |
| 报告人 | Jira | `未设置` |
| 来源 | Jira 字段或规则映射 | `未设置` |

## 9. 场景代码接入建议

本场景建议依附框架目录结构落地，不再新增独立的专用 runner。推荐接入点如下：

```text
active-jira-automation/
   scripts/
      run_automation_task.py
      scenarios/
         new_p0_bug_alert.py
      templates/
         lark_p0_bug_card_v1.py
      renderers/
         interactive_card_renderer.py
```

职责建议：

- `run_automation_task.py`：框架公共 runner。
- `scenarios/new_p0_bug_alert.py`：场景一的配置、查询构造、字段归一化和 LLM schema。
- `templates/lark_p0_bug_card_v1.py`：场景一的模板定义。
- `renderers/interactive_card_renderer.py`：框架公共 interactive 卡片渲染与校验能力。

## 10. 场景一验收标准

首期以“场景一跑通”为验收目标，建议满足以下条件：

1. 用户可以通过自然语言创建一个“新增 P0 BUG Jira 提醒”任务。
2. 创建过程中，Agent 会补齐缺失信息并输出确认摘要。
3. 任务创建后可在任务列表中看到。
4. 调度器触发 runner 时：
    - 无命中数据，不调用 LLM，不发送飞书消息。
    - 有命中数据，调用 LLM 生成受控摘要并发送 interactive 卡片。
5. 对同一条 Jira 不重复推送。
6. 用户可以暂停、恢复、删除该任务。

## 11. P0 冻结决定与剩余待确认项

P0 已冻结决定见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

对场景一，P0 已明确以下实现前提：

1. 调度集成基于框架侧统一 `scheduler_adapter` 契约，而不是直接依赖某个 Openclaw SDK 细节。
2. 飞书发送路径首期固定为 raw API fallback，消息类型固定为 `interactive`。
3. 字段读取契约固定为：`Severity -> customfield_10401`、`Priority -> priority`、`Fix Version/s -> fixVersions`、`归属Team -> 配置字段/常见字段/customfield_11801`、`来源 -> 场景配置字段路径`。

本场景在正式实现前，仍保留以下实现期确认项：

1. 首期是否允许除了 `P0 + Bug` 之外再附加标签、组件等复合过滤条件。
2. 单次命中 Jira 数量很多时，是否需要做卡片发送上限、分批或折叠策略。