# active-jira-automation 专项 TODO

## 1. 任务目标

基于以下设计文档，将 `active-jira-automation` 拆成可执行、可验收、可逐步交付的工程任务：

- [active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)
- [active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md)

最终交付目标是：

1. 保留并完善独立的 `active-jira-automation` Skill 目录与基础框架。
2. 落地一套可复用的自动化任务框架：任务管理、场景接入、统一 runner、检查点、去重、LLM 摘要、飞书 interactive 卡片投递。
3. 接入首个场景 `jira-scheduled-query-alert`，实现“用户自定义 JQL/筛选条件 + 定时查询 + 命中提醒”。
4. 让 `P0 Bug` 只作为一个样例筛选条件，而不是场景代码、模板或任务模型中的硬编码边界。
5. 让后续自动化场景以子能力 / 子方案形式接入，而不是重复实现公共运行时。

## 2. 设计修正结论

本次修正的核心结论：

- 旧方向：首期只支持 `new-p0-bug-alert`，查询条件固定为新增 P0 Bug。
- 新方向：首期支持 `jira-scheduled-query-alert`，由用户自由描述筛选条件，Agent 创建期生成并确认 `query_spec/base_jql`，运行期稳定脚本参数化执行。

工程上不要为每个任务生成一份查询脚本。应实现：

- 一个稳定复用的查询 runtime。
- 一个通用场景接入模块。
- 一个通用卡片模板。
- 多个任务各自保存 `filter_prompt`、`query_spec`、`base_jql`、`window_mode`、调度与群组配置。

## 3. Design -> Build 映射

| 设计来源 | 设计结论 | 对应构建产物 |
| --- | --- | --- |
| 框架文档“职责边界” | `active-jira-automation` 负责任务模型、调度适配、场景接入、执行编排 | `active-jira-automation/SKILL.md`、`scripts/` 公共运行时 |
| 框架文档“通用任务模型” | 任务定义需要保存可审计查询配置 | `task_store.py`、`manage_tasks.py create` |
| 场景文档“查询规格与 JQL 生成” | 创建期生成 `query_spec/base_jql`，运行期参数化执行 | `jira_query_runtime.py`、`scenarios/jira_scheduled_query_alert.py` |
| 场景文档“查询窗口、命中与去重规则” | 支持 `created/updated/snapshot` 三类窗口语义 | `jira_query_runtime.py`、`run_automation_task.py` |
| 场景文档“场景接入契约” | 场景一不硬编码 P0 Bug | `scripts/scenarios/jira_scheduled_query_alert.py` |
| 场景文档“卡片模板设计” | 需要通用 Jira 查询命中提醒卡片 | `scripts/templates/lark_jira_query_alert_card_v1.py` |
| 场景文档“LLM 策略” | 创建期可辅助生成 JQL，运行期仅命中后轻量分析 | `SKILL.md` workflow、`llm_summary_runtime.py` |

## 4. 阶段总览

| 阶段 | 名称 | 主要产物 | 状态 |
| --- | --- | --- | --- |
| P0 | 设计修正与范围重置 | 场景文档、TODO、框架文档链接修正 | 进行中 |
| P1 | 既有框架骨架确认 | Skill 目录、任务存储、runner、调度、投递 runtime | 基本已完成，需泛化复查 |
| P2 | 任务模型泛化 | 新增 `filter_prompt/query_spec/base_jql/window_mode/notify_policy` | 待做 |
| P3 | 查询 runtime 泛化 | 参数化 JQL、窗口组合、`snapshot` 去重 | 待做 |
| P4 | 场景一通用接入 | `jira_scheduled_query_alert.py` | 待做 |
| P5 | 通用卡片模板 | `lark_jira_query_alert_card_v1.py` | 待做 |
| P6 | 创建工作流与 Skill 文档 | Agent 追问、JQL 确认摘要、dry-run 规则 | 待做 |
| P7 | 端到端验收 | fixture、dry-run、样例任务、回归测试 | 待做 |

## 5. P0 设计修正与范围重置

### P0.1 修正场景一设计文档

- [x] 代码目标：
  - [x] 将场景一从“新增 P0 BUG Jira 定时提醒”改为“Jira 定时查询并提醒”。
  - [x] 明确 `P0 Bug` 只是样例，不是硬编码边界。
  - [x] 定义 `filter_prompt/query_spec/base_jql/window_mode/notify_policy`。
  - [x] 定义创建期 JQL 生成与用户确认流程。
  - [x] 定义运行期稳定脚本参数化执行方式。
- [x] 测试目标：
  - [x] 文档中能明确区分“创建期意图编译”和“运行期确定性执行”。
- [x] 验收命令：

```sh
rg -n "jira-scheduled-query-alert|filter_prompt|base_jql|window_mode|P0 Bug.*样例" doc/active-jira-automation\ 定时查询并提醒场景设计.md
```

### P0.2 修正专项 TODO 基线

- [x] 代码目标：
  - [x] 将 TODO 从 `new-p0-bug-alert` 专项改为 `jira-scheduled-query-alert` 通用场景。
  - [x] 明确既有 P1-P4 框架代码可保留，但 P5 场景接入需要重做。
- [x] 测试目标：
  - [x] TODO 中不再把 P0 Bug 作为首期唯一目标。
- [x] 验收命令：

```sh
rg -n "jira-scheduled-query-alert|query_spec|base_jql|lark_jira_query_alert_card_v1" doc/active-jira-automation-todo.md
```

### P0.3 修正框架主文档引用

- [x] 代码目标：
  - [x] 将框架文档中首个场景链接从旧 P0 专用文档改为新通用场景文档。
  - [x] 将目录结构建议从 `new_p0_bug_alert.py` 改为 `jira_scheduled_query_alert.py`。
  - [x] 将首期场景表改为 `jira-scheduled-query-alert`。
- [x] 测试目标：
  - [x] 主文档与场景文档使用同一套场景标识和模板标识。
- [x] 验收命令：

```sh
rg -n "jira-scheduled-query-alert|定时查询并提醒|jira_scheduled_query_alert|lark_jira_query_alert_card_v1" doc/active-jira-automation\ 框架能力设计.md
```

## 6. P1 既有框架骨架确认

### P1.1 确认 Skill 目录与公共 runtime 仍可复用

- [x] 代码目标：
  - [x] 保留 `active-jira-automation/` 目录。
  - [x] 保留 `manage_tasks.py`、`task_store.py`、`run_automation_task.py`、`scheduler_adapter.py`。
  - [x] 保留 `jira_query_runtime.py`、`llm_summary_runtime.py`、`lark_delivery_runtime.py`。
- [x] 复查目标：
  - [x] 确认现有公共 runtime 没有把 `new-p0-bug-alert` 写成不可替换逻辑。
  - [x] 若只是测试 fixture 中有 P0 样例，可后续替换或保留为样例。
- [x] 验收命令：

```sh
find active-jira-automation -maxdepth 3 | sort
rg -n "new-p0-bug-alert|lark-p0-bug-card-v1|new_p0_bug_alert" active-jira-automation
```

### P1.2 修正 Skill 基础说明

- [x] 代码目标：
  - [x] 将 `active-jira-automation/SKILL.md` 的支持场景改为 `jira-scheduled-query-alert`。
  - [x] 增加自然语言筛选条件到 JQL 确认摘要的工作流。
  - [x] 增加 `created/updated/snapshot` 窗口语义说明。
  - [x] 保留 create/list/pause/resume/delete 任务生命周期说明。
- [x] 测试目标：
  - [x] 文案能驱动 Agent 先收集必要信息，再确认 JQL，最后创建任务。
- [x] 验收命令：

```sh
rg -n "jira-scheduled-query-alert|base_jql|window_mode|snapshot|dry-run" active-jira-automation/SKILL.md
```

### P1.3 修正参考文档

- [x] 代码目标：
  - [x] 更新 `active-jira-automation/references/automation-framework.md` 的 MVP 场景。
  - [x] 如 `scenario-access-contract.md` 中有 P0 专用示例，替换为通用查询提醒示例。
- [x] 测试目标：
  - [x] Skill 内部 references 与 doc 目录中的设计一致。
- [x] 验收命令：

```sh
rg -n "jira-scheduled-query-alert|new-p0-bug-alert" active-jira-automation/references
```

## 7. P2 任务模型泛化

### P2.1 扩展任务定义 schema

- [ ] 代码目标：
  - [ ] 在任务定义中支持 `filter_prompt`。
  - [ ] 支持 `query_spec`。
  - [ ] 支持 `base_jql`。
  - [ ] 支持 `window_mode`：`created`、`updated`、`snapshot`。
  - [ ] 支持 `lookback_minutes`。
  - [ ] 支持 `notify_policy`：`mode`、`max_issues_per_run`、`repeat_snapshot`。
- [ ] 测试目标：
  - [ ] 覆盖最小合法任务、缺失 `base_jql`、非法 `window_mode`、非法 `notify_policy`。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_task_store.py'
```

### P2.2 泛化 `manage_tasks.py create`

- [ ] 代码目标：
  - [ ] 将 `--scenario new-p0-bug-alert` 替换为 `--scenario jira-scheduled-query-alert`。
  - [ ] 支持 `--filter-prompt`。
  - [ ] 支持 `--base-jql`。
  - [ ] 支持 `--query-spec-json` 或 `--query-spec-file`。
  - [ ] 支持 `--window-mode` 和 `--lookback-minutes`。
  - [ ] 支持 `--notify-policy-json`。
  - [ ] 创建摘要输出 `base_jql` 与窗口语义，便于用户确认。
- [ ] 测试目标：
  - [ ] 覆盖 CLI 参数创建、JSON 输入创建、缺失必填字段报错、重复任务名处理。
- [ ] 验收命令：

```sh
python active-jira-automation/scripts/manage_tasks.py create --help
python -m unittest discover active-jira-automation/tests -p 'test_manage_tasks.py'
```

### P2.3 兼容旧任务或明确迁移策略

- [ ] 代码目标：
  - [ ] 若存在旧 `new-p0-bug-alert` 任务，提供只读兼容或迁移提示。
  - [ ] 明确不自动修改用户已有任务 JSON，除非用户执行迁移命令。
- [ ] 测试目标：
  - [ ] 旧任务读取不会导致 list/pause/delete 崩溃。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_manage_tasks.py'
```

## 8. P3 查询 runtime 泛化

### P3.1 实现参数化 JQL 组合

- [ ] 代码目标：
  - [ ] `jira_query_runtime.py` 接收 `base_jql` 和窗口参数。
  - [ ] `created` 模式追加 created 时间窗口。
  - [ ] `updated` 模式追加 updated 时间窗口。
  - [ ] `snapshot` 模式不追加时间窗口。
  - [ ] `ORDER BY` 与窗口字段保持一致，允许任务配置覆盖。
- [ ] 测试目标：
  - [ ] 覆盖三种窗口模式的最终 JQL 输出。
  - [ ] 覆盖 JQL 中已有 `ORDER BY` 时的处理策略。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_jira_query_runtime.py'
```

### P3.2 修正检查点与去重逻辑

- [ ] 代码目标：
  - [ ] `created` 去重键使用 `task_id + issue_key + created`。
  - [ ] `updated` 去重键使用 `task_id + issue_key + updated`。
  - [ ] `snapshot` 去重键使用 `task_id + issue_key + base_jql_hash`。
  - [ ] 查询失败不推进检查点。
  - [ ] 无命中时只更新检查点和日志。
- [ ] 测试目标：
  - [ ] 覆盖首次运行、续跑、回看窗口、重复命中过滤、查询失败。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_jira_query_runtime.py'
python -m unittest discover active-jira-automation/tests -p 'test_run_automation_task.py'
```

### P3.3 接入真实 Jira 查询命令前的 fixture 运行

- [ ] 代码目标：
  - [ ] 准备本地 fixture JSON，模拟不同 JQL 命中结果。
  - [ ] runner 支持 dry-run/fixture 模式，避免早期依赖真实 Jira。
- [ ] 测试目标：
  - [ ] 用 fixture 跑通无命中、单条命中、多条命中、超出上限。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_run_automation_task.py'
```

## 9. P4 场景一通用接入

### P4.1 实现场景接入模块

- [ ] 代码目标：
  - [ ] 新增 `scripts/scenarios/jira_scheduled_query_alert.py`。
  - [ ] 实现 `config_schema/defaulting_rules/query_builder/result_normalizer/match_identity/llm_output_schema`。
  - [ ] 不在模块中写死 P0、Bug、GENEVA 或特定状态。
- [ ] 测试目标：
  - [ ] 覆盖 P0 Bug 样例、Open Blocker 样例、assignee 为空样例、标签样例。
  - [ ] 覆盖字段归一化、字段缺失兜底、去重键生成。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_jira_scheduled_query_alert.py'
```

### P4.2 更新场景注册表

- [ ] 代码目标：
  - [ ] 注册 `jira-scheduled-query-alert`。
  - [ ] 移除或降级旧 `new-p0-bug-alert` 注册。
  - [ ] 确认 `message_template_key = lark-jira-query-alert-card-v1`。
- [ ] 测试目标：
  - [ ] 覆盖注册成功、读取未知场景失败、旧 key 兼容或明确报错。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_scenario_registry.py'
```

### P4.3 修正 runner 场景调用

- [ ] 代码目标：
  - [ ] runner 从任务定义读取 `base_jql/window_mode/notify_policy`。
  - [ ] runner 只在命中后调用 LLM。
  - [ ] runner 根据 `notify_policy.max_issues_per_run` 限制发送。
- [ ] 测试目标：
  - [ ] 覆盖无命中零 Token、有命中摘要、dry-run、不合法配置、超出上限。
- [ ] 验收命令：

```sh
python active-jira-automation/scripts/run_automation_task.py --help
python -m unittest discover active-jira-automation/tests -p 'test_run_automation_task.py'
```

## 10. P5 通用卡片模板

### P5.1 实现通用提醒卡片模板

- [ ] 代码目标：
  - [ ] 新增 `templates/lark_jira_query_alert_card_v1.py`。
  - [ ] 按场景文档输出固定结构的 interactive card JSON。
  - [ ] 标题使用任务名或 `Jira 查询命中提醒`。
  - [ ] 支持字段长度裁剪与空值兜底。
  - [ ] 支持基于 Severity/Priority 或任务配置选择 header 颜色。
- [ ] 测试目标：
  - [ ] 覆盖完整字段、缺失责任人、缺失版本、超长 Summary、LLM 摘要缺失、无优先级。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_lark_jira_query_alert_card_v1.py'
```

### P5.2 保留 interactive 卡片公共校验

- [ ] 代码目标：
  - [ ] 复用 `renderers/interactive_card_renderer.py`。
  - [ ] 保持允许组件白名单：`header/div/fields/hr/note/action`。
  - [ ] 不让 LLM 直接输出整张卡片 JSON。
- [ ] 测试目标：
  - [ ] 现有卡片校验测试继续通过。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_interactive_card_renderer.py'
python -m unittest discover active-jira-automation/tests -p 'test_lark_delivery_runtime.py'
```

## 11. P6 创建工作流与文档

### P6.1 更新 Agent 创建任务工作流

- [ ] 代码目标：
  - [ ] 在 `SKILL.md` 中描述追问顺序：筛选目标、项目、窗口语义、调度、群组、通知策略。
  - [ ] 要求 Agent 生成 `base_jql` 后必须展示确认摘要。
  - [ ] 明确用户确认前不得创建调度器。
- [ ] 测试目标：
  - [ ] 文档能支撑首次试用，不依赖口头说明。
- [ ] 验收命令：

```sh
rg -n "追问|确认摘要|base_jql|window_mode|target_chat" active-jira-automation/SKILL.md
```

### P6.2 更新 README 或项目入口说明

- [ ] 代码目标：
  - [ ] 在 README 中新增 `active-jira-automation` 通用查询提醒能力说明。
  - [ ] 提供至少 3 个样例：P0 Bug、新增标签、更新未分配。
- [ ] 测试目标：
  - [ ] 示例命令与实际 CLI 参数一致。
- [ ] 验收命令：

```sh
rg -n "active-jira-automation|jira-scheduled-query-alert|base-jql|window-mode" README.md active-jira-automation/SKILL.md
```

## 12. P7 端到端验收

### P7.1 跑通 P0 Bug 样例，但验证它不是硬编码

- [ ] 代码目标：
  - [ ] 创建一个 P0 Bug 查询提醒任务。
  - [ ] 通过 fixture/dry-run 跑通命中路径。
- [ ] 测试目标：
  - [ ] 确认 P0 Bug 只是任务配置里的 `base_jql`，不是场景代码固定逻辑。
- [ ] 验收命令：

```sh
python active-jira-automation/scripts/manage_tasks.py create \
  --scenario jira-scheduled-query-alert \
  --task-name "Geneva P0 Bug Alert" \
  --project GENEVA \
  --filter-prompt "每小时查询一次 GENEVA 新增的 P0 Bug" \
  --base-jql 'project = GENEVA AND issuetype = Bug AND "Severity" = P0' \
  --window-mode created \
  --schedule-type recurring \
  --schedule-expr '0 * * * *' \
  --target-chat-id oc_demo \
  --dry-run
```

### P7.2 跑通非 P0 样例

- [ ] 代码目标：
  - [ ] 创建一个非 P0、非 Bug 的查询提醒任务。
  - [ ] 证明同一场景模块可以复用。
- [ ] 测试目标：
  - [ ] 覆盖例如 `assignee is EMPTY`、`labels = customer-escalation`、`status = Open` 等条件。
- [ ] 验收命令：

```sh
python active-jira-automation/scripts/manage_tasks.py create \
  --scenario jira-scheduled-query-alert \
  --task-name "Unassigned Updated Issues Alert" \
  --project GENEVA \
  --filter-prompt "每 30 分钟提醒最近有更新且 assignee 为空的 Jira" \
  --base-jql 'project = GENEVA AND assignee is EMPTY' \
  --window-mode updated \
  --schedule-type recurring \
  --schedule-expr '*/30 * * * *' \
  --target-chat-id oc_demo \
  --dry-run
```

### P7.3 形成首期验收清单

- [ ] 代码目标：
  - [ ] 将框架文档和场景文档中的首期验收标准收敛成一份执行清单。
  - [ ] 标记已满足、待验证、受阻项。
- [ ] 测试目标：
  - [ ] 验收清单能直接用于发布前 review。
- [ ] 验收命令：

```sh
rg -n "首期落地范围|验收标准|jira-scheduled-query-alert" doc/active-jira-automation\ 框架能力设计.md doc/active-jira-automation\ 定时查询并提醒场景设计.md doc/active-jira-automation-todo.md
```

## 13. 当前建议执行顺序

建议按以下顺序推进：

1. P0.3
2. P1.1 -> P1.2 -> P1.3
3. P2.1 -> P2.2 -> P2.3
4. P3.1 -> P3.2 -> P3.3
5. P4.1 -> P4.2 -> P4.3
6. P5.1 -> P5.2
7. P6.1 -> P6.2
8. P7.1 -> P7.2 -> P7.3

原因：

- 先把文档和 Skill 工作流统一，避免实现继续沿用旧 P0 专用命名。
- 先扩展任务模型，再改查询 runtime。
- 先有通用场景接入，再做通用卡片模板。
- 最后用 P0 Bug 和非 P0 两类样例共同验收，确认没有硬编码回潮。

## 14. 当前显式阻塞项

进入实现阶段后，需要提前关注以下阻塞：

1. 自定义字段别名到 Jira 字段 ID 的解析能力是否已经能从 `active-jira` 复用。
2. 创建期 JQL 由 Agent 生成后，是否需要额外的 JQL dry-run 校验命令。
3. `snapshot` 模式的重复提醒策略需要产品侧确认：默认只首次提醒，还是允许定期重复播报。
4. 单次命中 Jira 数量较大时，是否首期只做上限截断，还是同步实现折叠/批量摘要卡片。
