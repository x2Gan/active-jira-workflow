# active-jira-automation 框架能力设计

## 1. 文档定位

本文档是 `active-jira-automation` 的主文档，用于定义框架层的目标、边界、公共能力、接入契约与首期落地范围。

文档分工如下：

- 本文档负责框架公共能力设计。
- 场景子文档只负责描述单个场景的业务规则、参数、模板和接入映射。
- 当前首个场景子文档见：[active-jira-automation 定时查询P0并提醒场景设计](./active-jira-automation%20定时查询P0并提醒场景设计.md)。
- P0 设计冻结与外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

后续新增场景时，均应以“子能力 / 子方案”的形式接入本框架，而不是在各自文档中重复定义调度、检查点、去重、投递、审计等公共能力。

## 2. 目标与非目标

### 2.1 建设目标

`active-jira-automation` 的目标不是实现单一提醒脚本，而是沉淀一套可复用的 Jira 自动化任务框架，统一承接以下类型的能力：

1. 创建、列出、暂停、恢复、删除自动化任务。
2. 基于统一任务模型管理多种 Jira 自动化场景。
3. 将“查询、命中判断、LLM 摘要、飞书投递”拆成可复用的执行管线。
4. 让后续场景只接入业务规则和模板，不重复实现通用基础设施。
5. 保证所有外部副作用可预览、可审计、可幂等。

### 2.2 非目标

以下能力不应由 `active-jira-automation` 直接承担：

- 通用 Jira 字段探测与底层 JQL 教学。
- 没有明确用户意图时对 Jira 本身做写操作。
- 让 LLM 决定任务接收方、关键过滤条件或消息结构。
- 为首期场景引入过重的 DSL、插件平台或复杂动态组件体系。

## 3. 设计原则

框架层建议遵循以下原则：

1. 轻框架优先：先抽出公共执行壳，不做过度通用化设计。
2. 场景优先：场景差异通过接入契约表达，框架不硬编码业务规则。
3. 确定性优先：查询、去重、渲染、发送必须以确定性代码实现；LLM 只处理受控摘要字段。
4. 零命中零 Token：没有命中数据时，不调用 LLM、不生成卡片、不做飞书写操作。
5. 强审计：任务定义、运行检查点、消息幂等、发送结果都要可追溯。
6. 副作用后置：先校验目标、配置与 payload，再做外部发送。

## 4. 职责边界

三个 Skill 的边界建议固定如下：

| Skill | 职责 |
| --- | --- |
| `active-jira` | 通用 Jira 查询、字段读取、JQL 执行、详情补充 |
| `active-lark` | 通用飞书群组搜索、消息发送、权限、raw API 调用 |
| `active-jira-automation` | 自动化任务模型、调度适配、场景接入、执行编排、interactive 卡片模板约束 |

边界约束：

- `active-jira-automation` 不重复封装一套通用 Jira CLI 使用说明。
- `active-jira-automation` 不承接飞书基础认证、Profile 管理或通用通讯录能力。
- `active-jira-automation` 只沉淀“自动化任务框架”相关的公共运行时。

## 5. 框架能力分层

建议将 `active-jira-automation` 拆为六层公共能力。

### 5.1 任务管理层

负责：

- 创建任务
- 列出任务
- 暂停任务
- 恢复任务
- 删除任务
- 维护任务状态机

这一层只关心任务定义与生命周期，不关心具体场景的查询逻辑。

### 5.2 场景接入层

负责：

- 注册 `scenario_key`
- 声明该场景的配置字段与默认值
- 提供查询规则构造器
- 提供结果归一化规则
- 提供 LLM 输出 schema
- 绑定消息模板版本

这一层是“框架”和“场景子方案”之间的接缝。

### 5.3 通用执行引擎

负责统一执行壳：

1. 读取任务定义
2. 计算本次查询窗口
3. 调用 Jira 查询
4. 归一化命中结果
5. 去重
6. 命中后按策略调用 LLM
7. 渲染消息 payload
8. 校验并发送
9. 写回检查点与运行日志

执行引擎必须对所有场景共用，不能每个场景各自维护一套 runner。

### 5.4 投递与模板层

负责：

- 飞书 interactive 卡片渲染
- interactive payload 校验
- 发送 `--dry-run`
- 幂等键生成
- 发送结果记录

框架层只定义通用投递约束；具体卡片字段布局由场景模板提供。

### 5.5 调度适配层

负责与 Openclaw 或其他调度器对接，向上暴露统一接口：

- 创建调度任务
- 暂停调度任务
- 恢复调度任务
- 删除调度任务
- 查询调度任务 ID 和状态

这里应设计成“适配层”，而不是把框架绑死在 Openclaw 单一实现上。

### 5.6 审计与可观测层

负责记录：

- 最近一次运行时间
- 最近一次运行结果
- 最近一次命中数
- 最近一次发送数
- 最近一次错误
- 当前检查点
- 最近一次发送的幂等信息

## 6. 通用任务模型

所有自动化任务统一使用一个任务定义对象。建议最小字段如下：

| 字段 | 含义 | 是否必填 |
| --- | --- | --- |
| `task_id` | 任务唯一 ID，创建后稳定不变 | 是 |
| `task_name` | 用户可读名称 | 是 |
| `scenario_key` | 场景标识，例如 `new-p0-bug-alert` | 是 |
| `project` | Jira 项目 Key | 是 |
| `query_rule` | 结构化查询规则 | 是 |
| `schedule_type` | `recurring` 或 `once` | 是 |
| `schedule_expr` | cron、间隔表达式或单次执行时间 | 是 |
| `target_chat_id` | 飞书群稳定 ID | 是 |
| `target_chat_name` | 用户输入的原始群名 | 否 |
| `message_template_key` | 模板版本标识 | 是 |
| `llm_policy` | LLM 调用策略 | 是 |
| `status` | `enabled`、`paused`、`deleted` | 是 |
| `last_checkpoint` | 上次成功查询截止时间 | 否 |
| `created_by` | 创建任务的用户标识 | 否 |
| `created_at` | 创建时间 | 是 |
| `updated_at` | 更新时间 | 是 |

运行态建议单独存储：

- `last_run_at`
- `last_run_status`
- `last_match_count`
- `last_delivery_count`
- `last_error`
- `idempotency_window`

建议的持久化布局：

- 任务定义：`active-jira-automation/data/tasks/<task_id>.json`
- 运行检查点：`active-jira-automation/data/runtime/<task_id>.json`
- 运行日志：`active-jira-automation/data/logs/<task_id>/<timestamp>.json`

## 7. 生命周期与公共操作契约

### 7.1 状态机

建议的任务状态机：

- `enabled`：正常可调度
- `paused`：保留配置但不调度执行
- `deleted`：逻辑删除，不再展示为活跃任务

建议状态转换规则：

- `create -> enabled`
- `enabled -> paused`
- `paused -> enabled`
- `enabled|paused -> deleted`

### 7.2 创建任务

创建流程必须包含：

1. 识别目标场景。
2. 只追问缺失配置。
3. 将自然语言输入归一化为结构化字段。
4. 将群名解析为稳定 `chat_id`。
5. 展示确认摘要。
6. 用户确认后写入任务定义，并调用调度适配层创建计划任务。

### 7.3 列出任务

至少返回以下字段：

| 任务 ID | 名称 | 场景 | 状态 | 项目 | 调度 | 目标群 | 最近运行 | 最近命中 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 7.4 暂停、恢复、删除

公共规则：

- 优先基于 `task_id` 执行。
- 仅在任务名称唯一匹配时才允许用名称直接操作。
- `delete` 必须先给出任务摘要并要求确认。
- 默认只删除任务定义，不主动删除历史运行日志。

## 8. 通用执行管线

所有场景都应复用下面这条执行链路：

1. 读取任务定义与场景注册信息。
2. 计算查询窗口。
3. 执行 Jira 查询。
4. 对结果做归一化。
5. 根据唯一键去重。
6. 如果无命中：
   - 更新检查点
   - 写运行日志
   - 结束
7. 如果有命中：
   - 根据场景策略调用 LLM
   - 渲染 interactive 卡片 payload
   - 做 schema 校验
   - 执行发送
   - 写回运行结果和检查点

关键约束：

- 无命中时不调用 LLM。
- LLM 输出必须是 schema 可校验的结构化 JSON。
- 去重发生在发送之前。
- 卡片渲染和发送必须分离。

## 9. Interactive 卡片公共契约

`active-jira-automation` 的飞书消息卡片统一遵循以下公共约束：

1. 消息类型固定为飞书 IM `interactive`。
2. `content` 必须是 interactive card JSON 的字符串化结果。
3. payload 至少包含 `config`、`header`、`elements` 三部分。
4. 发送前必须执行本地结构校验。
5. 所有动态字段必须做空值处理、长度裁剪和特殊字符转义。
6. 支持 `--dry-run` 输出最终 interactive card JSON。
7. 默认使用 `active-lark` 的 raw API fallback 发送，后续可平滑切到通用发送脚本。

注意：框架层只约束 interactive 卡片协议与校验方式，不定义每个场景的具体字段布局。具体模板由场景子方案提供。

## 10. 场景接入契约

后续场景都应以“子能力 / 子方案”的形式接入主框架。每个场景至少需要声明以下内容：

| 接入项 | 说明 | 是否必填 |
| --- | --- | --- |
| `scenario_key` | 全局唯一场景标识 | 是 |
| `display_name` | 场景展示名 | 是 |
| `trigger_examples` | 典型触发语句 | 是 |
| `config_schema` | 需要收集的任务配置字段 | 是 |
| `defaulting_rules` | 可推断默认值规则 | 是 |
| `query_builder` | 结构化查询规则构造器 | 是 |
| `result_normalizer` | Jira 返回字段归一化逻辑 | 是 |
| `match_identity` | 去重唯一键定义 | 是 |
| `llm_policy` | 何时调用 LLM | 是 |
| `llm_output_schema` | LLM 允许输出的字段 | 是 |
| `message_template_key` | 模板版本标识 | 是 |
| `renderer` | interactive 卡片渲染器 | 是 |
| `delivery_policy` | 发送目标、频率、幂等等约束 | 是 |
| `acceptance_cases` | 场景验收样例 | 是 |

接入原则：

- 场景不能自带独立 runner，必须复用框架通用 runner。
- 场景不能绕过框架直接调用飞书发送。
- 场景的差异只体现在配置、查询规则、字段映射、模板和摘要策略上。

## 11. 建议的目录结构

建议 `active-jira-automation` Skill 采用如下结构：

```text
active-jira-automation/
  SKILL.md
  agents/
    openai.yaml
  references/
    automation-framework.md
    task-lifecycle.md
    scenario-access-contract.md
  scripts/
    manage_tasks.py
    run_automation_task.py
    scenario_registry.py
    scheduler_adapter.py
    jira_query_runtime.py
    llm_summary_runtime.py
    lark_delivery_runtime.py
    renderers/
      interactive_card_renderer.py
    templates/
      lark_p0_bug_card_v1.py
    scenarios/
      new_p0_bug_alert.py
  tests/
    test_manage_tasks.py
    test_run_automation_task.py
    test_interactive_card_renderer.py
    test_new_p0_bug_alert.py
```

含义说明：

- `scripts/scenarios/`：每个子场景的接入实现。
- `scripts/templates/`：场景卡片模板定义。
- `scripts/renderers/`：通用 interactive 卡片渲染与校验能力。
- `scripts/*_runtime.py`：通用运行时，不承载业务场景差异。

## 12. 当前场景接入清单

首期建议先接入一个场景，用它验证框架壳是否足够稳定。

| 场景 | `scenario_key` | 状态 | 子文档 |
| --- | --- | --- | --- |
| 新增 P0 BUG Jira 定时提醒 | `new-p0-bug-alert` | 规划中 | [active-jira-automation 定时查询P0并提醒场景设计](./active-jira-automation%20定时查询P0并提醒场景设计.md) |

建议后续可扩展的同类场景包括：

- 新增 Blocker/高优先级 Jira 提醒
- 长期未处理 Jira 自动巡检与定时汇报
- 指定 Team 的回归缺陷提醒
- 发布版本 blocker Jira 自动播报

## 13. 首期落地范围

首期框架落地建议只覆盖以下最小能力：

1. 单场景接入能力。
2. 单任务创建、列出、暂停、恢复、删除。
3. 统一 runner 与检查点机制。
4. 命中后单批次 LLM 摘要。
5. 飞书 interactive 卡片渲染、校验与发送 dry-run。

暂不建议首期引入：

- 多调度器并行适配
- 复杂模板编排 DSL
- 多场景依赖编排
- 高级交互式卡片组件

## 14. P0 冻结决定与剩余待确认项

P0 已冻结决定见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

在该确认记录基础上，框架侧已固定以下事项：

1. 调度层采用框架侧统一 `scheduler_adapter` 契约，对上暴露 `create/pause/resume/delete/get_status`。
2. 飞书 interactive 卡片首期发送路径固定为 `active-lark` raw API fallback。
3. 关键字段读取契约固定为：`Severity -> customfield_10401`、`Priority -> priority`、`Fix Version/s -> fixVersions`、`归属Team -> 配置字段/常见字段/customfield_11801`、`来源 -> 场景配置字段路径`。

P0 之后仍保留为实现期确认项的事项：

1. 首期是否需要支持多项目、多规则复合匹配。
2. 单次命中数量很大时的限流、分批和消息折叠策略。

## 15. 结论

`active-jira-automation` 需要独立的框架能力设计，而且应作为主文档存在。后续所有 Jira 自动化任务场景，都应以子能力和子方案的形式接入本框架。

这样做的收益是：

- 不重复实现任务生命周期与执行壳
- 不重复实现 interactive 卡片投递与校验
- 不重复实现检查点、去重、日志和审计
- 后续新增场景时只需要增加场景接入实现和子文档

首个场景的详细设计见：[active-jira-automation 定时查询P0并提醒场景设计](./active-jira-automation%20定时查询P0并提醒场景设计.md)。