# active-jira-automation 专项 TODO

## 1. 任务目标

基于以下设计文档，将 `active-jira-automation` 拆成可执行、可验收、可逐步交付的工程任务：

- [active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)
- [active-jira-automation 定时查询P0并提醒场景设计](./active-jira-automation%20定时查询P0并提醒场景设计.md)

最终交付目标是：

1. 新增独立的 `active-jira-automation` Skill 目录与基础说明。
2. 落地一套可复用的自动化任务框架：任务管理、场景接入、统一 runner、检查点、去重、LLM 摘要、飞书 interactive 卡片投递。
3. 接入首个场景 `new-p0-bug-alert`，实现“定时查询新增 P0 BUG Jira 并发送飞书 interactive 卡片提醒”。
4. 让后续自动化场景以子能力 / 子方案的形式接入，而不是重复实现公共运行时。

本任务清单按阶段推进，前一阶段达到可验收状态后再进入下一阶段。

## 2. Design -> Build 映射

| 设计来源 | 设计结论 | 对应构建产物 |
| --- | --- | --- |
| 框架文档第 4 节“职责边界” | `active-jira-automation` 负责任务模型、调度适配、场景接入、执行编排 | `active-jira-automation/SKILL.md`、`scripts/` 公共运行时 |
| 框架文档第 5 节“框架能力分层” | 需要任务管理层、场景接入层、执行引擎、投递模板层、调度适配层、审计层 | `manage_tasks.py`、`scenario_registry.py`、`run_automation_task.py`、`scheduler_adapter.py`、`lark_delivery_runtime.py` |
| 框架文档第 6 节“通用任务模型” | 需要统一任务定义、运行态、日志布局 | `data/tasks/`、`data/runtime/`、`data/logs/` 约定与读写 helper |
| 框架文档第 8 节“通用执行管线” | 所有场景必须复用统一 runner | `run_automation_task.py` |
| 框架文档第 9 节“Interactive 卡片公共契约” | 飞书消息必须是可校验的 interactive card JSON | `renderers/interactive_card_renderer.py`、`lark_delivery_runtime.py` |
| 框架文档第 10 节“场景接入契约” | 每个场景必须声明配置、查询构造、归一化、LLM schema、模板 | `scripts/scenarios/new_p0_bug_alert.py` |
| 场景文档第 3 节“场景输入与交互引导” | 需要收集 `project/query_rule/schedule/target_chat` | `manage_tasks.py create`、`SKILL.md` workflow |
| 场景文档第 5 节“查询与命中规则” | 需要查询窗口、回看窗口、去重键 | `jira_query_runtime.py`、`run_automation_task.py` |
| 场景文档第 7 节“LLM 策略” | 仅命中后调用 LLM，且输出字段受控 | `llm_summary_runtime.py`、场景 schema |
| 场景文档第 8 节“卡片模板设计” | 需要 `lark-p0-bug-card-v1` 模板与字段兜底 | `templates/lark_p0_bug_card_v1.py` |

## 3. 阶段总览

| 阶段 | 名称 | 主要产物 | 风险等级 |
| --- | --- | --- | --- |
| P0 | 设计冻结与外部契约确认 | TODO、接口边界、外部依赖确认 | 中 |
| P1 | Skill 目录与框架骨架 | `SKILL.md`、目录结构、占位脚本 | 低 |
| P2 | 任务管理与持久化 | 任务模型、状态机、`manage_tasks.py` | 中 |
| P3 | 通用执行引擎与调度适配 | `run_automation_task.py`、`scheduler_adapter.py` | 高 |
| P4 | Interactive 卡片投递链路 | 渲染器、发送器、dry-run、校验 | 高 |
| P5 | 场景一接入 | `new_p0_bug_alert.py`、P0 卡片模板 | 高 |
| P6 | 文档、联调与验收 | README/Skill 文档、端到端 dry-run | 中 |

## 4. P0 设计冻结与外部契约确认

### P0.1 冻结框架能力边界

- [x] 代码目标：
  - [x] 确认框架只承接任务管理、场景接入、统一 runner、interactive 卡片投递，不重复封装通用 Jira/Lark 基础能力。
  - [x] 确认首期只支持单场景 `new-p0-bug-alert`。
- [x] 测试目标：
  - [x] 文档审阅时能明确区分框架公共能力与场景差异。
- [x] 验收命令：

```sh
rg -n "职责边界|框架能力分层|场景接入契约|首期落地范围" doc/active-jira-automation\ 框架能力设计.md
rg -n "场景接入主文档的实现映射|场景代码接入建议" doc/active-jira-automation\ 定时查询P0并提醒场景设计.md
```

- [x] 阻塞项：
  - [x] 若后续要同时接入多个场景，首期范围可能膨胀。
- [x] 解阻条件：
  - [x] 明确 MVP 仅覆盖框架壳 + 场景一。

### P0.2 确认外部依赖契约

- [x] 代码目标：
  - [x] 明确 Openclaw 的创建、暂停、恢复、删除接口形态。
  - [x] 明确飞书 interactive 卡片发送首期是否直接走 raw API fallback。
  - [x] 明确 Jira 字段 `Severity/Priority/归属Team/来源/修复版本` 的稳定路径。
- [x] 测试目标：
  - [x] 形成一份外部依赖确认清单，避免实现阶段出现字段猜测或接口漂移。
- [x] 验收命令：

```sh
test -f doc/active-jira-automation\ P0设计冻结与外部契约确认.md
rg -n "Openclaw|raw API fallback|customfield_10401|fixVersions|customfield_11801|来源" doc/active-jira-automation\ P0设计冻结与外部契约确认.md
```

- [x] 阻塞项：
  - [x] Openclaw 接口未冻结。
  - [x] Jira 字段路径仍不稳定。
- [x] 解阻条件：
  - [x] 补一份外部接口确认记录，至少冻结首期字段与发送路径。

### P0.3 冻结专项 TODO 基线

- [x] 代码目标：
  - [x] 产出本专项 TODO 文档，形成执行基线。
- [x] 测试目标：
  - [x] TODO 文档结构覆盖阶段、原子任务、验收命令、阻塞项与解阻条件。
- [x] 验收命令：

```sh
test -f doc/active-jira-automation-todo.md
rg -n "Design -> Build 映射|阶段总览|阻塞项|解阻条件" doc/active-jira-automation-todo.md
```

- [x] 阻塞项：
  - [x] 无。
- [x] 解阻条件：
  - [x] 无。

## 5. P1 Skill 目录与框架骨架

### P1.1 创建 Skill 目录骨架

- [x] 代码目标：
  - [x] 新增 `active-jira-automation/` 目录。
  - [x] 创建 `SKILL.md`、`agents/openai.yaml`、`references/`、`scripts/`、`tests/` 基础结构。
- [x] 测试目标：
  - [x] 目录结构与框架文档第 11 节保持一致。
- [x] 验收命令：

```sh
find active-jira-automation -maxdepth 3 | sort
```

- [x] 阻塞项：
  - [x] 技术方案未冻结时，目录设计可能反复变动。
- [x] 解阻条件：
  - [x] 按框架文档第 11 节一次性创建最小骨架，后续只增量补充。

### P1.2 起草 SKILL 基础说明

- [x] 代码目标：
  - [x] 编写 `active-jira-automation/SKILL.md`。
  - [x] 覆盖创建、列出、暂停、恢复、删除任务的触发语句。
  - [x] 覆盖场景一的参数收集和 `dry-run` 规则。
- [x] 测试目标：
  - [x] 文案能准确驱动 Agent 走到“框架公共能力 + 场景一”的执行路径。
- [x] 验收命令：

```sh
rg -n "create|list|pause|resume|delete|new-p0-bug-alert|dry-run" active-jira-automation/SKILL.md
```

- [x] 阻塞项：
  - [x] 场景一的参数名和默认值还可能调整。
- [x] 解阻条件：
  - [x] 先按现有场景文档冻结最小字段：`project/query_rule/schedule_type/schedule_expr/target_chat_id`。

### P1.3 创建场景注册表骨架

- [x] 代码目标：
  - [x] 新增 `scripts/scenario_registry.py`。
  - [x] 支持按 `scenario_key` 注册和读取场景实现。
  - [x] 预留场景接入契约校验入口。
- [x] 测试目标：
  - [x] 至少覆盖“注册成功、重复注册失败、读取未知场景失败”。
- [x] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_scenario_registry.py'
```

- [x] 阻塞项：
  - [x] 场景对象契约未固定。
- [x] 解阻条件：
  - [x] 先以框架文档第 10 节中的必填接入项为最小契约。

## 6. P2 任务管理与持久化

### P2.1 实现任务模型与存储 helper

- [x] 代码目标：
  - [x] 实现任务定义、运行态、日志路径的读写 helper。
  - [x] 固定 `data/tasks/`、`data/runtime/`、`data/logs/` 布局。
  - [x] 定义任务状态机：`enabled/paused/deleted`。
- [x] 测试目标：
  - [x] 覆盖创建任务定义、更新状态、写入运行态、写入日志。
- [x] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_task_store.py'
```

- [x] 阻塞项：
  - [x] `task_id` 生成规则和日志格式未确定。
- [x] 解阻条件：
  - [x] 先使用稳定 slug + 时间戳或 UUID，日志统一写 JSON。

### P2.2 实现 `manage_tasks.py list/pause/resume/delete`

- [x] 代码目标：
  - [x] 新增 `manage_tasks.py`。
  - [x] 先实现 `list`、`pause`、`resume`、`delete`。
  - [x] `delete` 默认为逻辑删除并保留历史日志。
- [x] 测试目标：
  - [x] 覆盖按 `task_id` 操作、按名称唯一匹配操作、删除确认前置约束。
- [x] 验收命令：

```sh
python active-jira-automation/scripts/manage_tasks.py --help
python -m unittest discover active-jira-automation/tests -p 'test_manage_tasks.py'
```

- [x] 阻塞项：
  - [x] CLI 参数设计不稳，后续 create 子命令可能影响整体命令形态。
- [x] 解阻条件：
  - [x] 先冻结子命令风格：`manage_tasks.py <subcommand> ...`。

### P2.3 实现 `manage_tasks.py create` 基础落盘能力

- [x] 代码目标：
  - [x] 支持把结构化配置写入任务定义。
  - [x] 支持输出创建确认摘要。
  - [x] 暂不绑定交互问答，先支持脚本参数与 JSON 输入。
- [x] 测试目标：
  - [x] 覆盖最小合法任务创建、缺失必填字段报错、重复任务名处理。
- [x] 验收命令：

```sh
python active-jira-automation/scripts/manage_tasks.py create --help
python -m unittest discover active-jira-automation/tests -p 'test_manage_tasks.py'
```

- [x] 阻塞项：
  - [x] 群名到 `chat_id` 的解析策略尚未落地。
- [x] 解阻条件：
  - [x] 首期先要求 `create` 阶段传入稳定 `target_chat_id`，群名解析后补。

## 7. P3 通用执行引擎与调度适配

### P3.1 实现查询窗口与检查点逻辑

- [ ] 代码目标：
  - [ ] 新增 `jira_query_runtime.py`。
  - [ ] 实现 `last_checkpoint`、当前执行时间、回看窗口的计算。
  - [ ] 支持无命中时仅更新检查点并退出。
- [ ] 测试目标：
  - [ ] 覆盖首次运行、正常续跑、回看窗口、防止漏数。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_jira_query_runtime.py'
```

- [ ] 阻塞项：
  - [ ] 首次运行的默认起点未明确。
- [ ] 解阻条件：
  - [ ] 冻结规则：首次运行由任务创建时间或显式开始时间决定。

### P3.2 实现统一 runner 骨架

- [ ] 代码目标：
  - [ ] 新增 `run_automation_task.py`。
  - [ ] 串起“读取任务 -> 读取场景 -> 查询 -> 去重 -> 按需调用 LLM -> 渲染 -> 发送 -> 回写结果”。
  - [ ] 支持 `--dry-run`。
- [ ] 测试目标：
  - [ ] 覆盖无命中路径、命中路径、未知任务、未知场景、场景执行异常。
- [ ] 验收命令：

```sh
python active-jira-automation/scripts/run_automation_task.py --help
python -m unittest discover active-jira-automation/tests -p 'test_run_automation_task.py'
```

- [ ] 阻塞项：
  - [ ] LLM runtime 和 delivery runtime 的接口尚未固定。
- [ ] 解阻条件：
  - [ ] 先定义最小接口：`summarize(matches) -> summaries`，`deliver(cards, target) -> result`。

### P3.3 实现调度适配层骨架

- [ ] 代码目标：
  - [ ] 新增 `scheduler_adapter.py`。
  - [ ] 定义 `create/pause/resume/delete/get_status` 统一接口。
  - [ ] 首期提供 Openclaw 占位实现或 mock 实现。
- [ ] 测试目标：
  - [ ] 覆盖接口调用路径和错误封装，不要求首期真实连通 Openclaw。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_scheduler_adapter.py'
```

- [ ] 阻塞项：
  - [ ] Openclaw 真接口未冻结。
- [ ] 解阻条件：
  - [ ] 先在适配层抽象接口，真实联调延后到 P6。

## 8. P4 Interactive 卡片投递链路

### P4.1 实现通用 interactive 卡片渲染器

- [ ] 代码目标：
  - [ ] 新增 `renderers/interactive_card_renderer.py`。
  - [ ] 提供 `config/header/elements` 基础结构校验。
  - [ ] 限制允许组件白名单。
- [ ] 测试目标：
  - [ ] 覆盖合法 payload、缺失 `header`、空 `elements`、非法 tag、字段转义。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_interactive_card_renderer.py'
```

- [ ] 阻塞项：
  - [ ] 飞书 interactive card 的最终字段边界需要进一步验证。
- [ ] 解阻条件：
  - [ ] 首期只支持设计文档中已冻结的组件子集：`header/div/fields/hr/note/action`。

### P4.2 实现飞书投递 runtime

- [ ] 代码目标：
  - [ ] 新增 `lark_delivery_runtime.py`。
  - [ ] 负责序列化 interactive card、生成幂等键、执行 `--dry-run`、调用 `active-lark` raw API fallback。
  - [ ] 记录发送结果。
- [ ] 测试目标：
  - [ ] 覆盖 dry-run、不合法 payload 拒发、幂等键生成、发送目标参数装配。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_lark_delivery_runtime.py'
```

- [ ] 阻塞项：
  - [ ] 飞书发送命令的最终封装方式未定。
- [ ] 解阻条件：
  - [ ] 首期直接调用 raw API fallback，后续可替换底层实现但保持 runtime 接口不变。

### P4.3 实现 LLM 摘要 runtime

- [ ] 代码目标：
  - [ ] 新增 `llm_summary_runtime.py`。
  - [ ] 仅在命中后按批量调用，输出 `symptom_summary/impact_summary`。
  - [ ] 提供不可用时的降级逻辑。
- [ ] 测试目标：
  - [ ] 覆盖无命中不调用、合法 schema、字段缺失降级、异常降级。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_llm_summary_runtime.py'
```

- [ ] 阻塞项：
  - [ ] 首期 LLM 调用通道未定。
- [ ] 解阻条件：
  - [ ] 先抽象 runtime 接口并用 stub/mocked provider 完成测试。

## 9. P5 场景一接入

### P5.1 实现场景一接入模块

- [ ] 代码目标：
  - [ ] 新增 `scripts/scenarios/new_p0_bug_alert.py`。
  - [ ] 实现 `config_schema/defaulting_rules/query_builder/result_normalizer/match_identity/llm_output_schema`。
- [ ] 测试目标：
  - [ ] 覆盖 `P0 + Bug` 默认规则、字段归一化、去重键生成、字段缺失兜底前置处理。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_new_p0_bug_alert.py'
```

- [ ] 阻塞项：
  - [ ] Jira 字段路径未完全确认。
- [ ] 解阻条件：
  - [ ] 先支持配置化字段路径，默认值用当前文档冻结规则。

### P5.2 实现场景一卡片模板

- [ ] 代码目标：
  - [ ] 新增 `templates/lark_p0_bug_card_v1.py`。
  - [ ] 按设计文档输出固定结构的 interactive card JSON。
  - [ ] 实现字段长度裁剪与空值兜底。
- [ ] 测试目标：
  - [ ] 覆盖完整字段、缺失责任人、缺失 Team、缺失 FixVersion、超长 Summary、LLM 摘要缺失。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_lark_p0_bug_card_v1.py'
```

- [ ] 阻塞项：
  - [ ] 真实飞书客户端展示效果尚未验证。
- [ ] 解阻条件：
  - [ ] 先通过本地 payload 校验与 dry-run，联调阶段再做真机验证。

### P5.3 串通场景一 create -> run 最小闭环

- [ ] 代码目标：
  - [ ] 让 `manage_tasks.py create` 能创建 `new-p0-bug-alert` 任务。
  - [ ] 让 `run_automation_task.py --task-id <ID> --dry-run` 能跑通无命中与命中两条路径。
- [ ] 测试目标：
  - [ ] 增加集成测试覆盖“创建任务 -> 执行 runner -> 输出结果”。
- [ ] 验收命令：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_integration_new_p0_bug_alert.py'
python active-jira-automation/scripts/run_automation_task.py --task-id demo-task --dry-run
```

- [ ] 阻塞项：
  - [ ] 需要样例 Jira 输入数据和样例飞书输出 payload。
- [ ] 解阻条件：
  - [ ] 先准备本地 fixture JSON，避免一开始依赖真实外部系统。

## 10. P6 文档、联调与验收

### P6.1 补齐 README 与 Skill 使用说明

- [ ] 代码目标：
  - [ ] 在 README 中新增 `active-jira-automation` 能力说明。
  - [ ] 补充安装后如何触发 create/list/pause/resume/delete 的用法示例。
- [ ] 测试目标：
  - [ ] 文档能支撑首次试用，不依赖口头说明。
- [ ] 验收命令：

```sh
rg -n "active-jira-automation|new-p0-bug-alert|interactive" README.md active-jira-automation/SKILL.md
```

- [ ] 阻塞项：
  - [ ] 真实命令行参数形态需要以前几个阶段的实现为准。
- [ ] 解阻条件：
  - [ ] README 最后补，避免前期命令漂移导致文档失真。

### P6.2 完成端到端 dry-run 联调

- [ ] 代码目标：
  - [ ] 跑通“创建任务 -> 调度占位 -> runner 执行 -> interactive card dry-run 输出”的闭环。
  - [ ] 记录关键样例命令与预期输出。
- [ ] 测试目标：
  - [ ] 至少验证一次无命中路径和一次命中路径。
- [ ] 验收命令：

```sh
python active-jira-automation/scripts/manage_tasks.py create --scenario new-p0-bug-alert --project GENEVA --query-rule 'P0 + Bug' --schedule-type recurring --schedule-expr '0 * * * *' --target-chat-id oc_demo
python active-jira-automation/scripts/run_automation_task.py --task-id <TASK_ID> --dry-run
```

- [ ] 阻塞项：
  - [ ] 真实外部系统联调可能尚未完成。
- [ ] 解阻条件：
  - [ ] 先以 fixture + dry-run 完成端到端，真实系统联调后补最后一轮验证。

### P6.3 形成首期验收清单

- [ ] 代码目标：
  - [ ] 将框架文档和场景文档中的首期验收标准收敛成一份执行清单。
  - [ ] 标记已满足、待验证、受阻项。
- [ ] 测试目标：
  - [ ] 验收清单能直接用于发布前 review。
- [ ] 验收命令：

```sh
rg -n "首期落地范围|验收标准" doc/active-jira-automation\ 框架能力设计.md doc/active-jira-automation\ 定时查询P0并提醒场景设计.md doc/active-jira-automation-todo.md
```

- [ ] 阻塞项：
  - [ ] 若中途扩大范围，验收标准会失焦。
- [ ] 解阻条件：
  - [ ] 发布前只按 P0-P6 已冻结范围验收，不临时加需求。

## 11. 当前建议执行顺序

建议严格按以下顺序推进，不跳步：

1. P0.1 -> P0.2 -> P1.1
2. P1.2 -> P1.3 -> P2.1
3. P2.2 -> P2.3 -> P3.1
4. P3.2 -> P3.3 -> P4.1
5. P4.2 -> P4.3 -> P5.1
6. P5.2 -> P5.3 -> P6.1
7. P6.2 -> P6.3

原因：

- 先冻结边界，再建骨架。
- 先有任务模型，再有 runner。
- 先有通用渲染与投递，再接具体场景模板。
- 先完成 dry-run 闭环，再进入真实联调。

## 12. 当前显式阻塞项

P0 已完成。进入实现阶段后，仍需要提前关注以下阻塞：

1. Openclaw 的真实接口、鉴权方式和错误码如何映射到 `scheduler_adapter.py`。
2. 目标项目中 `来源` 字段的具体读取路径仍需要业务侧或真实 Jira 数据确认。
3. 若单次命中 Jira 数量较大，是否需要分批发送、上限控制或折叠策略。

建议在进入 P3 和 P6 之前优先收敛这 3 个实现期阻塞。
