# active-jira-automation 框架能力设计

## 1. 文档定位

本文档是 `active-jira-automation` 的主文档，用于定义框架层的目标、边界、公共能力、宿主契约、接入契约与首期落地范围。

默认前提：

- 优先采用 OpenClaw 作为宿主运行模型。
- 自建框架或其他平台不作为当前主路径，但应兼容同一宿主契约，避免后期扩展时重新拆边界。

文档分工如下：

- 本文档负责框架公共能力设计与宿主边界定义。
- 场景子文档只负责描述单个场景的业务规则、参数、模板和接入映射。
- 当前首个场景子文档见：[active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md)。
- P0 设计冻结与外部契约确认见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。
- OpenClaw 可直接使用的模板见：[openclaw-native-message-templates](../active-jira-automation/references/openclaw-native-message-templates.md)。

后续新增场景时，均应以“子能力 / 子方案”的形式接入本框架，而不是在各自文档中重复定义宿主契约、检查点、去重、投递、审计等公共能力。

## 2. 目标与非目标

### 2.1 建设目标

`active-jira-automation` 的目标不是实现单一提醒脚本，也不是把本仓库做成一个自带调度中心的产品，而是沉淀一套以 OpenClaw 为默认宿主的 Jira 自动化能力包，统一承接以下能力：

1. 在宿主对话中引导用户创建 Jira 自动化任务。
2. 将自然语言筛选意图转成可审计的 `query_spec` 与 `base_jql`。
3. 把“查询、命中判断、LLM 摘要、飞书投递”拆成可复用的执行管线。
4. 让后续场景只接入业务规则和模板，不重复实现通用运行基础设施。
5. 保证所有外部副作用可预览、可审计、可幂等。
6. 对其他宿主平台保留兼容占位，只要求其映射到同一宿主契约。

### 2.2 非目标

以下能力不应由 `active-jira-automation` 直接承担：

- 把本地 task store 或 scheduler adapter 作为生产主路径。
- 通用 Jira 字段探测与底层 JQL 教学。
- 没有明确用户意图时对 Jira 本身做写操作。
- 让 LLM 决定任务接收方、关键过滤条件或消息结构。
- 为首期场景引入过重的 DSL、插件平台或复杂动态组件体系。
- 为每个宿主平台各自复制一套 runner、模板或发送链路。

## 3. 设计原则

框架层建议遵循以下原则：

1. OpenClaw 优先：主设计首先服务 OpenClaw 宿主模型，再向其他平台暴露兼容契约。
2. 宿主与业务解耦：宿主管任务，skill 管业务语义、运行契约和共享脚本。
3. 场景优先：场景差异通过接入契约表达，框架不硬编码业务规则。
4. 确定性优先：查询、去重、渲染、发送必须以确定性代码实现；LLM 只处理受控摘要字段。
5. 零命中零 Token：没有命中数据时，不调用 LLM、不生成卡片、不做飞书写操作。
6. 强审计：确认摘要、运行检查点、消息幂等、发送结果都要可追溯。
7. 副作用后置：先校验目标、配置与 payload，再做外部发送。

## 4. 职责边界

### 4.1 Skill 边界

三个 Skill 的边界建议固定如下：

| Skill | 职责 |
| --- | --- |
| `active-jira` | 通用 Jira 查询、字段读取、JQL 执行、详情补充 |
| `active-lark` | 通用飞书群组搜索、消息发送、权限、raw API 调用 |
| `active-jira-automation` | OpenClaw-facing 创建流程、场景接入、执行编排、interactive 卡片模板约束、共享运行时脚本 |

边界约束：

- `active-jira-automation` 不重复封装一套通用 Jira CLI 使用说明。
- `active-jira-automation` 不承接飞书基础认证、Profile 管理或通用通讯录能力。
- `active-jira-automation` 只沉淀“自动化场景公共运行时”与“宿主消费契约”相关内容。

### 4.2 宿主边界

默认 OpenClaw 宿主应承担以下职责：

| 能力 | 默认归属 |
| --- | --- |
| cron 或一次性任务创建 | OpenClaw |
| 时区管理 | OpenClaw |
| session 生命周期 | OpenClaw |
| 任务列表、状态、执行历史 | OpenClaw |
| announce 与频道回传 | OpenClaw |
| 创建期交互流程 | `active-jira-automation` 协助 OpenClaw |
| JQL 设计与确认摘要 | `active-jira-automation` |
| 共享 runner、查询、去重、卡片渲染、飞书发送 | `active-jira-automation` |

其他平台如要兼容，只需要能映射同一组宿主语义：`name`、`cron/at`、`tz`、`session`、`message`、`announce`、执行历史。

## 5. 框架能力分层

建议将 `active-jira-automation` 拆为六层公共能力。

### 5.1 宿主集成契约层

负责定义宿主如何消费本 skill 的输出，而不是在 skill 内部重新实现一个通用调度产品。

默认 OpenClaw 需要消费：

- 创建期确认摘要
- 定时执行消息模板
- `name`
- `cron` 或 `at`
- `tz`
- `session`
- `announce` 与可选 `channel`

兼容策略：

- OpenClaw 是默认主路径。
- 自建框架或其他平台必须映射到同一宿主契约，不允许为每个平台发散出一套独立业务逻辑。
- `scripts/manage_tasks.py`、`scripts/task_store.py`、`scripts/scheduler_adapter.py` 可以保留为本地开发或测试 harness，但不是产品主路径。

### 5.2 创建工作流层

负责：

- 识别目标场景
- 只追问缺失配置
- 将自然语言输入归一化为结构化字段
- 将群名解析为稳定 `chat_id`
- 生成固定确认摘要
- 生成宿主可消费的执行消息

这一层是 OpenClaw 对话式创建流程与共享运行时之间的接缝。

### 5.3 场景接入层

负责：

- 注册 `scenario_key`
- 声明该场景的配置字段与默认值
- 提供查询规则构造器
- 提供结果归一化规则
- 提供 LLM 输出 schema
- 绑定消息模板版本

这一层是“框架”和“场景子方案”之间的接缝。

### 5.4 通用执行引擎

负责统一执行壳：

1. 读取确认后的任务配置或宿主注入载荷。
2. 计算本次查询窗口。
3. 调用 Jira 查询，获取命中 key 与窗口身份字段。
4. 归一化最小命中结果。
5. 去重并应用通知上限。
6. 命中后按 key 补全 Jira 详情。
7. 按策略调用 LLM。
8. 渲染消息 payload。
9. 校验并发送。
10. 写回检查点与运行日志。

执行引擎必须对所有场景共用，不能每个场景各自维护一套 runner。

### 5.5 投递与模板层

负责：

- 飞书 interactive 卡片渲染
- interactive payload 校验
- 发送 `--dry-run`
- 幂等键生成
- 发送结果记录

框架层只定义通用投递约束；具体卡片字段布局由场景模板提供。

### 5.6 审计与可观测层

负责记录：

- 最近一次运行时间
- 最近一次运行结果
- 最近一次命中数
- 最近一次发送数
- 最近一次错误
- 当前检查点
- 最近一次发送的幂等信息

OpenClaw 默认负责调度与执行历史的宿主侧记录；框架保留业务运行态日志与检查点即可。

## 6. 通用任务规格与宿主元数据

为避免主文档和子文档边界不一致，建议把任务模型拆成两部分：业务确认规格与宿主元数据。

### 6.1 业务确认规格

所有自动化任务统一使用一份“确认后的业务规格”。建议最小字段如下：

| 字段 | 含义 | 是否必填 |
| --- | --- | --- |
| `task_name` | 用户可读名称 | 是 |
| `scenario_key` | 场景标识，例如 `jira-scheduled-query-alert` | 是 |
| `project` / `projects` | Jira 项目范围 | 是 |
| `filter_prompt` | 用户原始自然语言筛选意图 | 是 |
| `query_spec` | 可审计的结构化查询规格 | 是 |
| `base_jql` | 不含运行窗口的基础 JQL | 是 |
| `window_mode` | `created`、`updated` 或 `snapshot` | 是 |
| `lookback_minutes` | 调度抖动回看窗口分钟数 | 是 |
| `notify_policy` | 通知模式、单轮上限、存量重复提醒策略 | 是 |
| `target_chat_id` | 飞书群稳定 ID | 是 |
| `target_chat_name` | 用户输入的原始群名 | 否 |
| `message_template_key` | 模板版本标识 | 是 |
| `llm_policy` | LLM 调用策略 | 是 |

### 6.2 宿主元数据

以下字段由宿主优先负责，但应允许在确认摘要中被审计：

| 字段 | 含义 | 默认建议 |
| --- | --- | --- |
| `schedule_type` | `recurring` 或 `once` | 必填 |
| `schedule_expr` | cron、相对时间或绝对执行时间 | 必填 |
| `timezone` | IANA 时区 | `Asia/Shanghai` |
| `host_session` | 宿主执行 session | `isolated` |
| `announce_policy` | announce 是否开启及其粒度 | compact |
| `host_job_id` | 宿主任务 ID | 宿主生成 |
| `host_platform` | 默认 `openclaw` | `openclaw` |
| `created_by` | 创建任务的用户标识 | 可选 |
| `created_at` | 创建时间 | 宿主生成 |
| `updated_at` | 更新时间 | 宿主生成 |

### 6.3 运行态数据

运行态建议单独存储：

- `last_checkpoint`
- `last_run_at`
- `last_run_status`
- `last_match_count`
- `last_delivery_count`
- `last_error`
- `idempotency_window`

### 6.4 持久化建议

默认 OpenClaw 产品路径：

- 宿主保存定时任务、时区、session、状态与执行历史。
- 宿主通过确认摘要或结构化载荷保存业务确认规格。

本地开发或测试 harness 仍可使用：

- 任务定义：`active-jira-automation/data/tasks/<task_id>.json`
- 运行检查点：`active-jira-automation/data/runtime/<task_id>.json`
- 运行日志：`active-jira-automation/data/logs/<task_id>/<timestamp>.json`

## 7. 生命周期与宿主操作契约

### 7.1 事实来源

默认规则：

- OpenClaw 是任务 CRUD、启停、执行历史和调度状态的事实来源。
- `active-jira-automation` 是业务规格、执行消息和共享运行时的事实来源。

### 7.2 创建任务

创建流程必须包含：

1. 识别目标场景。
2. 只追问缺失配置。
3. 将自然语言输入归一化为结构化字段。
4. 将群名解析为稳定 `chat_id`。
5. 展示确认摘要。
6. 用户确认后，由 OpenClaw 创建计划任务。
7. 宿主写入 `name`、`cron/at`、`tz`、`session`、`message` 等字段。

### 7.3 列出、查看、编辑、暂停、恢复、删除

公共规则：

- 列表、状态、最近执行等信息优先由宿主提供。
- skill 主要负责解释和再生成业务规格，不取代宿主的任务中心。
- 编辑任务时，应重新生成确认摘要并再次确认。
- `delete` 必须先给出任务摘要并要求确认。

### 7.4 兼容占位原则

如果后续接入自建框架或其他平台，应满足：

- 能表达 `cron/at`、时区、session 和执行消息。
- 能提供基本的 list、show、edit、remove 或等价操作。
- 若不支持 pause 或 resume，可映射为 enable 或 disable 等价语义。

## 8. 通用执行管线

所有场景都应复用下面这条执行链路：

1. 宿主到期时注入确认后的任务配置或执行消息。
2. 读取任务定义与场景注册信息。
3. 计算查询窗口。
4. 执行 Jira 查询，只获取命中 key 与去重所需窗口字段。
5. 对命中结果做最小归一化。
6. 根据唯一键去重，并应用单轮通知上限。
7. 如果无命中：
   - 更新检查点
   - 写运行日志
   - 结束
8. 如果有命中：
   - 按 Jira key 调用 `active-jira` 或本地 JiraCLI 拉取详情
   - 对详情做场景字段归一化
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
- 运行期不得重新解释用户原始意图、改写 `base_jql` 或重选目标群。

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
- 宿主相关建议如默认时区、session 或 announce 策略，优先写在场景文档中，不扩展成必填场景字段。

## 11. 建议的目录结构

建议 `active-jira-automation` Skill 采用如下结构：

```text
active-jira-automation/
  SKILL.md
  agents/
    openai.yaml
  references/
    automation-framework.md
    openclaw-native-message-templates.md
    task-lifecycle.md
    scenario-access-contract.md
  scripts/
    run_automation_task.py
    scenario_registry.py
    jira_query_runtime.py
    llm_summary_runtime.py
    lark_delivery_runtime.py
    renderers/
      interactive_card_renderer.py
    templates/
      lark_jira_query_alert_card_v1.py
    scenarios/
      jira_scheduled_query_alert.py
    harness/
      manage_tasks.py
      task_store.py
      scheduler_adapter.py
  tests/
    test_run_automation_task.py
    test_interactive_card_renderer.py
    test_jira_scheduled_query_alert.py
    test_manage_tasks.py
```

含义说明：

- `scripts/scenarios/`：每个子场景的接入实现。
- `scripts/templates/`：场景卡片模板定义。
- `scripts/renderers/`：通用 interactive 卡片渲染与校验能力。
- `scripts/*_runtime.py`：通用运行时，不承载业务场景差异。
- `scripts/harness/`：本地开发与测试占位。当前仓库中的相关脚本虽仍在顶层，但设计上应视为 harness 能力，而不是主产品路径。

## 12. 当前场景接入清单

首期建议先接入一个场景，用它验证 OpenClaw 宿主模型下的框架壳是否足够稳定。

| 场景 | `scenario_key` | 状态 | 子文档 |
| --- | --- | --- | --- |
| Jira 定时查询并提醒 | `jira-scheduled-query-alert` | 规划中 | [active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md) |

建议后续可扩展的同类场景包括：

- 新增 Blocker 或高优先级 Jira 提醒
- 长期未处理 Jira 自动巡检与定时汇报
- 指定 Team 的回归缺陷提醒
- 发布版本 blocker Jira 自动播报

## 13. 首期落地范围

首期框架落地建议只覆盖以下最小能力：

1. 单场景接入能力。
2. OpenClaw 创建期确认摘要与定时执行消息契约。
3. 统一 runner 与检查点机制。
4. 命中后单批次 LLM 摘要。
5. 飞书 interactive 卡片渲染、校验与发送 dry-run。
6. 本地 harness 仅用于开发和测试，不要求作为生产主路径对外暴露。

暂不建议首期引入：

- 多宿主平台并行做正式产品化适配
- 复杂模板编排 DSL
- 多场景依赖编排
- 高级交互式卡片组件

## 14. P0 冻结决定与剩余待确认项

P0 已冻结决定见：[active-jira-automation P0 设计冻结与外部契约确认](./active-jira-automation%20P0设计冻结与外部契约确认.md)。

在该确认记录基础上，框架侧已固定以下事项：

1. 默认采用 OpenClaw 宿主模型。
2. 宿主消费的确认摘要与执行消息契约已固定。
3. 飞书 interactive 卡片首期发送路径固定为 `active-lark` raw API fallback。
4. 关键字段读取契约固定为：`Severity -> customfield_10401`、`Priority -> priority`、`Fix Version/s -> fixVersions`、`归属Team -> 配置字段/常见字段/customfield_11801`、`来源 -> 场景配置字段路径`。

P0 之后仍保留为实现期确认项的事项：

1. 首期是否需要支持多项目、多规则复合匹配。
2. OpenClaw 是否支持结构化 payload 注入，以替代长文本执行消息。
3. 单次命中数量很大时的限流、分批和消息折叠策略。
4. 自建框架或其他平台接入时，最小宿主能力是否需要再收敛成正式兼容接口。

## 15. 结论

`active-jira-automation` 需要独立的框架能力设计，而且应作为主文档存在。但该框架的默认产品形态应是“OpenClaw 宿主 + skill 业务契约 + 共享运行时”，而不是“skill 自带调度中心”。

这样做的收益是：

- 不重复实现宿主级任务生命周期与执行历史
- 不重复实现 interactive 卡片投递与校验
- 不重复实现检查点、去重、日志和审计
- 后续新增场景时只需要增加场景接入实现和子文档
- 后续接入其他平台时，只需要映射同一宿主契约，不必重拆业务边界

首个场景的详细设计见：[active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md)。
