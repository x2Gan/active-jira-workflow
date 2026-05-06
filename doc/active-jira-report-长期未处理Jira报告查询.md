# Active Jira Report 需求：长期未处理Jira报告查询

## - 长期未处理Jira报告查询 @Dean ZHANG

### 需求整理
1. 场景：帮我查询GENEVA项目超过1周未处理的Jira情况
2. 规则：帮我查询[项目名称]项目超过[超时时间]未处理的Jira情况
3. 要求：
- 输出满足要求的Jira的清单表格，可以是Markdown文档
- 文档包含查询的命令、时间等信息
- 每个Jira单项必须包含Jira编号、创建时间、责任人、超期时长（创建时间到查询时间的时长（天））、Jira描述的问题摘要/总结
- 每个Jira单项可选包含该Jira的评论摘要
- 对每个Jira进行紧急程度评估：参考Jira中的Severity字段，P0表示最紧急
- Jira清单按照紧急程度排序输出，最紧急考前显示，相同紧急程度创建时间越早越靠前

### SKILL规则

#### 触发与参数识别
1. 当用户提出“长期未处理 Jira”“超过 N 天/周/月未处理”“stale issue”“未关闭超期 Jira”等需求时，使用 `active-jira-report` 的长期未处理 Jira 报告规则。
2. 从用户输入中提取：
- `project`：Jira 项目 Key，例如 `GENEVA`；未给出时先使用当前 JiraCLI 默认项目，无法确认时询问用户。
- `age`：超时时间，例如 `7d`、`1w`、`14d`、`1mo`、`30天`；`1周`按 7 天计算，`1月/1mo`按 30 天计算。
- 可选过滤条件：责任人、状态、组件、版本、标签或用户额外给出的 JQL 条件。
3. “未处理”默认定义为：创建时间早于超时阈值，且未关闭/未完成。GENEVA 默认采用 `status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved`；其他项目优先使用项目现有状态规范，无法确认时使用 `status not in (Closed) AND resolution = Unresolved`。

#### 查询规则
1. 优先使用已有脚本生成并执行基础查询：

```bash
python active-jira-report/scripts/generate_stale_jira_report.py --project <PROJECT> --age <AGE>
```

Agent 正常执行时优先使用 `--output <REPORT_PATH>` 写入本地 Markdown 文件，便于后续飞书发布复用同一份报告。

2. 报告中必须保留脚本生成或实际执行的查询信息，包括查询时间、命令、项目、超时时间、生成的 JQL。需要确认 JQL 时先执行：

```bash
python active-jira-report/scripts/generate_stale_jira_report.py --project <PROJECT> --age <AGE> --dry-run
```

3. 当 Markdown 报告成功生成到本地文件后，Agent 应主动询问是否继续创建飞书云文档并发送到指定群组：

```text
报告已生成：<REPORT_PATH>。需要我继续创建飞书云文档并发送到指定群组吗？如果需要，请告诉我群名或 oc_... 群 ID。
```

用户确认后，优先复用已经生成的 Markdown 文件，不重复查询 Jira：

```bash
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py \
  --project <PROJECT> \
  --age <AGE> \
  --report-input <REPORT_PATH>
```

4. 若脚本输出字段不足以满足报告要求，应对命中的 Jira 逐条补充详情：

```bash
jira issue view <ISSUE-KEY> --raw
jira issue view <ISSUE-KEY> --comments 5
```

5. 补充详情时只读取报告必需字段：Jira 编号、创建时间、责任人、状态、Severity/Priority、Summary、Description 摘要、最近评论。不要创建、修改、流转、评论或分配 Jira，除非用户明确要求。
6. 若 JiraCLI 查询失败，应在输出中说明失败命令和失败原因，并优先给出可复制执行的 JQL/命令，不要编造结果。

#### 数据处理规则
1. 查询时间使用执行时本地时间，报告中以 `YYYY-MM-DD HH:mm:ss <timezone>` 记录。
2. 超期时长按 `查询时间 - 创建时间` 计算，单位为天，保留 1 位小数；排序比较时使用原始数值。
3. 紧急程度优先读取 Jira 的 `Severity` 字段；若没有 Severity，则读取 `Priority`；两者都没有时标记为 `未设置`。
4. Severity 排序优先级为 `P0 > P1 > P2 > P3 > P4 > 未设置/未知`。如果字段值是 `Blocker/Critical/High/Medium/Low` 等非 P 级别，应保留原值，并按项目已有映射或 Jira priority 顺序排序；无法映射时放在 `未知` 分组。
5. Jira 摘要优先使用 `Summary`；问题描述摘要可从 `Description` 中提炼 1 句，不超过 80 个中文字符。没有描述时使用 `Summary` 补足。
6. 完整 Jira 清单必须按照 `归属Team` 分组展示。`归属Team` 优先读取脚本配置的 team 字段、常见字段名和 `customfield_11801`；字段不存在或为空时标记为 `未设置`。这些值只作为已有 Jira 的报告事实展示，不作为创建/编辑 Jira 时的自动填写枚举。
7. 评论摘要为可选项：当用户明确要求、问题数量较少，或评论中包含阻塞/等待/需要确认等明显风险信息时输出；否则列为 `-`。
8. Highlight 用于帮助 PM/PL 快速识别最应该立即修复或确认责任人的 Jira。Highlight 放在查询信息之后、完整 Jira 清单之前；选择逻辑按综合风险排序：紧急程度优先，其次状态风险（`Reopened`、`Open`、`In Progress`、`Pending`、`Resolved`、`In Review`），再考虑是否未分配责任人和超期天数。每条 Highlight 必须给出一句简短推荐理由。

#### 输出规则
1. 默认输出 Markdown 报告，结构固定为：
- 标题：`<PROJECT> 长期未处理 Jira 报告`
- 查询信息：查询时间、项目、超时时间、命令、JQL
- 开头 Highlight：Agent 综合分析后认为最应该立即修复或确认责任人的 Jira List 简要，面向 PM/PL 快速汇报
- Jira 清单按 `归属Team` 分组展示；每组先给必要统计，再列出归属该组的所有 Jira
- 文档末尾汇总：总数、状态分布、紧急程度分布、未分配数量、最久未处理 Jira、责任人数量 Top 5、最久未处理 Top 5、评论抓取策略、紧急程度字段来源和归属Team字段来源
- 可选：风险说明/建议行动
2. Highlight 表格必须包含以下列：

| Jira | 紧急程度 | 超期天数 | 状态 | 责任人 | 推荐理由 | 摘要 |
| --- | --- | --- | --- | --- | --- | --- |

3. 每个 `归属Team` 分组必须包含必要统计信息：
- 数量
- 状态分布
- 紧急程度分布
- 未分配责任人数量
- 平均超期天数
- 最久未处理 Jira
- 责任人 Top 3
4. 每个 `归属Team` 分组下的 Jira 清单表格必须包含以下列：

| 排序 | Jira | Severity/紧急程度 | 创建时间 | 超期时长(天) | 状态 | 责任人 | 问题摘要 | 评论摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

5. Jira 清单排序规则：
- 第一排序：紧急程度，`P0` 最靠前。
- 第二排序：创建时间，越早创建越靠前。
- 第三排序：Jira Key 字典序，保证输出稳定。
6. Jira 编号应尽量输出为可点击链接；若无法获取 Jira base URL，则只输出 Key。
7. 如果没有满足条件的 Jira，仍输出查询信息、Highlight、汇总和空表，并明确写明“未查询到满足条件的 Jira”。
8. 报告内容应区分事实与判断：完整 Jira 清单只放 Jira 原始事实和明确计算值；Highlight 的推荐理由可以包含基于紧急程度、状态、未分配和超期天数的判断，但必须可追溯到表格字段。
9. 文档末尾汇总格式固定为：

```markdown
## 汇总

总数: <count>
状态分布: <status count list>
紧急程度: <urgency count list>
未分配: <count>
最久未处理: <issue key>，<days> 天

### 责任人数量 Top 5

| 责任人 | 数量 |
| --- | --- |

### 最久未处理 Top 5

| Jira | 紧急程度 | 超期天数 | 状态 | 责任人 | 摘要 |
| --- | --- | --- | --- | --- | --- |

<评论抓取策略>；紧急程度来源: <Severity/Priority 字段来源>；归属Team来源: <team 字段来源>。
```

10. 状态分布按数量降序输出；紧急程度分布按 Jira 紧急程度排序输出；责任人 Top 5 不包含 `Unassigned`，未分配数量单独由“未分配”字段体现；最久未处理 Top 5 按超期天数降序输出。
