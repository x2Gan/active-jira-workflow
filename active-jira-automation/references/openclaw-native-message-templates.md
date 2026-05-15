# OpenClaw 原生创建与执行消息模板

## 1. 文档用途

本文档提供两份可以直接给 OpenClaw 使用的模板：

1. 创建期确认摘要模板：用于 OpenClaw 在真正创建定时任务前给用户做最终确认。
2. 定时执行消息模板：用于 OpenClaw 到期时向模型注入稳定、不可歧义的执行契约。

这些模板面向 `active-jira-automation` 的 `jira-scheduled-query-alert` 场景。默认假设：

- OpenClaw 负责任务创建、时区、session、announce、执行历史和任务管理。
- skill 负责交互流程、JQL 设计规则、共享脚本和消息结构约束。
- 默认推荐 OpenClaw `session isolated`。

## 2. 填充规则

### 2.1 业务确认前置字段

使用模板前，OpenClaw 需要先拿到已确认的配置：

- `task_name`
- `scenario_key=jira-scheduled-query-alert`
- `project` 或 `projects`
- `filter_prompt`
- `query_spec`
- `base_jql`
- `window_mode`
- `lookback_minutes`
- `schedule_type`
- `schedule_expr`
- `timezone`
- `target_chat_name`
- `target_chat_id`
- `notify_policy`
- `message_template_key=lark-jira-query-alert-card-v1`

如果宿主支持结构化 payload 注入，优先用结构化字段；以下文本模板主要用于需要通过 message 字段注入长文本的场景。

### 2.2 OpenClaw 宿主输入 schema / checklist 表

下表是给 OpenClaw 创建任务实现直接使用的最小输入清单。建议实现顺序就是表格顺序：先收集和确认业务规格，再映射到宿主字段。

| Checklist 项 | OpenClaw 字段 | 来源字段 | 是否必填 | 默认值 | 何时填充 | 创建前校验 |
| --- | --- | --- | --- | --- | --- | --- |
| 任务名称 | `name` | `task_name` | 是 | 从项目名 + 核心筛选意图 + 调度语义生成候选名 | 用户确认业务摘要后填写 | 非空，且用户能识别 |
| 周期调度 | `cron` | `schedule_expr` | 条件必填 | 无 | `schedule_type=recurring` 时填写 | cron 合法，且 `at` 为空 |
| 一次性调度 | `at` | `schedule_expr` | 条件必填 | 无 | `schedule_type=once` 时填写 | 时间格式合法，且 `cron` 为空 |
| 时区 | `tz` | `timezone` | 强烈建议必填 | `Asia/Shanghai` | 确认调度语义后填写 | 合法 IANA 时区 |
| 执行会话 | `session` | `openclaw_session` | 是 | `isolated` | 默认在调度字段之后填写 | 必须是宿主支持的 session 语法 |
| 执行消息 | `message` | `rendered_execution_message` | 是 | 无 | 业务规格全部确认后渲染 | 不允许遗漏 `base_jql`、`target_chat_id`、`notify_policy` |
| 宿主播报开关 | `announce` | `announce_policy.enabled` | 建议填写 | `true` | `message` 生成后填写 | 若开启，不得重复整张 Jira 卡片内容 |
| 宿主播报目标 | `channel` / `to` | `announce_policy.channel` | 按需 | 空 | 只有需要把宿主执行摘要投递到指定频道时填写 | 目标必须是宿主可识别的频道或接收方 |
| 一次性任务自动删除 | `delete-after-run` | `schedule_type` | 条件建议 | `true` for `once` | `schedule_type=once` 时填写 | 周期任务不应为 true |
| 一次性任务保留 | `keep-after-run` | `keep_after_run` | 否 | 空 | 用户明确要求保留一次性任务时填写 | 与 `delete-after-run` 语义相反 |
| 固定模型 | `model` | `host_model` | 否 | 宿主默认模型 | 只有用户明确要求钉住模型时填写 | 不应和宿主默认策略冲突 |

实现提示：

1. `system-event` 和 `wake` 不属于本技能默认主路径；除非宿主被强制限制在 `session main`，否则不要填。
2. `target_chat_id` 是业务规格字段，不是 OpenClaw 宿主字段；它必须进入 `message`，而不是填进 `channel` 或 `to`。
3. `query_spec`、`base_jql`、`window_mode`、`notify_policy` 不直接映射成 OpenClaw 顶层字段，但必须先确认，再参与 `message` 渲染。

### 2.3 字段缺失时的追问规则表

下表固定了创建期字段缺失时的追问策略。优先顺序必须遵守：筛选目标 -> 项目范围 -> 窗口语义 -> 调度语义 -> 时区 -> 推送目标 -> 通知策略 -> 宿主补充项。

| 字段 | 默认值 | 何时追问 | 何时不追问 | 固定追问文案 |
| --- | --- | --- | --- | --- |
| `filter_prompt` | 无 | 用户只说“建一个 Jira 定时任务”之类的模糊意图时 | 用户已经明确说出筛选条件 | 你想定时检查哪类 Jira？请直接描述筛选条件，例如项目、类型、状态、标签、负责人、优先级或时间范围。 |
| `project` / `projects` | 无 | 未出现明确项目 Key，且无法从上下文稳定推断时 | 用户已经给出明确项目 Key，或 query_spec 能唯一推出项目范围 | 这条任务要查哪些 Jira 项目？请给我一个或多个项目 Key，例如 GENEVA。 |
| `task_name` | 自动从项目 + 核心筛选意图 + 调度语义生成候选值 | 只有在自动生成的候选名明显不清晰、或用户明确要求自定义名称时 | 候选名清晰且用户无异议 | 我准备把任务名设为“{{candidate_task_name}}”。如果你想改名，请直接告诉我新的任务名称。 |
| `window_mode` | `created` | 用户没有明确“新增/更新/存量”语义，且提醒场景存在歧义时 | 用户已明确说“新增”“最近更新”或“当前仍满足条件” | 这条任务按哪种窗口语义执行？可选：created（只看新增）、updated（只看最近更新）、snapshot（每次检查当前仍命中的数据）。 |
| `schedule_type` | 无 | 用户只说“定时”但没说明周期还是单次时 | 用户已明确是 recurring 还是 once | 这是周期任务还是一次性任务？如果是周期任务，我会用 cron；如果是一次性任务，我会用 at。 |
| `schedule_expr` | 无 | 无法从用户话术直接转换成明确的 cron 或 at 表达式时 | 已能稳定转换，例如“每小时”“每天 10 点”“20 分钟后”“明天上午 9 点” | 请给我明确的执行时间。你可以直接说“每小时”“每天 10 点”“20 分钟后”或一个具体时间。 |
| `timezone` | `Asia/Shanghai` | 用户所在时区不明确，且任务时间含义可能受时区影响时 | 用户明确指定时区，或可直接接受默认值 | 这条任务默认按 Asia/Shanghai 执行。如果你要用其他时区，请直接告诉我时区名称，例如 UTC 或 America/Los_Angeles。 |
| `target_chat_name` / `target_chat_id` | 无 | 没有可用的稳定 `target_chat_id` 时 | 已拿到稳定 `target_chat_id` | 这条提醒要发到哪个飞书群？如果你已经有稳定的 chat_id，请直接给我 `oc_...`；如果只有群名，也可以先告诉我群名。 |
| `target_chat_id` 二次确认 | 无 | 用户只提供了群名、别名或模糊目标，无法稳定解析 chat_id 时 | 已拿到稳定 `oc_...` ID | 我还缺少这个飞书群的稳定 chat_id。请提供 `oc_...` 形式的群 ID，避免把提醒发错群。 |
| `notify_policy.mode` | `per_issue` | 用户明确提到“汇总”“合并发送”或“不要一条一条发”时 | 用户无特殊要求 | 发送方式默认是每条 Jira 单独一张卡片。如果你更希望批量汇总，我可以改成 batch_summary。 |
| `notify_policy.max_issues_per_run` | `20` | 用户担心刷屏、或任务可能命中很多 Jira 时 | 用户无特殊要求且默认值适用 | 单轮提醒上限默认是 20 条。如果你想调小或调大，请告诉我一个数字。 |
| `notify_policy.repeat_snapshot` | `false` | `window_mode=snapshot` 且用户没有明确是否允许重复提醒时 | 非 snapshot 模式 | 当前是 snapshot 模式。默认只首次提醒同一条 Jira，不重复刷屏。你要不要允许重复提醒？ |
| `openclaw_session` | `isolated` | 用户明确要求跨次记忆、长期上下文或固定会话时 | 用户无特殊要求 | 这条任务默认用 OpenClaw 的 isolated session。只有你明确需要跨次记忆时，我才会改成持久 session。 |
| `announce` | `true` with compact summary | 用户明确说“不需要宿主播报结果”或“结果只发飞书群”时 | 用户无特殊要求 | 宿主侧默认会保留一条简短执行摘要；如果你不想要，我可以关闭 announce。 |
| `model` | 宿主默认模型 | 用户明确要求固定模型时 | 用户无特殊要求 | 这条任务默认使用宿主模型。如果你要固定成某个模型，请直接告诉我模型名。 |

实现约束：

1. `query_spec` 和 `base_jql` 不应直接追问；应在 `filter_prompt`、`project`、`window_mode` 充分明确后由系统生成，并放入确认摘要。
2. `message` 不应直接追问；它必须由确认后的业务规格自动渲染。
3. 当某字段已有稳定默认值且默认值不会改变业务语义时，可用“告知默认值 + 允许用户覆盖”的问法，不用强制阻塞创建。

### 2.4 OpenClaw 创建任务字段填充规则清单

下表直接对应 OpenClaw 宿主创建任务时常见的字段。默认目标是 `jira-scheduled-query-alert` 场景，推荐优先使用 `session isolated + message`。

| OpenClaw 字段 | 是否必填 | 填充值来源 | 填充规则 | 校验要求 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `name` | 是 | `task_name` | 直接使用确认后的任务名称 | 不允许为空；应能被用户识别 | 与业务摘要中的任务名称保持一致 |
| `cron` | 条件必填 | `schedule_expr` | 当 `schedule_type=recurring` 时填写 | 必须是合法 cron 表达式 | 与 `at` 二选一 |
| `at` | 条件必填 | `schedule_expr` | 当 `schedule_type=once` 时填写 | 相对时间、绝对时间或宿主支持的时间格式必须合法 | 与 `cron` 二选一 |
| `tz` | 强烈建议必填 | `timezone` | 默认填 `Asia/Shanghai`；用户显式指定时覆盖 | 应为合法 IANA 时区 | 对绝对时间和周期任务都建议显式设置 |
| `session` | 是 | `openclaw_session` | 默认填 `isolated` | 只能使用宿主支持的 session 语法 | 仅当用户明确要求跨次记忆时才使用命名持久 session |
| `message` | 是 | 定时执行消息模板 | 使用确认后的配置渲染，不允许自由发挥 | 不允许遗漏 `base_jql`、`target_chat_id`、`notify_policy` 等核心字段 | `session isolated` 和命名 session 都使用此字段 |
| `system-event` | 否 | 不建议使用 | 对本场景默认留空 | 若宿主必须填写，应停止并改回 `message` 方案 | 仅适合 `session main` 的简单提醒，不适合本技能 |
| `announce` | 建议填写 | 宿主策略 | 推荐开启，但结果只保留紧凑执行摘要 | 不应重复完整 Jira 卡片内容 | 若用户明确不需要宿主侧播报，可关闭 |
| `channel` / `to` | 按需 | 宿主侧结果投递目标 | 仅在需要把 announce 结果定向到特定频道时填写 | 目标必须是宿主可识别的频道或接收方 | 这不是飞书 `target_chat_id` |
| `model` | 否 | 用户显式指定或宿主默认 | 默认继承宿主模型，不主动写死 | 只有在用户明确要求模型钉住时才填写 | 例如成本、速度、稳定性有硬要求时使用 |
| `delete-after-run` | 条件建议 | `schedule_type` | 当 `schedule_type=once` 时建议开启 | 周期任务不应填写为 true | 对一次性任务，默认执行后自动删除 |
| `keep-after-run` | 否 | 用户显式要求 | 只在一次性任务需要保留记录或复盘时填写 | 与 `delete-after-run` 语义相反 | 默认不填 |
| `wake` | 否 | 不建议使用 | 默认留空 | 若使用 `session main` 才需要考虑 | 本技能默认不走 `session main` |

### 2.5 直接对应宿主实现的最小填充顺序

1. 先确认业务规格：`task_name`、`query_spec`、`base_jql`、`window_mode`、`target_chat_id`、`notify_policy`。
2. 再确认调度语义：`schedule_type`、`schedule_expr`、`timezone`。
3. 默认填 `session=isolated`。
4. 用本文件的定时执行消息模板渲染 `message`。
5. 根据 `schedule_type` 二选一填写 `cron` 或 `at`。
6. 根据宿主策略填写 `announce`；若需要宿主侧播报落到某个频道，再填 `channel` 或 `to`。
7. 仅在用户明确要求时填写 `model`、`keep-after-run` 等可选字段。

### 2.6 直接对应宿主实现的命令骨架

周期任务骨架：

```text
openclaw cron add \
   --name "{{task_name}}" \
   --cron "{{schedule_expr}}" \
   --tz "{{timezone}}" \
   --session isolated \
   --message "{{rendered_execution_message}}" \
   --announce
```

一次性任务骨架：

```text
openclaw cron add \
   --name "{{task_name}}" \
   --at "{{schedule_expr}}" \
   --tz "{{timezone}}" \
   --session isolated \
   --message "{{rendered_execution_message}}" \
   --announce \
   --delete-after-run
```

如果需要把宿主侧执行摘要发送到指定频道，可在命令尾部追加 `--channel <HOST_CHANNEL>` 或宿主支持的等价字段。不要把飞书 `target_chat_id` 误填到这里。

## 3. 创建期确认摘要模板

建议在真正创建 OpenClaw 定时任务前，向用户输出以下确认摘要：

```md
请确认以下 OpenClaw Jira 定时任务配置：

- 任务名称：{{task_name}}
- 场景标识：jira-scheduled-query-alert
- Jira 项目范围：{{project_scope}}
- 用户原始筛选意图：{{filter_prompt}}
- 基础 JQL：{{base_jql}}
- 窗口语义：{{window_mode}}（{{window_mode_explanation}}）
- 调度方式：{{schedule_type}} / {{schedule_expr}}
- 时区：{{timezone}}
- OpenClaw session：{{openclaw_session}}
- 推送目标群：{{target_chat_name}} / {{target_chat_id}}
- 通知策略：{{notify_policy_summary}}
- LLM 策略：on-match-only
- 卡片模板：lark-jira-query-alert-card-v1

query_spec：
```json
{{query_spec_pretty_json}}
```

请回复以下两类结果之一：
1. 回复“确认创建”，允许 OpenClaw 创建定时任务。
2. 回复需要修改的字段，例如“把窗口模式改成 updated”或“改成每天 10 点执行”。
```

### 3.1 字段填充建议

| 占位符 | 填充建议 |
| --- | --- |
| `{{project_scope}}` | 单项目写 `GENEVA`，多项目写 `GENEVA, ACTIVE, ...` |
| `{{window_mode_explanation}}` | `created=只检查新增`，`updated=只检查最近更新`，`snapshot=每次检查当前仍命中的数据` |
| `{{openclaw_session}}` | 默认 `isolated` |
| `{{notify_policy_summary}}` | 例如 `per_issue, max_issues_per_run=20, repeat_snapshot=false` |
| `{{query_spec_pretty_json}}` | 建议格式化 JSON，方便用户审计 |

## 4. 定时执行消息模板

以下模板可直接作为 OpenClaw 到期执行时注入给模型的 message：

```text
你正在执行 active-jira-automation 的定时任务。
场景：jira-scheduled-query-alert。

这是已确认配置，不允许重新解释用户意图，不允许修改 JQL、群组或消息结构。

task_name: {{task_name}}
scenario_key: jira-scheduled-query-alert
project_scope: {{project_scope}}
filter_prompt: {{filter_prompt}}
query_spec: {{query_spec_compact_json}}
base_jql: {{base_jql}}
window_mode: {{window_mode}}
lookback_minutes: {{lookback_minutes}}
schedule_type: {{schedule_type}}
schedule_expr: {{schedule_expr}}
timezone: {{timezone}}
target_chat_id: {{target_chat_id}}
target_chat_name: {{target_chat_name}}
notify_policy: {{notify_policy_compact_json}}
message_template_key: lark-jira-query-alert-card-v1

执行要求：
1. 仅使用确认后的配置运行共享脚本。
2. 先进行确定性 Jira 查询与去重，再决定是否需要调用 LLM。
3. 不得改写 base_jql，不得重新选择 target_chat_id，不得更换消息模板。
4. 如果无命中：
   - 不调用 LLM。
   - 不发送飞书消息。
   - 输出简短执行摘要，说明无命中与查询窗口。
5. 如果有命中：
   - 先按 key 拉取详情。
   - 仅生成受控字段：match_reason、problem_summary、risk_assessment。
   - 使用 lark-jira-query-alert-card-v1 渲染 interactive card。
   - 向 target_chat_id 发送卡片。
6. 输出最终执行摘要时，只汇报 task_name、window、match_count、delivery_count、target_chat_id 和是否成功；不要重复整张卡片内容。
```

### 4.1 适合直接填入 OpenClaw 的宿主字段

如果宿主需要把这些结果映射到自己的定时参数，建议按如下方式对齐：

| OpenClaw 宿主字段 | 填充值来源 |
| --- | --- |
| `name` | `{{task_name}}` |
| `cron` | `{{schedule_expr}}`，当 `schedule_type=recurring` |
| `at` | `{{schedule_expr}}`，当 `schedule_type=once` |
| `tz` | `{{timezone}}` |
| `session` | 默认 `isolated`，或用户明确指定的持久 session |
| `message` | 使用上面的定时执行消息模板 |
| `announce` | 按宿主默认；若飞书群收到卡片，announce 只保留简短摘要 |
| `channel` / `to` | 只有在需要把 announce 结果发送到指定频道时填写 |

更细的字段填充与校验规则见上文“OpenClaw 创建任务字段填充规则清单”。

## 5. 一份可直接替换占位符的样例

以下是一个完整样例，便于宿主侧实现联调：

```text
你正在执行 active-jira-automation 的定时任务。
场景：jira-scheduled-query-alert。

这是已确认配置，不允许重新解释用户意图，不允许修改 JQL、群组或消息结构。

task_name: Geneva P0 Bug Alert
scenario_key: jira-scheduled-query-alert
project_scope: GENEVA
filter_prompt: 每小时查询一次 GENEVA 新增的 P0 Bug
query_spec: {"projects":["GENEVA"],"clauses":[{"field":"issuetype","op":"=","value":"Bug"},{"field":"customfield_10401","alias":"Severity","op":"=","value":"P0"}],"order_by":[{"field":"created","direction":"ASC"}]}
base_jql: project = GENEVA AND issuetype = Bug AND "Severity" = P0
window_mode: created
lookback_minutes: 5
schedule_type: recurring
schedule_expr: 0 * * * *
timezone: Asia/Shanghai
target_chat_id: oc_xxx
target_chat_name: 测试告警群
notify_policy: {"mode":"per_issue","max_issues_per_run":20,"repeat_snapshot":false}
message_template_key: lark-jira-query-alert-card-v1

执行要求：
1. 仅使用确认后的配置运行共享脚本。
2. 先进行确定性 Jira 查询与去重，再决定是否需要调用 LLM。
3. 不得改写 base_jql，不得重新选择 target_chat_id，不得更换消息模板。
4. 如果无命中：不调用 LLM，不发送飞书消息，只输出简短执行摘要。
5. 如果有命中：按 key 拉取详情，生成受控摘要字段，渲染 interactive card，并向 target_chat_id 发送卡片。
6. 输出最终执行摘要时，只汇报 task_name、window、match_count、delivery_count、target_chat_id 和是否成功。
```