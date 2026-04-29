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
python active-jira/scripts/query_stale_jiras.py --project <PROJECT> --age <AGE>
```

2. 报告中必须保留脚本生成或实际执行的查询信息，包括查询时间、命令、项目、超时时间、生成的 JQL。需要确认 JQL 时先执行：

```bash
python active-jira/scripts/query_stale_jiras.py --project <PROJECT> --age <AGE> --dry-run
```

3. 若脚本输出字段不足以满足报告要求，应对命中的 Jira 逐条补充详情：

```bash
jira issue view <ISSUE-KEY> --raw
jira issue view <ISSUE-KEY> --comments 5
```

4. 补充详情时只读取报告必需字段：Jira 编号、创建时间、责任人、状态、Severity/Priority、Summary、Description 摘要、最近评论。不要创建、修改、流转、评论或分配 Jira，除非用户明确要求。
5. 若 JiraCLI 查询失败，应在输出中说明失败命令和失败原因，并优先给出可复制执行的 JQL/命令，不要编造结果。

#### 数据处理规则
1. 查询时间使用执行时本地时间，报告中以 `YYYY-MM-DD HH:mm:ss <timezone>` 记录。
2. 超期时长按 `查询时间 - 创建时间` 计算，单位为天，保留 1 位小数；排序比较时使用原始数值。
3. 紧急程度优先读取 Jira 的 `Severity` 字段；若没有 Severity，则读取 `Priority`；两者都没有时标记为 `未设置`。
4. Severity 排序优先级为 `P0 > P1 > P2 > P3 > P4 > 未设置/未知`。如果字段值是 `Blocker/Critical/High/Medium/Low` 等非 P 级别，应保留原值，并按项目已有映射或 Jira priority 顺序排序；无法映射时放在 `未知` 分组。
5. Jira 摘要优先使用 `Summary`；问题描述摘要可从 `Description` 中提炼 1 句，不超过 80 个中文字符。没有描述时使用 `Summary` 补足。
6. 评论摘要为可选项：当用户明确要求、问题数量较少，或评论中包含阻塞/等待/需要确认等明显风险信息时输出；否则列为 `-`。

#### 输出规则
1. 默认输出 Markdown 报告，结构固定为：
- 标题：`<PROJECT> 长期未处理 Jira 报告`
- 查询信息：查询时间、项目、超时时间、命令、JQL
- 汇总：总数、最高紧急程度、最久未处理 Jira、未分配数量
- Jira 清单表格
- 可选：风险说明/建议行动
2. Jira 清单表格必须包含以下列：

| 排序 | Jira | Severity/紧急程度 | 创建时间 | 超期时长(天) | 状态 | 责任人 | 问题摘要 | 评论摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

3. Jira 清单排序规则：
- 第一排序：紧急程度，`P0` 最靠前。
- 第二排序：创建时间，越早创建越靠前。
- 第三排序：Jira Key 字典序，保证输出稳定。
4. Jira 编号应尽量输出为可点击链接；若无法获取 Jira base URL，则只输出 Key。
5. 如果没有满足条件的 Jira，仍输出查询信息、汇总和空表，并明确写明“未查询到满足条件的 Jira”。
6. 报告内容应区分事实与判断：表格只放 Jira 原始事实和明确计算值；紧急程度评估、风险和建议放在汇总或建议行动中。
