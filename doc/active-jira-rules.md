# Active Jira 规则文档

本文档固化 Active Jira 工作流当前可用的字段名、字段 ID、必填规则和枚举值，供 Agent 创建、编辑、查询和汇总 Jira 时直接使用。由于 `doc/` 目录对 SKILL 运行时不可见，本规则被同步复制到两个 SKILL 的 `references/` 目录。

## 适用范围

- Jira server: `https://jira.huami.com`
- 适用范围: Active Jira 项目通用规则。
- 项目 key 由用户请求、上下文或 Jira 配置决定；创建和查询时必须显式或可追溯地确定 `project`。
- 核心规则: 自定义字段必须使用字段 ID；不要编造别名，也不要把 raw-only/legacy 字段用于创建或编辑。

## 快速规则

- 创建或查询时必须使用用户指定或上下文明确的 `project`；不要默认固定为任何单一项目。
- Valid issue types: Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task
- Use `customfield_10401` for Severity. Allowed values: P0, P1, P2, P3.
- Use `customfield_10800` for Products in create/edit flows. `customfield_11400` is only an observed raw/legacy field from existing issues.
- Use `customfield_10716` for 问题概率 in create/edit flows. `customfield_10312` is only an observed raw/legacy field from existing issues.
- `status` and `resolution` are workflow fields. Move/transition issues instead of setting them as ordinary create custom fields.
- `components`、`versions`、`fixVersions`、`status` 等可能受项目配置影响；若目标项目与本文档枚举不一致、Jira 拒绝字段值，或用户要求刷新，则按目标项目重新读取 Jira metadata。
- User fields such as `assignee`, `reporter`, and `customfield_10304` do not have static enumerations; resolve users by Jira username/display name/email through Jira user search or CLI assignment semantics.
- Free text / date / attachment / link fields have no enumerations; validate by type and only fill when the user provided content or a project rule clearly applies.

## 动态字段查询规则

以下字段不固化枚举值。它们的合法值可能随项目、issue type、工作流、版本配置或用户权限变化；需要在读取已有 Jira 或创建新 Jira 前动态查询。

查询脚本采用 CLI-first 策略：已有 Jira 和项目列表优先调用本地 `jira` CLI；只有新建前的字段合法值、工作流状态等 JiraCLI 未提供稳定命令的元数据查询，才读取 Jira REST metadata。

| 字段 | 字段 ID | 动态原因 | 查询方法 |
| --- | --- | --- | --- |
| Project | `project` | 项目列表随权限和组织配置变化 | `python active-jira/scripts/query_jira_field_options.py projects --match <keyword>` |
| Status | `status` | 状态受项目工作流和 issue type 影响 | `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields status` |
| Component/s | `components` | 组件是项目级配置 | `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields components --match <keyword>` |
| Affects Version/s | `versions` | 版本是项目级配置 | `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields versions --match <keyword>` |
| Fix Version/s | `fixVersions` | 修复版本是项目级配置 | `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields fixVersions --match <keyword>` |
| Products | `customfield_10800` | 产品选项可能按项目/上下文变化 | `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields customfield_10800 --match <keyword>` |
| 规划版本 | `customfield_12700` | 规划版本来自项目版本配置 | `python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type <TYPE> --fields customfield_12700 --match <keyword>` |
| Assignee / Reporter / Follower | `assignee` / `reporter` / `customfield_10304` | 用户集合随权限、项目角色和账号状态变化 | 通过 Jira 用户搜索、`jira issue assign`、`jira issue create -a/-r` 或已有 Jira raw 数据确认 |
| Parent / Epic Link | `parent` / `customfield_10101` | 关联目标必须来自真实存在且可见的 Jira | 先用 JQL 或 `jira issue view <KEY> --raw` 确认目标 Jira |

常用只读查询：

```bash
python active-jira/scripts/query_jira_field_options.py issue <ISSUE-KEY> --fields project,versions,fixVersions,customfield_10800,customfield_12700,status
```

常用新建前匹配：

```bash
python active-jira/scripts/query_jira_field_options.py create --project <PROJECT> --issue-type Bug --fields versions,fixVersions,customfield_10800,customfield_12700 --match <keyword>
```

## 字段分类

- 身份与流程: `Status` / `status`; `Summary` / `summary`; `Security Level` / `security`; `Issue Type` / `issuetype`; `Project` / `project`; `Resolution` / `resolution`; `Parent` / `parent`
- 人员协作: `Reporter` / `reporter`; `Assignee` / `assignee`; `Follower` / `customfield_10304`; `Creator` / `creator`
- 优先级与风险: `Severity` / `customfield_10401`; `Priority` / `priority`
- 产品、版本与组件: `Products` / `customfield_10800`; `规划版本` / `customfield_12700`; `Component/s` / `components`; `Affects Version/s` / `versions`; `Fix Version/s` / `fixVersions`; `Products (GT3)` / `customfield_11400`
- 缺陷定位与根因: `原因分类` / `customfield_12005`; `问题概率(problem probability)` / `customfield_10716`; `研发验证结果` / `customfield_12003`; `发现问题阶段(Problem discovery stage)` / `customfield_11000`; `RootCause Analysis` / `customfield_11002`; `Reopen原因分类` / `customfield_12400`; `Root Cause` / `customfield_10902`; `报修平台(Repair platform)` / `customfield_10404`; `引入问题阶段` / `customfield_11001`; `改进措施` / `customfield_12002`; `复现概率` / `customfield_10312`
- 计划、时间与集成: `测试轮次` / `customfield_12300`; `Gerrit_Url` / `customfield_11200`; `Start date` / `customfield_10702`; `SYNC_ISSUE` / `customfield_10720`; `Integration` / `customfield_11401`; `Time Tracking` / `timetracking`; `Due Date` / `duedate`
- 文本、附件与链接: `Epic Link` / `customfield_10101`; `Epic Name` / `customfield_10103`; `Comment` / `comment`; `Description` / `description`; `Attachment` / `attachment`; `Environment` / `environment`; `Status whiteboard` / `customfield_10717`; `Labels` / `labels`; `Log Work` / `worklog`; `详细描述` / `customfield_10513`; `Linked Issues` / `issuelinks`
- 审计只读: `Updated` / `updated`; `Resolution Date` / `resolutiondate`; `Created` / `created`

## 不同 Jira 类型的必填/选填规则

| Jira 类型 | 必填字段 | 可选创建字段 | 合法状态 |
| --- | --- | --- | --- |
| Epic | Summary / `summary`, Issue Type / `issuetype`, Severity / `customfield_10401`, Epic Name / `customfield_10103`, Security Level / `security`, Project / `project` | Priority / `priority`, Fix Version/s / `fixVersions`, Component/s / `components`, Start date / `customfield_10702`, Due Date / `duedate`, Time Tracking / `timetracking`, Linked Issues / `issuelinks`, Gerrit_Url / `customfield_11200`, Description / `description`, Integration / `customfield_11401`, Epic Link / `customfield_10101`, Products / `customfield_10800`, Labels / `labels`, SYNC_ISSUE / `customfield_10720`, Status whiteboard / `customfield_10717`, 归属Team(Ownership Team) / `customfield_11801`, Affects Version/s / `versions`, 测试轮次 / `customfield_12300`, 规划版本 / `customfield_12700`, Assignee / `assignee` | Open, In Progress, In Review, Closed |
| Meeting | Summary / `summary`, Issue Type / `issuetype`, Security Level / `security`, Project / `project` | Start date / `customfield_10702`, Due Date / `duedate`, Time Tracking / `timetracking`, Description / `description`, Log Work / `worklog`, Fix Version/s / `fixVersions`, Labels / `labels`, Assignee / `assignee` | Open, Closed |
| Task | Summary / `summary`, Issue Type / `issuetype`, Severity / `customfield_10401`, Security Level / `security`, Project / `project` | Priority / `priority`, Fix Version/s / `fixVersions`, Component/s / `components`, Start date / `customfield_10702`, Due Date / `duedate`, Time Tracking / `timetracking`, Linked Issues / `issuelinks`, Gerrit_Url / `customfield_11200`, Description / `description`, Integration / `customfield_11401`, Epic Link / `customfield_10101`, Products / `customfield_10800`, Labels / `labels`, SYNC_ISSUE / `customfield_10720`, Status whiteboard / `customfield_10717`, 归属Team(Ownership Team) / `customfield_11801`, Affects Version/s / `versions`, 测试轮次 / `customfield_12300`, 规划版本 / `customfield_12700`, Assignee / `assignee` | Open, In Progress, Resolved, Closed, Reopened, Pending |
| Bug | Summary / `summary`, Issue Type / `issuetype`, Severity / `customfield_10401`, 报修平台(Repair platform) / `customfield_10404`, 发现问题阶段(Problem discovery stage) / `customfield_11000`, Security Level / `security`, Project / `project` | Priority / `priority`, Fix Version/s / `fixVersions`, Affects Version/s / `versions`, 详细描述 / `customfield_10513`, Labels / `labels`, Environment / `environment`, Attachment / `attachment`, Linked Issues / `issuelinks`, Component/s / `components`, Start date / `customfield_10702`, Due Date / `duedate`, 问题概率(problem probability) / `customfield_10716`, Gerrit_Url / `customfield_11200`, Log Work / `worklog`, Time Tracking / `timetracking`, Integration / `customfield_11401`, Epic Link / `customfield_10101`, Products / `customfield_10800`, Follower / `customfield_10304`, 引入问题阶段 / `customfield_11001`, RootCause Analysis / `customfield_11002`, SYNC_ISSUE / `customfield_10720`, Description / `description`, Status whiteboard / `customfield_10717`, 归属Team(Ownership Team) / `customfield_11801`, 原因分类 / `customfield_12005`, 改进措施 / `customfield_12002`, 研发验证结果 / `customfield_12003`, Reopen原因分类 / `customfield_12400`, 规划版本 / `customfield_12700`, Assignee / `assignee` | Open, In Progress, Resolved, Closed, Reopened, Pending |
| Improvement | Summary / `summary`, Issue Type / `issuetype`, Severity / `customfield_10401`, Security Level / `security`, Project / `project` | Priority / `priority`, Fix Version/s / `fixVersions`, Component/s / `components`, Start date / `customfield_10702`, Due Date / `duedate`, Time Tracking / `timetracking`, Linked Issues / `issuelinks`, Gerrit_Url / `customfield_11200`, Description / `description`, Integration / `customfield_11401`, Epic Link / `customfield_10101`, Products / `customfield_10800`, Labels / `labels`, SYNC_ISSUE / `customfield_10720`, Status whiteboard / `customfield_10717`, 归属Team(Ownership Team) / `customfield_11801`, Affects Version/s / `versions`, 测试轮次 / `customfield_12300`, 规划版本 / `customfield_12700`, Assignee / `assignee` | Open, In Progress, Resolved, Closed, Reopened, Pending |
| New Feature | Summary / `summary`, Issue Type / `issuetype`, Severity / `customfield_10401`, Security Level / `security`, Project / `project` | Priority / `priority`, Fix Version/s / `fixVersions`, Component/s / `components`, Start date / `customfield_10702`, Due Date / `duedate`, Time Tracking / `timetracking`, Linked Issues / `issuelinks`, Gerrit_Url / `customfield_11200`, Description / `description`, Integration / `customfield_11401`, Epic Link / `customfield_10101`, Products / `customfield_10800`, Labels / `labels`, SYNC_ISSUE / `customfield_10720`, Status whiteboard / `customfield_10717`, 归属Team(Ownership Team) / `customfield_11801`, Affects Version/s / `versions`, 测试轮次 / `customfield_12300`, 规划版本 / `customfield_12700`, Assignee / `assignee` | Open, In Progress, Resolved, Closed, Reopened, Pending |
| Sub-task | Summary / `summary`, Issue Type / `issuetype`, Severity / `customfield_10401`, Security Level / `security`, Project / `project`, Parent / `parent` | Priority / `priority`, Fix Version/s / `fixVersions`, Component/s / `components`, Start date / `customfield_10702`, Due Date / `duedate`, Time Tracking / `timetracking`, Linked Issues / `issuelinks`, Gerrit_Url / `customfield_11200`, Description / `description`, Integration / `customfield_11401`, Epic Link / `customfield_10101`, Products / `customfield_10800`, Labels / `labels`, SYNC_ISSUE / `customfield_10720`, Status whiteboard / `customfield_10717`, 归属Team(Ownership Team) / `customfield_11801`, Affects Version/s / `versions`, 测试轮次 / `customfield_12300`, 规划版本 / `customfield_12700`, Assignee / `assignee` | Open, In Progress, Resolved, Closed, Reopened, Pending |

## 字段总表

| 分类 | 字段 | 字段 ID | 类型 | 出现范围 | 必填范围 | 枚举策略 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 身份与流程 | Issue Type | `issuetype` | issuetype | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | 1 | present in sampled Bug editmeta |
| 身份与流程 | Parent | `parent` | issuelink | Sub-task | Sub-task | 0 | - |
| 身份与流程 | Project | `project` | project | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | 动态查询 | 使用 `projects --match` 或上下文明确的项目 key；不要固化单个项目 |
| 身份与流程 | Resolution | `resolution` | resolution | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 0 | workflow outcome; normally set by transition, not direct create/edit |
| 身份与流程 | Security Level | `security` | securitylevel | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | 11 | present in sampled Bug editmeta |
| 身份与流程 | Status | `status` | workflow-status | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 动态查询 | 工作流字段；按目标项目和 issue type 查询，流转时使用 transition/move |
| 身份与流程 | Summary | `summary` | string | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | 0 | present in sampled Bug editmeta |
| 人员协作 | Assignee | `assignee` | user | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 人员协作 | Follower | `customfield_10304` | array/user | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 人员协作 | Reporter | `reporter` | user | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 0 | CLI supports -r/--reporter, but it is not in current sampled createmeta; set only when user asks and Jira permission allows |
| 优先级与风险 | Priority | `priority` | priority | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 5 | present in sampled Bug editmeta |
| 优先级与风险 | Severity | `customfield_10401` | option | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | 4 | present in sampled Bug editmeta |
| 产品、版本与组件 | Affects Version/s | `versions` | array/version | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 动态查询 | 项目级版本字段；创建前用查询脚本按目标项目/类型获取 |
| 产品、版本与组件 | Component/s | `components` | array/component | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 动态查询 | 项目级组件字段；创建前用查询脚本按目标项目/类型获取 |
| 产品、版本与组件 | Fix Version/s | `fixVersions` | array/version | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 动态查询 | 项目级版本字段；创建前用查询脚本按目标项目/类型获取 |
| 产品、版本与组件 | Products | `customfield_10800` | array/option | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 动态查询 | 产品选项不在规则中固化；创建前用查询脚本按目标项目/类型获取 |
| 产品、版本与组件 | Products (GT3) | `customfield_11400` | raw-observed | raw observed only | optional / not create-required | 0 | observed value: huamiOS (Kernel/Platform/Apps...); legacy/raw field; use Products/customfield_10800 for create/edit |
| 产品、版本与组件 | 规划版本 | `customfield_12700` | version | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 动态查询 | 项目级版本字段；创建前用查询脚本按目标项目/类型获取 |
| 缺陷定位与根因 | Reopen原因分类 | `customfield_12400` | option | Bug, Bug(edit screen) | optional / not create-required | 11 | present in sampled Bug editmeta |
| 缺陷定位与根因 | Root Cause | `customfield_10902` | raw-observed | raw observed only | optional / not create-required | 0 | observed value: Development; raw issue has value; not in sampled create/edit metadata |
| 缺陷定位与根因 | RootCause Analysis | `customfield_11002` | string | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 原因分类 | `customfield_12005` | option | Bug, Bug(edit screen) | optional / not create-required | 47 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 发现问题阶段(Problem discovery stage) | `customfield_11000` | option | Bug, Bug(edit screen) | Bug, Bug(edit screen) | 20 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 复现概率 | `customfield_10312` | raw-observed | raw observed only | optional / not create-required | 0 | observed value: 必现（100%）; legacy/raw field; use 问题概率/customfield_10716 for create/edit |
| 缺陷定位与根因 | 引入问题阶段 | `customfield_11001` | option | Bug, Bug(edit screen) | optional / not create-required | 5 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 报修平台(Repair platform) | `customfield_10404` | option | Bug, Bug(edit screen) | Bug, Bug(edit screen) | 17 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 改进措施 | `customfield_12002` | string | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 研发验证结果 | `customfield_12003` | string | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 缺陷定位与根因 | 问题概率(problem probability) | `customfield_10716` | option | Bug, Bug(edit screen) | optional / not create-required | 6 | present in sampled Bug editmeta |
| 计划、时间与集成 | Due Date | `duedate` | date | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 计划、时间与集成 | Gerrit_Url | `customfield_11200` | string | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 计划、时间与集成 | Integration | `customfield_11401` | option | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 2 | present in sampled Bug editmeta |
| 计划、时间与集成 | Start date | `customfield_10702` | date | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 计划、时间与集成 | SYNC_ISSUE | `customfield_10720` | string | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 计划、时间与集成 | Time Tracking | `timetracking` | timetracking | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 计划、时间与集成 | 测试轮次 | `customfield_12300` | option | Epic, Task, Improvement, New Feature, Sub-task | optional / not create-required | 8 | - |
| 文本、附件与链接 | Attachment | `attachment` | array/attachment | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Comment | `comment` | comments-page | Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Description | `description` | string | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Environment | `environment` | string | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Epic Link | `customfield_10101` | any | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Epic Name | `customfield_10103` | string | Epic | Epic | 0 | - |
| 文本、附件与链接 | Labels | `labels` | array/string | Epic, Meeting, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Linked Issues | `issuelinks` | array/issuelinks | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Log Work | `worklog` | array/worklog | Meeting, Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | Status whiteboard | `customfield_10717` | string | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 0 | present in sampled Bug editmeta |
| 文本、附件与链接 | 详细描述 | `customfield_10513` | string | Bug, Bug(edit screen) | optional / not create-required | 0 | present in sampled Bug editmeta |
| 审计只读 | Created | `created` | datetime/read-only | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 0 | read-only audit field; useful for stale reports |
| 审计只读 | Creator | `creator` | user/read-only | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 0 | read-only audit field from raw issue data |
| 审计只读 | Resolution Date | `resolutiondate` | datetime/read-only | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 0 | read-only audit field; usually populated by workflow resolution |
| 审计只读 | Updated | `updated` | datetime/read-only | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | optional / not create-required | 0 | read-only audit field; useful for stale reports |
| 其他字段 | Requirement Catalog | `customfield_11447` | raw-observed | raw observed only | optional / not create-required | 0 | observed value: 其它; raw issue has value; not in sampled create/edit metadata |
| 其他字段 | Resolution[外部小米专用] | `customfield_11700` | raw-observed | raw observed only | optional / not create-required | 0 | observed value: Fixed; raw issue has value; not in sampled create/edit metadata |
| 其他字段 | 归属Team(Ownership Team) | `customfield_11801` | option | Epic, Task, Bug, Bug(edit screen), Improvement, New Feature, Sub-task | optional / not create-required | 130 | present in sampled Bug editmeta |

## 枚举值

本节只固化相对稳定的枚举值。项目级、版本级、产品级、工作流级和用户级字段不要在这里固化，按“动态字段查询规则”获取。

### Issue Type / `issuetype`

- Epic
- Meeting
- Task
- Bug
- Improvement
- New Feature
- Sub-task

### Security Level / `security`

- AMBIQ 公司可见(包括公司内成员和阿波罗公司成员)
- P公司可见(包括公司内成员和外部成员)
- RTL公司可见(包括公司内成员和RTL公司成员)
- W公司-场测(包括公司内成员和外部成员)
- W公司-研发(包括公司内成员和外部成员)
- Y公司可见(包括公司内成员和外部成员)
- 仅公司内成员可见(Only visible to members within the company)
- 新思公司可见(包括公司内成员和新思公司成员)
- 瀛通公司(FLEX项目成员)
- 英飞凌公司可见(包括公司内成员和英飞凌)
- 领为公司可见(包括公司内成员和领为公司成员)

### Priority / `priority`

- Highest
- High
- Medium
- Low
- Lowest

### Severity / `customfield_10401`

- P0
- P1
- P2
- P3



### Reopen原因分类 / `customfield_12400`

- Bug fix不彻底
- CI Reopen
- JIRA操作不规范(测试)
- JIRA操作不规范(研发)
- RCA不充分
- 代码提交不规范
- 功能未按需求实现
- 提交的bug信息不全
- 研发对代码逻辑不熟
- 需求不明确
- 首次执行，未有再次Reopened操作

### 原因分类 / `customfield_12005`

- HW-可靠性测试
- HW-硬件设计
- HW-基带设计
- HW-天线设计
- HW-射频设计
- HW-屏设计
- HW-电池设计
- HW-音频设计
- HW-马达设计
- HW-充电线设计
- HW-包装设计
- HW-腕带设计
- HW-电子工艺
- HW-架构设计
- HW-结构设计
- HW-模具设计
- HW-结构工艺
- HW-物料设计
- HW-物料制程
- HW-ID/CMF
- HW-工厂管理
- HW-生产制程
- HW-生产治具
- HW-测试治具
- HW-固件问题
- HW-其他
- SW-需求问题
- SW-软件架构与设计问题
- SW-修改引入问题
- SW-功能优化
- SW-功能缺陷
- SW-性能缺陷
- SW-接口问题
- SW-安全性问题
- SW-易用性问题
- SW-兼容性问题
- SW-UI问题
- SW-配置问题
- SW-与标准不符
- SW-测试环境问题
- SW-文案问题
- SW-计算问题
- SW-算法问题，逻辑判断归入功能问题
- SW-操作问题
- SW-非问题
- SW-体验类问题
- SW-其他

### 发现问题阶段(Problem discovery stage) / `customfield_11000`

- 需求(Requirements)
- 定义(Definition)
- 开发(Development)
- Code Review
- 测试(Testing)
- 工厂(Factory)
- 用户(consumer)
- 售后(After-sales)
- 硬件研发(Hardware development)-T0
- 硬件研发(Hardware development)-EVT1
- 硬件研发(Hardware development)-EVT2
- 硬件研发(Hardware development)-EVT3
- 硬件研发(Hardware development)-EVT4
- 硬件研发(Hardware development)-DVT1
- 硬件研发(Hardware development)-DVT2
- 硬件研发(Hardware development)-DVT3
- 硬件研发(Hardware development)-DVT4
- 硬件研发(Hardware development)-PVT
- 硬件研发-原型机试产(Prototype Production Testing)
- MP

### 引入问题阶段 / `customfield_11001`

- 产品需求
- 研发设计
- 编码
- 硬件
- 不适用

### 报修平台(Repair platform) / `customfield_10404`

- Android
- iOS
- FW
- Server
- Algo
- Hardware
- Hardware Test
- 可靠性测试(Reliability testing)
- NPI 测试(NPI testing)
- 产线测试(Production line testing)
- 来料检查(Incoming inspection)
- 硬件自测(Hardware self-test)
- 声学(Acoustics)
- 电子工艺(Electronic technology)
- 整机工艺(Assembly process)
- IQC来料(Incoming Quality Control)
- 售后(After-sale service)

### 问题概率(problem probability) / `customfield_10716`

- 必现(Inevitable)（100%）
- 75%（≥7/10）
- 50%（≥ 5/10）
- 25%（≥2/10）
- 10% (1/10)
- 1% (只遇到一次[once])

### Integration / `customfield_11401`

- YES
- NO

### 测试轮次 / `customfield_12300`

- 1
- 2
- 3
- 4
- 5
- 6
- 7
- 8

### 归属Team(Ownership Team) / `customfield_11801`

- AI及创新研究院
- AI及创新研究院-算法工程部-北京工程组
- AI及创新研究院-算法工程部-合肥工程组
- APP事业部
- APP事业部-产品部
- APP事业部-用户运营和用户研究部
- APP事业部-视觉设计部
- APP事业部-软件研发部
- APP事业部-软件研发部-项目管理组
- APP健康功能组
- APP平台组
- APP测试组
- APP睡眠组
- APP设备组
- APP运动组
- Balance智能手表事业部
- Balance智能手表事业部-产品部
- Balance智能手表事业部-产品部-设计组
- Balance智能手表事业部-应用开发一组(健康）
- Balance智能手表事业部-应用开发三组(基础）
- Balance智能手表事业部-应用开发二组(系统）
- Balance智能手表事业部-应用开发四组(小程序）
- Balance智能手表事业部-成都开发组
- Balance智能手表事业部-硬件部
- Balance智能手表事业部-硬件部-质量与售后组
- Balance智能手表事业部-结构部
- Balance智能手表事业部-软件部
- Balance智能手表事业部-软件部-应用开发组
- Balance智能手表事业部-软件部-软件架构组
- Balance智能手表事业部-软件部-软件项目组
- Balance智能手表事业部-软件部-驱动开发组
- Balance智能手表事业部-驱动一组
- Balance智能手表事业部-驱动三组
- Balance智能手表事业部-驱动二组
- Balance智能手表事业部-驱动四组
- CTO办公室-研发效能部
- ZeppOS事业部
- ZeppOS事业部-AI产品与生态部
- ZeppOS事业部-中国产品部
- ZeppOS事业部-中间件部
- ZeppOS事业部-中间件部-中间件一组
- ZeppOS事业部-中间件部-中间件三组
- ZeppOS事业部-中间件部-中间件二组
- ZeppOS事业部-产品部
- ZeppOS事业部-产品部-用户与产品研究组
- ZeppOS事业部-内核与架构部
- ZeppOS事业部-内核与架构部-GUI引擎组
- ZeppOS事业部-内核与架构部-内核与架构组
- ZeppOS事业部-固件工程部
- ZeppOS事业部-固件工程部-Balance固件组
- ZeppOS事业部-固件工程部-工具与效率组
- ZeppOS事业部-应用平台部
- ZeppOS事业部-应用平台部-JS平台组
- ZeppOS事业部-应用平台部-JS生态组
- ZeppOS事业部-应用平台部-控件组
- ZeppOS事业部-应用开发部
- ZeppOS事业部-应用开发部-健康应用组
- ZeppOS事业部-应用开发部-多媒体应用组
- ZeppOS事业部-应用开发部-工具应用组
- ZeppOS事业部-应用开发部-系统应用组
- ZeppOS事业部-应用开发部-运动应用组
- ZeppOS事业部-应用生态部
- ZeppOS事业部-应用生态部-应用组
- ZeppOS事业部-硬件系统平台部
- ZeppOS事业部-硬件系统平台部-功耗组
- ZeppOS事业部-硬件系统平台部-外设组
- ZeppOS事业部-硬件系统平台部-存储组
- ZeppOS事业部-系统产品与设计部
- ZeppOS事业部-系统产品与设计部-用户与产品研究组
- ZeppOS事业部-系统产品与设计部-视觉设计组
- ZeppOS事业部-通信系统平台部
- ZeppOS事业部-通信系统平台部-蓝牙平台组
- ZeppOS事业部-通信系统平台部-蓝牙应用组
- ZeppOS事业部-通信系统平台部-通信组
- 供应链中心
- 供应链中心-供应质量与运作部-电子件质量组
- 助听器及TWS事业部
- 助听器及TWS事业部-产品管理部
- 助听器及TWS事业部-硬件开发部
- 助听器及TWS事业部-结构开发部
- 助听器及TWS事业部-营销及支持部
- 助听器及TWS事业部-质量与可靠性部
- 助听器及TWS事业部-软件开发部
- 助听器及TWS事业部-项目管理部
- 外包同学(Outsourced classmates)
- 大数据及云平台事业部
- 大数据及云平台事业部-工程平台部
- 大数据及云平台事业部-应用中台部
- 大数据及云平台事业部-数据应用部
- 大数据及云平台事业部-设备中台部
- 工业设计中心
- 市场部
- 测试中心
- 硬件平台部
- 芯片事业部
- 芯片事业部-应用及软件
- 运动手表事业部
- 运动手表事业部-产品质量部
- 运动手表事业部-产品质量部-硬件质量组
- 运动手表事业部-硬件部
- 运动手表事业部-硬件部-硬件工程组
- 运动手表事业部-硬件部-硬件项目组
- 运动手表事业部-硬件部-结构工艺组
- 运动手表事业部-社区运营与产品研究部
- 运动手表事业部-社区运营与产品研究部-UI设计组
- 运动手表事业部-社区运营与产品部-硬件产品组
- 运动手表事业部-社区运营与产品部-软件产品组
- 运动手表事业部-软件部
- 运动手表事业部-软件部-GNSS组
- 运动手表事业部-软件部-传感器组
- 运动手表事业部-软件部-平台组
- 运动手表事业部-软件部-软件项目组
- 运动手表事业部-软件部-运动应用组
- 运动手表事业部-软件部-运动架构组
- 运动手表事业部-运动应用组
- 重点业务产品商务和支持中心
- 青春手表事业部
- 青春手表事业部-产品部
- 青春手表事业部-应用开发一组
- 青春手表事业部-应用开发二组
- 青春手表事业部-硬件部
- 青春手表事业部-结构部
- 青春手表事业部-软件部
- 青春手表事业部-软件部-应用开发组
- 青春手表事业部-软件部-软件架构组
- 青春手表事业部-软件部-软件项目组
- 青春手表事业部-项目与质量部
- 青春手表事业部-项目与质量部-产品质量组
- 青春手表事业部-驱动组
- 硬件合作方

## Raw 观察字段 / 未复核前不要用于创建编辑

| 字段 | 字段 ID | 样例单中观察到的值 | 规则 |
| --- | --- | --- | --- |
| Root Cause | `customfield_10902` | Development | raw issue has value; not in sampled create/edit metadata |
| Resolution[外部小米专用] | `customfield_11700` | Fixed | raw issue has value; not in sampled create/edit metadata |
| Products (GT3) | `customfield_11400` | huamiOS (Kernel/Platform/Apps...) | legacy/raw field; use Products/customfield_10800 for create/edit |
| Requirement Catalog | `customfield_11447` | 其它 | raw issue has value; not in sampled create/edit metadata |
| 复现概率 | `customfield_10312` | 必现（100%） | legacy/raw field; use 问题概率/customfield_10716 for create/edit |

## Agent 使用规则

- Before creating an issue, choose the issue type first, then apply that issue type's required fields from this document.
- For Bug creation, never omit `customfield_10401`, `customfield_10404`, `customfield_11000`, `security`, `summary`, `issuetype`, and `project`.
- For Epic creation, include `customfield_10103` / Epic Name in addition to the common required fields.
- For Sub-task creation, include `parent` in addition to the common required fields.
- Prefer `Severity` over `Priority` when judging risk or sorting defects. `Priority` remains optional metadata unless the user specifically asks for it.
- Do not repeatedly query enum metadata during normal skill use. Query Jira metadata only when the project changes, Jira rejects a value, or the user explicitly asks for a refresh.
- Treat generated reports as read-only unless the user explicitly asks for Jira mutation.

## 维护信息

- 固定字段、必填规则和部分稳定枚举基于已验证的 Active Jira 元数据固化；项目级动态字段不固化具体取值，按目标项目实时查询。
- `Products (GT3)` / `customfield_11400`、`复现概率` / `customfield_10312` 等 raw/legacy 字段只作为历史兼容线索，不作为创建或编辑字段。
