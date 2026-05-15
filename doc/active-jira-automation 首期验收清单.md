# active-jira-automation 首期验收清单

## 1. 文档目标

本文将以下两份设计文档中的首期约束收敛成一份发布前 review 清单：

- [active-jira-automation 框架能力设计](./active-jira-automation%20框架能力设计.md)
- [active-jira-automation 定时查询并提醒场景设计](./active-jira-automation%20定时查询并提醒场景设计.md)

适用范围限定为首期场景 `jira-scheduled-query-alert`，目标是确认框架公共能力、场景接入、fixture/dry-run 验收链路和外部联调前置条件已经收敛到可执行状态。

## 2. Design -> Acceptance 映射

| 设计来源 | 首期要求 | 对应验收证据 |
| --- | --- | --- |
| 框架文档 `13. 首期落地范围` | 单场景接入能力 | `test_scenario_registry.py`、`test_jira_scheduled_query_alert.py` |
| 框架文档 `13. 首期落地范围` | 单任务创建、列出、暂停、恢复、删除 | `test_manage_tasks.py` |
| 框架文档 `13. 首期落地范围` | 统一 runner 与检查点机制 | `test_run_automation_task.py` |
| 框架文档 `13. 首期落地范围` | interactive 卡片渲染、校验与发送 dry-run | `test_interactive_card_renderer.py`、`test_lark_delivery_runtime.py` |
| 场景文档 `12. 场景一验收标准` | 筛选条件不限于 P0 Bug | `test_jira_scheduled_query_alert.py`、`test_end_to_end_acceptance.py` |
| 场景文档 `12. 场景一验收标准` | 创建期确认 `base_jql/query_spec/window_mode` | `test_manage_tasks.py`、`test_end_to_end_acceptance.py` |
| 场景文档 `12. 场景一验收标准` | 无命中零 LLM/零发送，有命中后受控摘要和卡片 | `test_run_automation_task.py` |

## 3. 可执行回归命令

自动回归：

```sh
python -m unittest discover active-jira-automation/tests -p 'test_manage_tasks.py'
python -m unittest discover active-jira-automation/tests -p 'test_run_automation_task.py'
python -m unittest discover active-jira-automation/tests -p 'test_end_to_end_acceptance.py'
```

手工 smoke：

```sh
TMPDIR="$(mktemp -d)"
python active-jira-automation/scripts/manage_tasks.py create \
  --data-root "$TMPDIR" \
  --scenario jira-scheduled-query-alert \
  --task-name "Geneva P0 Bug Alert" \
  --project GENEVA \
  --filter-prompt "每小时查询一次 GENEVA 新增的 P0 Bug" \
  --base-jql 'project = GENEVA AND issuetype = Bug AND "Severity" = P0' \
  --query-spec-json '{"projects":["GENEVA"],"clauses":[{"field":"issuetype","op":"=","value":"Bug"},{"field":"Severity","op":"=","value":"P0"}]}' \
  --window-mode created \
  --schedule-type recurring \
  --schedule-expr '0 * * * *' \
  --target-chat-id oc_demo \
  --dry-run

python active-jira-automation/scripts/manage_tasks.py create \
  --data-root "$TMPDIR" \
  --scenario jira-scheduled-query-alert \
  --task-name "Geneva P0 Bug Alert" \
  --project GENEVA \
  --filter-prompt "每小时查询一次 GENEVA 新增的 P0 Bug" \
  --base-jql 'project = GENEVA AND issuetype = Bug AND "Severity" = P0' \
  --query-spec-json '{"projects":["GENEVA"],"clauses":[{"field":"issuetype","op":"=","value":"Bug"},{"field":"Severity","op":"=","value":"P0"}]}' \
  --window-mode created \
  --schedule-type recurring \
  --schedule-expr '0 * * * *' \
  --target-chat-id oc_demo

python active-jira-automation/scripts/run_automation_task.py "Geneva P0 Bug Alert" \
  --data-root "$TMPDIR" \
  --fixture-json active-jira-automation/tests/fixtures/jira_query_results.json \
  --dry-run
```

## 4. 发布前检查清单

| 检查项 | 当前状态 | 验证方式 | 说明 |
| --- | --- | --- | --- |
| 单场景 `jira-scheduled-query-alert` 已注册并可执行 | 已满足 | `test_scenario_registry.py`、`test_jira_scheduled_query_alert.py` | 场景注册表已切到通用查询提醒 |
| 任务生命周期 `create/list/pause/resume/delete` 可用 | 已满足 | `test_manage_tasks.py` | 新增 `create --dry-run` 预演能力 |
| runner 支持 `created/updated/snapshot`、去重、检查点和上限截断 | 已满足 | `test_run_automation_task.py` | fixture 与 dry-run 路径均可回归 |
| P0 Bug 只作为任务配置样例，不是场景硬编码 | 已满足 | `test_jira_scheduled_query_alert.py`、`test_end_to_end_acceptance.py` | 模块源码和端到端样例均已覆盖 |
| 非 P0、非 Bug 查询可复用同一场景模块 | 已满足 | `test_jira_scheduled_query_alert.py`、`test_end_to_end_acceptance.py` | 已覆盖 `assignee IS EMPTY`、`labels`、`status = Open` |
| interactive 卡片渲染和投递 dry-run 可用 | 已满足 | `test_interactive_card_renderer.py`、`test_lark_delivery_runtime.py` | 仍保持公共白名单校验 |
| 真实 JiraCLI 查询联调 | 待验证 | 手工 smoke + `--jira-bin jira` | 需要目标环境已完成 `jira init` |
| 真实飞书群发送联调 | 待验证 | 手工 smoke 去掉 `--dry-run` | 需要可用机器人权限和真实 `target_chat_id` |

## 5. 受阻项与解阻条件

| 受阻项 | 原因 | 解阻条件 |
| --- | --- | --- |
| 真实 Jira/Lark 联调尚未在仓库回归内执行 | 当前仓库验收以 fixture + dry-run 为主，避免引入外部副作用和凭证依赖 | 在联调环境准备可用 `jira` 命令、机器人权限和目标 `chat_id`，再执行真实 smoke |
| `snapshot` 模式重复提醒策略未做产品侧二次确认 | 设计文档保留 `repeat_snapshot` 开关，但首期默认只首次提醒 | 产品确认是否允许周期性重复播报；若允许，再补充对应验收用例 |

## 6. 当前结论

首期本地可重复验收链路已经闭环：创建预演、任务落盘、fixture 命中、runner dry-run、卡片渲染和非 P0 复用都已有自动回归覆盖。剩余工作主要是外部环境联调，不再是框架内代码阻塞。