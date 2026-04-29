# GENEVA-1996 关键属性和值清单

- 查询时间: 2026-04-29 16:49:35 Asia/Shanghai
- Jira: https://jira.huami.com/browse/GENEVA-1996
- 范围: GENEVA / Bug；选项来源优先使用 `/editmeta` 和 `/createmeta`
- 必填字段数: 7 / create/edit 字段总数: 38

## 当前关键值

- Summary: 【FROM 质量平台-意见反馈】2026-04-20 04:23:17 After the latest updates, notifications are almost non-existent, neither FB nor SMS, despite the features being enabled and the watch being reset
- Status: Open
- Assignee: gangan
- Reporter: zhanghuan
- Priority: Highest
- Severity: P1
- Repair platform: FW
- Discovery stage: 用户(consumer)
- Versions: affects=gen-ota1.2-3/12; fix=gen-ota1.2-3/12
- Labels: 消息通知问题, 质量平台-意见反馈模块

## 关键属性、当前值、可选项

| 属性 | 字段 ID | 必填 | 当前值 | 可选项 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Project | `project` | 是 | Geneva | Geneva | 当前按 GENEVA 项目筛选 |
| Issue Type | `issuetype` | 是 | Bug | Epic, Meeting, Task, Bug, Improvement, New Feature, Sub-task | 项目可选类型；本单为 Bug |
| Status | `status` | workflow | Open | Open, In Progress, Resolved, Closed, Reopened, Pending | 当前可执行流转: Start Progress -> In Progress, Pending -> Pending |
| Summary | `summary` | 是 | 【FROM 质量平台-意见反馈】2026-04-20 04:23:17 After the latest updates, notifications are almost non-existent, neither FB nor SMS, despite the features being enabled and the watch being reset | - | 文本 |
| Priority | `priority` | 否 | Highest | Highest, High, Medium, Low, Lowest |  |
| Severity | `customfield_10401` | 是 | P1 | P0, P1, P2, P3 |  |
| Security Level | `security` | 是 | 仅公司内成员可见(Only visible to members within the company) | AMBIQ 公司可见(包括公司内成员和阿波罗公司成员), P公司可见(包括公司内成员和外部成员), RTL公司可见(包括公司内成员和RTL公司成员), W公司-场测(包括公司内成员和外部成员), W公司-研发(包括公司内成员和外部成员), Y公司可见(包括公司内成员和外部成员), 仅公司内成员可见(Only visible to members within the company), 新思公司可见(包括公司内成员和新思公司成员), 瀛通公司(FLEX项目成员), 英飞凌公司可见(包括公司内成员和英飞凌), 领为公司可见(包括公司内成员和领为公司成员) |  |
| 报修平台(Repair platform) | `customfield_10404` | 是 | FW | Android, iOS, FW, Server, Algo, Hardware, Hardware Test, 可靠性测试(Reliability testing), NPI  测试(NPI testing), 产线测试(Production line testing), 来料检查(Incoming inspection), 硬件自测(Hardware self-test), 声学(Acoustics), 电子工艺(Electronic technology), 整机工艺(Assembly process), IQC来料(Incoming Quality Control), 售后(After-sale service) |  |
| 发现问题阶段(Problem discovery stage) | `customfield_11000` | 是 | 用户(consumer) | 需求(Requirements), 定义(Definition), 开发(Development), Code Review, 测试(Testing), 工厂(Factory), 用户(consumer), 售后(After-sales), 硬件研发(Hardware development)-T0, 硬件研发(Hardware development)-EVT1, 硬件研发(Hardware development)-EVT2, 硬件研发(Hardware development)-EVT3, 硬件研发(Hardware development)-EVT4, 硬件研发(Hardware development)-DVT1, 硬件研发(Hardware development)-DVT2, 硬件研发(Hardware development)-DVT3, 硬件研发(Hardware development)-DVT4, 硬件研发(Hardware development)-PVT, 硬件研发-原型机试产(Prototype Production Testing), MP |  |
| 引入问题阶段 | `customfield_11001` | 否 | - | 产品需求, 研发设计, 编码, 硬件, 不适用 |  |
| 问题概率(problem probability) | `customfield_10716` | 否 | - | 必现(Inevitable)（100%）, 75%（≥7/10）, 50%（≥ 5/10）, 25%（≥2/10）, 10% (1/10), 1% (只遇到一次[once]) | 当前 raw 旧字段 customfield_10312/复现概率 = 必现（100%） |
| Products | `customfield_10800` | 否 | - | Munich, Oslo, Dublin, Matterhorn, Makalu, Rocky, Rimo, Lincs, Lisbon, Lisbon-L, Newton, Newton-L, Prague, Volga, Hamburg, Bonn, Madrid(GT3), Geneva(GT3), Zurich(GT3), Verona(GT3), Vienna(GT3), Barcelona(GT3), Andes(GT3), huamiOS(Kernel/Platform/Apps...), Bled(GT3), Cannes(GT3), Osaka(GT3), Cigna, Prudential, Timex/T-Mobile, Sofia, Teide, Florence, Berlin, Lille, Cheetah, Swift, Swordfish, Monaco, Altai, Hannover, Etna, kunlun-标准版, kunlun-北美版 | 当前 raw 旧字段 customfield_11400/Products (GT3) = huamiOS (Kernel/Platform/Apps...) |
| Affects Version/s | `versions` | 否 | gen-ota1.2-3/12 | gen-preT0-7/28, gen-T0-8/17, gen-EVT-8/30, gen-DVT-9/30, gen-PVT-10/27, gen-PVT2-11/10, gen-OTA1-12/30, gen-α1-9/5, gen-α2-9/19, gen-preβ1-10/9, gen-β1-10/15, gen-β2-10/22, gen-β3-11/5, gen-β4-11/12, gen-rc1-11/27, gen-rc2-12/5, gen-rc3-12/19, gen-rc5-12/26, gen-β5-11/18, gen-rc2-12/12, gen-ota1.1-1/5, gen-ota1.1-1/12, gen-ota1.1-1/16, gen-ota1.1-1/21, gen-ota2-1/28, gen-ota1.1- 2/26, gen-ota1.1-3/3, gen-ota1.2-3/12, gen-ota1.2-3/20, gen-ota1.2-3/26, gen-ota2-4/28, gen-ota2-5/13, gen-ota2-5/20, gen-ota2-5/27 |  |
| Fix Version/s | `fixVersions` | 否 | gen-ota1.2-3/12 | gen-preT0-7/28, gen-T0-8/17, gen-EVT-8/30, gen-DVT-9/30, gen-PVT-10/27, gen-PVT2-11/10, gen-OTA1-12/30, gen-α1-9/5, gen-α2-9/19, gen-preβ1-10/9, gen-β1-10/15, gen-β2-10/22, gen-β3-11/5, gen-β4-11/12, gen-rc1-11/27, gen-rc2-12/5, gen-rc3-12/19, gen-rc5-12/26, gen-β5-11/18, gen-rc2-12/12, gen-ota1.1-1/5, gen-ota1.1-1/12, gen-ota1.1-1/16, gen-ota1.1-1/21, gen-ota2-1/28, gen-ota1.1- 2/26, gen-ota1.1-3/3, gen-ota1.2-3/12, gen-ota1.2-3/20, gen-ota1.2-3/26, gen-ota2-4/28, gen-ota2-5/13, gen-ota2-5/20, gen-ota2-5/27 |  |
| 规划版本 | `customfield_12700` | 否 | - | gen-preT0-7/28, gen-T0-8/17, gen-EVT-8/30, gen-DVT-9/30, gen-PVT-10/27, gen-PVT2-11/10, gen-OTA1-12/30, gen-α1-9/5, gen-α2-9/19, gen-preβ1-10/9, gen-β1-10/15, gen-β2-10/22, gen-β3-11/5, gen-β4-11/12, gen-rc1-11/27, gen-rc2-12/5, gen-rc3-12/19, gen-rc5-12/26, gen-β5-11/18, gen-rc2-12/12, gen-ota1.1-1/5, gen-ota1.1-1/12, gen-ota1.1-1/16, gen-ota1.1-1/21, gen-ota2-1/28, gen-ota1.1- 2/26, gen-ota1.1-3/3, gen-ota1.2-3/12, gen-ota1.2-3/20, gen-ota1.2-3/26, gen-ota2-4/28, gen-ota2-5/13, gen-ota2-5/20, gen-ota2-5/27 |  |
| 归属Team(Ownership Team) | `customfield_11801` | 否 | 青春手表事业部-应用开发一组 | AI及创新研究院, AI及创新研究院-算法工程部-北京工程组, AI及创新研究院-算法工程部-合肥工程组, APP事业部, APP事业部-产品部, APP事业部-用户运营和用户研究部, APP事业部-视觉设计部, APP事业部-软件研发部, APP事业部-软件研发部-项目管理组, APP健康功能组, APP平台组, APP测试组, APP睡眠组, APP设备组, APP运动组, Balance智能手表事业部, Balance智能手表事业部-产品部, Balance智能手表事业部-产品部-设计组, Balance智能手表事业部-应用开发一组(健康）, Balance智能手表事业部-应用开发三组(基础）, Balance智能手表事业部-应用开发二组(系统）, Balance智能手表事业部-应用开发四组(小程序）, Balance智能手表事业部-成都开发组, Balance智能手表事业部-硬件部, Balance智能手表事业部-硬件部-质量与售后组, Balance智能手表事业部-结构部, Balance智能手表事业部-软件部, Balance智能手表事业部-软件部-应用开发组, Balance智能手表事业部-软件部-软件架构组, Balance智能手表事业部-软件部-软件项目组, Balance智能手表事业部-软件部-驱动开发组, Balance智能手表事业部-驱动一组, Balance智能手表事业部-驱动三组, Balance智能手表事业部-驱动二组, Balance智能手表事业部-驱动四组, CTO办公室-研发效能部, ZeppOS事业部, ZeppOS事业部-AI产品与生态部, ZeppOS事业部-中国产品部, ZeppOS事业部-中间件部, ZeppOS事业部-中间件部-中间件一组, ZeppOS事业部-中间件部-中间件三组, ZeppOS事业部-中间件部-中间件二组, ZeppOS事业部-产品部, ZeppOS事业部-产品部-用户与产品研究组, ZeppOS事业部-内核与架构部, ZeppOS事业部-内核与架构部-GUI引擎组, ZeppOS事业部-内核与架构部-内核与架构组, ZeppOS事业部-固件工程部, ZeppOS事业部-固件工程部-Balance固件组, ZeppOS事业部-固件工程部-工具与效率组, ZeppOS事业部-应用平台部, ZeppOS事业部-应用平台部-JS平台组, ZeppOS事业部-应用平台部-JS生态组, ZeppOS事业部-应用平台部-控件组, ZeppOS事业部-应用开发部, ZeppOS事业部-应用开发部-健康应用组, ZeppOS事业部-应用开发部-多媒体应用组, ZeppOS事业部-应用开发部-工具应用组, ZeppOS事业部-应用开发部-系统应用组, ZeppOS事业部-应用开发部-运动应用组, ZeppOS事业部-应用生态部, ZeppOS事业部-应用生态部-应用组, ZeppOS事业部-硬件系统平台部, ZeppOS事业部-硬件系统平台部-功耗组, ZeppOS事业部-硬件系统平台部-外设组, ZeppOS事业部-硬件系统平台部-存储组, ZeppOS事业部-系统产品与设计部, ZeppOS事业部-系统产品与设计部-用户与产品研究组, ZeppOS事业部-系统产品与设计部-视觉设计组, ZeppOS事业部-通信系统平台部, ZeppOS事业部-通信系统平台部-蓝牙平台组, ZeppOS事业部-通信系统平台部-蓝牙应用组, ZeppOS事业部-通信系统平台部-通信组, 供应链中心, 供应链中心-供应质量与运作部-电子件质量组, 助听器及TWS事业部, 助听器及TWS事业部-产品管理部, 助听器及TWS事业部-硬件开发部, 助听器及TWS事业部-结构开发部, 助听器及TWS事业部-营销及支持部, 助听器及TWS事业部-质量与可靠性部, 助听器及TWS事业部-软件开发部, 助听器及TWS事业部-项目管理部, 外包同学(Outsourced classmates), 大数据及云平台事业部, 大数据及云平台事业部-工程平台部, 大数据及云平台事业部-应用中台部, 大数据及云平台事业部-数据应用部, 大数据及云平台事业部-设备中台部, 工业设计中心, 市场部, 测试中心, 硬件平台部, 芯片事业部, 芯片事业部-应用及软件, 运动手表事业部, 运动手表事业部-产品质量部, 运动手表事业部-产品质量部-硬件质量组, 运动手表事业部-硬件部, 运动手表事业部-硬件部-硬件工程组, 运动手表事业部-硬件部-硬件项目组, 运动手表事业部-硬件部-结构工艺组, 运动手表事业部-社区运营与产品研究部, 运动手表事业部-社区运营与产品研究部-UI设计组, 运动手表事业部-社区运营与产品部-硬件产品组, 运动手表事业部-社区运营与产品部-软件产品组, 运动手表事业部-软件部, 运动手表事业部-软件部-GNSS组, 运动手表事业部-软件部-传感器组, 运动手表事业部-软件部-平台组, 运动手表事业部-软件部-软件项目组, 运动手表事业部-软件部-运动应用组, 运动手表事业部-软件部-运动架构组, 运动手表事业部-运动应用组, 重点业务产品商务和支持中心, 青春手表事业部, 青春手表事业部-产品部, 青春手表事业部-应用开发一组, 青春手表事业部-应用开发二组, 青春手表事业部-硬件部, 青春手表事业部-结构部, 青春手表事业部-软件部, 青春手表事业部-软件部-应用开发组, 青春手表事业部-软件部-软件架构组, 青春手表事业部-软件部-软件项目组, 青春手表事业部-项目与质量部, 青春手表事业部-项目与质量部-产品质量组, 青春手表事业部-驱动组, 硬件合作方 |  |
| 原因分类 | `customfield_12005` | 否 | - | HW-可靠性测试, HW-硬件设计, HW-基带设计, HW-天线设计, HW-射频设计, HW-屏设计, HW-电池设计, HW-音频设计, HW-马达设计, HW-充电线设计, HW-包装设计, HW-腕带设计, HW-电子工艺, HW-架构设计, HW-结构设计, HW-模具设计, HW-结构工艺, HW-物料设计, HW-物料制程, HW-ID/CMF, HW-工厂管理, HW-生产制程, HW-生产治具, HW-测试治具, HW-固件问题, HW-其他, SW-需求问题, SW-软件架构与设计问题, SW-修改引入问题, SW-功能优化, SW-功能缺陷, SW-性能缺陷, SW-接口问题, SW-安全性问题, SW-易用性问题, SW-兼容性问题, SW-UI问题, SW-配置问题, SW-与标准不符, SW-测试环境问题, SW-文案问题, SW-计算问题, SW-算法问题，逻辑判断归入功能问题, SW-操作问题, SW-非问题, SW-体验类问题, SW-其他 |  |
| Reopen原因分类 | `customfield_12400` | 否 | - | Bug fix不彻底, CI Reopen, JIRA操作不规范(测试), JIRA操作不规范(研发), RCA不充分, 代码提交不规范, 功能未按需求实现, 提交的bug信息不全, 研发对代码逻辑不熟, 需求不明确, 首次执行，未有再次Reopened操作 |  |
| Integration | `customfield_11401` | 否 | - | YES, NO |  |
| Component/s | `components` | 否 | - | - | 当前项目 components 接口返回 0 个组件 |
| Labels | `labels` | 否 | 消息通知问题, 质量平台-意见反馈模块 | - | 自由标签/已有标签 |
| Assignee | `assignee` | 否 | gangan | - | 用户字段，通过用户搜索选择 |
| Reporter | `reporter` | 否 | zhanghuan | - | 用户字段，通过用户搜索选择 |
| Due Date | `duedate` | 否 | 2026-04-23 | - | 日期 |
| Description | `description` | 否 | - | - | 文本 |
| 详细描述 | `customfield_10513` | 否 | 用户: <id-redacted> / 联系方式: <contact-redacted> / 手机型号: InfinixInfinix X6851B / 系统版本: 15 / APP版本号: 10.2.0-play(151825)202604071614 / 绑定设备: GenevaWN / 固件版本: 3.7.0.1 / 反馈时间: 2026-04-20 04:23:17 / 反馈详情: powiadomienia po ostatnich aktualizacji już prawie nie przychodzą ani FB ani SMS mimo właczonych funkcji i resetu zegarka / 反馈详情(英文): After the latest updates, notifications are almost non-existent, neither FB nor SMS, despite the features being enabled and the watch being reset / 日志标签: 通知服务异常(Android) , BT连接始终建立失败 , 频繁断连 , v3睡眠算法 , 心跳包超时断连 / 质量平台上的该反馈: https://devops.zepp.com/zeus/#/feedback?app_name=zepp&id=6bdpp50BxFTLHfN_sg1s | - | 文本；清单中已脱敏联系方式 |
| Root Cause | `customfield_10902` | 否 | Development | - | raw issue 有当前值，但不在当前 Bug create/edit meta 中；REST 未返回完整可选项 |
| Resolution[外部小米专用] | `customfield_11700` | 否 | Fixed | - | raw issue 有当前值，但不在当前 Bug create/edit meta 中；REST 未返回完整可选项 |
| Requirement Catalog | `customfield_11447` | 否 | 其它 | - | raw issue 有当前值，但不在当前 Bug create/edit meta 中；REST 未返回完整可选项 |

## 全量 create/edit 字段

| 字段名 | 字段 ID | 必填 | 类型 | 当前值 | 选项数量 |
| --- | --- | --- | --- | --- | --- |
| Issue Type | `issuetype` | 是 | issuetype | Bug | 1 |
| Project | `project` | 是 | project | Geneva | 1 |
| Security Level | `security` | 是 | securitylevel | 仅公司内成员可见(Only visible to members within the company) | 11 |
| Severity | `customfield_10401` | 是 | option | P1 | 4 |
| Summary | `summary` | 是 | string | 【FROM 质量平台-意见反馈】2026-04-20 04:23:17 After the latest updates, notifications are almost non-existent, neither FB nor SMS, despite the features being enabled and the watch being reset | 0 |
| 发现问题阶段(Problem discovery stage) | `customfield_11000` | 是 | option | 用户(consumer) | 20 |
| 报修平台(Repair platform) | `customfield_10404` | 是 | option | FW | 17 |
| Affects Version/s | `versions` | 否 | array/version | gen-ota1.2-3/12 | 34 |
| Assignee | `assignee` | 否 | user | gangan | 0 |
| Attachment | `attachment` | 否 | array/attachment | - | 0 |
| Component/s | `components` | 否 | array/component | - | 0 |
| Description | `description` | 否 | string | - | 0 |
| Due Date | `duedate` | 否 | date | 2026-04-23 | 0 |
| Environment | `environment` | 否 | string | - | 0 |
| Epic Link | `customfield_10101` | 否 | any | - | 0 |
| Fix Version/s | `fixVersions` | 否 | array/version | gen-ota1.2-3/12 | 34 |
| Follower | `customfield_10304` | 否 | array/user | - | 0 |
| Gerrit_Url | `customfield_11200` | 否 | string | - | 0 |
| Integration | `customfield_11401` | 否 | option | - | 2 |
| Labels | `labels` | 否 | array/string | 消息通知问题, 质量平台-意见反馈模块 | 0 |
| Linked Issues | `issuelinks` | 否 | array/issuelinks | - | 0 |
| Log Work | `worklog` | 否 | array/worklog | {"startAt": 0, "maxResults": 20, "total": 0, "worklogs": []} | 0 |
| Priority | `priority` | 否 | priority | Highest | 5 |
| Products | `customfield_10800` | 否 | array/option | - | 44 |
| Reopen原因分类 | `customfield_12400` | 否 | option | - | 11 |
| RootCause Analysis | `customfield_11002` | 否 | string | - | 0 |
| SYNC_ISSUE | `customfield_10720` | 否 | string | - | 0 |
| Start date | `customfield_10702` | 否 | date | - | 0 |
| Status whiteboard | `customfield_10717` | 否 | string | - | 0 |
| Time Tracking | `timetracking` | 否 | timetracking | - | 0 |
| 原因分类 | `customfield_12005` | 否 | option | - | 47 |
| 引入问题阶段 | `customfield_11001` | 否 | option | - | 5 |
| 归属Team(Ownership Team) | `customfield_11801` | 否 | option | 青春手表事业部-应用开发一组 | 130 |
| 改进措施 | `customfield_12002` | 否 | string | - | 0 |
| 研发验证结果 | `customfield_12003` | 否 | string | - | 0 |
| 规划版本 | `customfield_12700` | 否 | version | - | 34 |
| 详细描述 | `customfield_10513` | 否 | string | 用户: <id-redacted> / 联系方式: <contact-redacted> / 手机型号: InfinixInfinix X6851B / 系统版本: 15 / APP版本号: 10.2.0-play(151825)202604071614 / 绑定设备: GenevaWN / 固件版本: 3.7.0.1 / 反馈时间: 2026-04-20 04:23:17 / 反馈详情: powiadomienia po ostatnich aktualizacji już prawie nie przychodzą ani FB ani SMS mimo właczonych funkcji i resetu zegarka / 反馈详情(英文): After the latest updates, notifications are almost non-existent, neither FB nor SMS, despite the features being enabled and the watch being reset / 日志标签: 通知服务异常(Android) , BT连接始终建立失败 , 频繁断连 , v3睡眠算法 , 心跳包超时断连 / 质量平台上的该反馈: https://devops.zepp.com/zeus/#/feedback?app_name=zepp&id=6bdpp50BxFTLHfN_sg1s | 0 |
| 问题概率(problem probability) | `customfield_10716` | 否 | option | - | 6 |
