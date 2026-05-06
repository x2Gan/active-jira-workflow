# active-jira-workflow

`active-jira-workflow` 是面向 Active 团队的 Jira 与飞书 Agent 工作流仓库。它把本地 [`ankitpokhrel/jira-cli`](https://github.com/ankitpokhrel/jira-cli) 和官方 `lark-cli` 封装成可安装的 Skills，让 Codex、GitHub Copilot 等 Agent 能按团队规则查询 Jira、生成 Markdown 报告、创建规范 Jira，并把报告发布为飞书云文档后推送到指定群聊。

## GitHub Description

面向 Codex/Copilot 的 Active Jira Agent 工作流：安装 jira-cli/Lark CLI Skills，查询与管理 Jira，生成规则化 Markdown 报告，并发布到飞书文档和机器人群聊。

## 能力概览

| 能力 | 说明 |
| --- | --- |
| Jira 查询与管理 | 查询 issue、epic、sprint、release、project、board；查看、创建、编辑、流转、评论、指派、链接、克隆、关注 Jira issue。 |
| 场景化 Jira 报告 | 生成周报、风险报告、发布报告、负责人汇总；内置 `GENEVA` 长期未处理 Jira 报告，自动分页、排序、Highlight 和汇总。 |
| 项目规则化建单 | 按 Active 项目规则补齐缺陷 Jira 的 Severity、Products、自定义字段、标签、组件等信息。 |
| 飞书文档发布 | 通过官方 Lark CLI 将本地 Markdown 报告创建或更新为飞书云文档。 |
| 飞书机器人推送 | 为目标群聊授权文档查看权限，并通过机器人发送报告链接，支持 `--dry-run` 预览外部副作用。 |
| 安装与更新 | 一键安装源码、jira-cli、Skills、本地管理命令；Lark CLI 作为可选增强能力接入。 |

## 常用入口速查

| 场景 | 命令 |
| --- | --- |
| 一键安装 | `gh auth login && gh auth setup-git` 后执行下方 Private 安装命令 |
| 更新源码和 jira-cli | `active-jira update` |
| 重新安装 Skills | `active-jira skills` |
| 查看版本 | `active-jira version` |
| 生成长期未处理 Jira 报告 | `python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w` |
| 生成报告并发布到飞书 | `python active-jira-report/scripts/publish_stale_jira_report_to_lark.py --project GENEVA --age 1w --dry-run` |
| 发布已有报告并推送到群聊 | `python active-jira-report/scripts/publish_stale_jira_report_to_lark.py --project GENEVA --age 1w --report-input reports/geneva-stale-jira.md --chat-id oc_xxx --grant-chat-view --dry-run` |
| Lark CLI 环境检查 | `sh lark-cli.sh doctor` |

## 仓库摘要

仓库主要内容：

```text
install.sh                         一键安装、更新、配置入口
jira-cli.sh                        Linux 下安装/更新 ankitpokhrel/jira-cli 的辅助脚本
lark-cli.sh                        可选安装/配置/登录官方 Lark CLI 的辅助脚本
VERSION                            仓库版本
active-jira/SKILL.md               Agent Skill 主说明
active-jira-report/SKILL.md        场景化报告与规则化建单 Skill
active-lark/SKILL.md               飞书/Lark CLI 通用能力 Skill
active-jira/references/            jira-cli 用法参考
active-jira/scripts/               场景化查询脚本
active-jira/agents/openai.yaml     Skill 展示信息
active-jira-report/references/     报告模板与建单规则参考
active-jira-report/scripts/        Jira 报告生成与飞书发布编排脚本
active-jira-report/agents/openai.yaml Skill 展示信息
active-lark/references/            lark-cli 用法与快捷命令参考
active-lark/scripts/               飞书文档发布辅助脚本
active-lark/agents/openai.yaml     Skill 展示信息
reports/                           本地生成报告目录，默认不提交 Git
```

安装后会得到三部分能力：

- 源码目录：默认安装到当前目录下的 `active-jira-workflow/`。
- Skill 软链接：默认同时安装 `active-jira`、`active-jira-report` 和 `active-lark` 到 Codex 或 GitHub Copilot 项目的 skills 目录。
- 本地管理命令：默认安装为 `~/.local/bin/active-jira`，用于后续更新和查看版本。

## 设计原则

- 本地优先：Jira 与飞书操作都通过本机 CLI 执行，不在仓库中保存 Jira Token、飞书 App Secret、access token 或 refresh token。
- Skills 可演进：通用 Jira 能力、场景化报告能力、飞书能力拆成独立 Skill，方便按需安装和持续迭代。
- 可审计输出：报告固定包含查询时间、命令、JQL、分页策略和字段来源，方便复盘。
- 外部副作用先预览：飞书文档创建、权限授权、消息发送等写操作优先使用 `--dry-run`。

## 分发方式

仓库切换为 Private 后，未认证访问 `raw.githubusercontent.com` 会返回 `404`。这不是文件不存在，而是 GitHub 对私有仓库 raw 文件的默认隐藏行为。推荐使用 GitHub CLI 先完成认证，再拉取安装脚本：

```bash
gh auth login
gh auth setup-git
```

Private 仓库一行安装：

```bash
sh -c "$(gh api --method GET -H 'Accept: application/vnd.github.raw+json' /repos/active-ailab/active-jira-workflow/contents/install.sh -f ref=main)"
```

也可以指定源码安装父目录：

```bash
sh -c "$(gh api --method GET -H 'Accept: application/vnd.github.raw+json' /repos/active-ailab/active-jira-workflow/contents/install.sh -f ref=main)" -- /path/to/parent
```

如果本机没有安装 GitHub CLI，可以使用具备仓库 `Contents: Read` 权限的 Token：

```bash
export GITHUB_TOKEN="github_pat_xxx"
sh -c "$(curl -fsSL -H "Authorization: Bearer ${GITHUB_TOKEN:?}" -H 'Accept: application/vnd.github.raw+json' 'https://api.github.com/repos/active-ailab/active-jira-workflow/contents/install.sh?ref=main')"
```

源码会被放到：

```text
/path/to/parent/active-jira-workflow
```

如果需要先手动克隆仓库，也可以在仓库内执行：

```bash
gh repo clone active-ailab/active-jira-workflow
cd active-jira-workflow
PROJECT_DIR="$(pwd)" sh install.sh
```

从已克隆源码目录直接运行 `install.sh` 时，建议显式设置 `PROJECT_DIR="$(pwd)"`，表示复用当前源码目录。

如果使用 SSH，也可以手动克隆后安装：

```bash
git clone git@github.com:active-ailab/active-jira-workflow.git
cd active-jira-workflow
PROJECT_DIR="$(pwd)" REPO_URL=git@github.com:active-ailab/active-jira-workflow.git sh install.sh
```

## 安装

交互式完整安装：

```bash
gh auth login
gh auth setup-git
sh -c "$(gh api --method GET -H 'Accept: application/vnd.github.raw+json' /repos/active-ailab/active-jira-workflow/contents/install.sh -f ref=main)"
```

安装流程会依次做这些事：

1. 下载或更新本仓库源码。
2. 检查本地是否存在 `jira` 命令。
3. 如果缺少 `jira`，在 Linux 环境下通过 `jira-cli.sh` 安装 `ankitpokhrel/jira-cli`。
4. 执行 `jira init`，生成 JiraCLI 配置。
5. 将 `active-jira`、`active-jira-report` 和 `active-lark` 三个 Skill 软链接到目标 Agent 的 skills 目录。
6. 安装本地管理命令 `active-jira`。

安装流程末尾会把 Lark CLI 作为可选增强能力提示出来，默认不会安装。它用于后续把生成的 Jira Markdown 报告发布为飞书云文档，并在确认后发送给指定用户或群。

安装完成后，如果 `~/.local/bin` 已在 `PATH` 中，可以使用本地管理命令：

```bash
# 只安装/更新 Skill 和本地管理命令，不重新初始化 jira-cli
active-jira skills

# 更新本仓库源码，并检查/更新 jira-cli
active-jira update

# 查看安装器、源码、jira-cli 版本
active-jira version

# 查看安装器帮助
active-jira help
```

可以用下面的命令确认本地管理命令是否存在，以及它当前指向哪个源码目录：

```bash
command -v active-jira
active-jira version
```

如果还没有安装 `active-jira`，或者它指向旧源码目录，可以在当前仓库中直接使用 `install.sh` 的等价命令：

```bash
PROJECT_DIR="$(pwd)" sh install.sh skills
PROJECT_DIR="$(pwd)" sh install.sh update
PROJECT_DIR="$(pwd)" sh install.sh version
PROJECT_DIR="$(pwd)" sh install.sh help
```

如果 `~/.local/bin` 不在 `PATH` 中，请把下面这行加入 `~/.zshrc` 或 `~/.bashrc`，然后重新打开终端：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 配置

### JiraCLI 配置

安装器会调用 `jira init`。交互式安装时，它会询问：

- Jira 服务器地址，例如 `https://jira.example.com`
- Jira 类型：`cloud` 或 `local`
- 认证类型：`basic`、`bearer` 或 `mtls`
- Jira 账号
- Jira 密码、API Token 或 PAT
- 默认 Jira project
- 默认 Jira board

非交互式安装可以通过环境变量提供配置：

```bash
JIRA_SERVER="https://jira.example.com" \
JIRA_ACCOUNT="your.name" \
JIRA_API_TOKEN="your-token-or-password" \
JIRA_INSTALLATION="local" \
JIRA_AUTH_TYPE="bearer" \
JIRA_PROJECT="GENEVA" \
JIRA_BOARD="Geneva Board" \
SKILL_PROJECT_ROOT="/path/to/active/project" \
SKILL_PLUGIN="codex" \
sh -c "$(gh api --method GET -H 'Accept: application/vnd.github.raw+json' /repos/active-ailab/active-jira-workflow/contents/install.sh -f ref=main)"
```

Jira Cloud 通常使用：

```bash
JIRA_INSTALLATION="cloud"
JIRA_AUTH_TYPE="basic"
JIRA_API_TOKEN="Atlassian API Token"
```

Jira Server/Data Center 使用 PAT 时通常使用：

```bash
JIRA_INSTALLATION="local"
JIRA_AUTH_TYPE="bearer"
JIRA_API_TOKEN="Personal Access Token"
```

安装器会把认证信息写入 `~/.netrc` 的托管区块，并将文件权限设置为 `600`。如果你已经有自定义 JiraCLI 配置，也可以跳过初始化：

```bash
PROJECT_DIR="$(pwd)" INIT_JIRA_CLI=0 sh install.sh
```

如果机器已经安装好 `jira`，并且不希望安装器处理 jira-cli：

```bash
PROJECT_DIR="$(pwd)" INSTALL_JIRA_CLI=0 sh install.sh
```

### Lark CLI 可选接入

Lark CLI 是可选能力，不影响 Jira 查询和本地 Markdown 报告生成。需要发布到飞书云文档时，可以单独安装并完成飞书配置、登录：

```bash
sh lark-cli.sh bootstrap
```

也可以先只安装官方 CLI 和 Skill，不拉起浏览器配置或 OAuth 登录：

```bash
sh lark-cli.sh install
```

该命令会安装官方 npm 包 `@larksuite/cli`，并按官方当前推荐方式执行 `npx -y skills add larksuite/cli -g -y` 安装上游 Lark CLI Skills。仓库内的 `active-lark` Skill 是本项目自己的聚合封装，会随主安装器一起安装。

在主安装器中显式启用：

```bash
INSTALL_LARK_CLI=1 sh install.sh
```

如果只希望主安装器安装 Lark CLI、不执行配置和登录：

```bash
INSTALL_LARK_CLI=1 LARK_CLI_SETUP_MODE=install sh install.sh
```

常用维护命令：

```bash
sh lark-cli.sh doctor
sh lark-cli.sh status
sh lark-cli.sh update
```

`config` 和 `login` 会进入飞书官方配置或 OAuth 授权流程，可能打开浏览器或输出链接。本仓库不会保存 App Secret、access token、refresh token 或 OAuth code。

常见问题：

- 缺少 Node.js、npm 或 npx：先安装 Node.js LTS，再执行 `sh lark-cli.sh doctor`。
- `npm install -g` 权限不足：安装器会先检测 npm 全局目录是否可写；不可写时在交互终端触发 `sudo` 密码提示。若你拒绝 sudo，安装器会继续询问是否改装到用户级 fallback 路径，默认是 `~/.local/npm`。
- 使用 fallback 路径后找不到 `lark-cli`：把 `export PATH="$HOME/.local/npm/bin:$PATH"` 加入 `~/.zshrc` 或 `~/.bashrc`，然后重新打开终端。
- 安装后找不到 `lark-cli`：执行 `sh lark-cli.sh doctor`，按提示把 npm 全局 bin 目录加入 `PATH`。
- OAuth 授权码过期或授权中断：重新执行 `sh lark-cli.sh login`。
- 权限不足：按飞书官方授权页面补充应用或用户权限后，重新执行 `sh lark-cli.sh login`。
- 非交互安装默认跳过 Lark CLI：使用 `INSTALL_LARK_CLI=1` 显式启用。

### Skill 安装位置

安装器默认会询问 Active 项目根目录和目标插件：

- Codex：`<Active 项目根目录>/.codex/skills/`
- GitHub Copilot：`<Active 项目根目录>/.github/skills/`

也可以直接指定 skills 目录：

```bash
PROJECT_DIR="$(pwd)" SKILL_INSTALL_DIR="/path/to/project/.codex/skills" sh install.sh
```

安装结果是一个软链接：

```text
/path/to/project/.codex/skills/active-jira -> /path/to/active-jira-workflow/active-jira
/path/to/project/.codex/skills/active-jira-report -> /path/to/active-jira-workflow/active-jira-report
/path/to/project/.codex/skills/active-lark -> /path/to/active-jira-workflow/active-lark
```

这样仓库更新后，Skill 内容会跟随源码目录同步更新。

## SKILL 介绍与用法

这个仓库现在拆成三个并列 Skill：

- `active-jira`：通用 Jira 能力底座，负责查询、查看、编辑、流转等原子能力。
- `active-jira-report`：场景化工作流，负责报告整理、项目规则汇总、按约定创建缺陷 Jira。
- `active-lark`：飞书/Lark 通用能力底座，负责通过官方 `lark-cli` 操作文档、消息、日历、表格、任务、多维表格、云空间、Wiki 等资源。

### `active-lark`

基础能力来自本地官方 `lark-cli` 命令，Agent 会优先使用带 `+` 的快捷命令，并在必要时退到 generated API 或 raw OpenAPI：

```bash
lark-cli auth status --verify
lark-cli docs +create --api-version v2 --doc-format markdown --content @report.md
lark-cli docs +fetch --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --doc-format markdown --format json
lark-cli docs +update --api-version v2 --doc '<DOC_URL_OR_TOKEN>' --command append --doc-format markdown --content @appendix.md
lark-cli im +chat-search --query 'project group' --format table
lark-cli im +messages-send --chat-id 'oc_xxx' --text 'hello' --dry-run
lark-cli calendar +agenda --format table
lark-cli sheets +read --url '<SHEET_URL>' --range 'A1:E20'
lark-cli base +record-list --base-token '<BASE_TOKEN>' --table-id '<TABLE_ID_OR_NAME>' --format json
lark-cli task +search --query 'release' --format json
```

发布本地 Markdown 报告到飞书文档时，也可以使用仓库脚本：

```bash
python active-lark/scripts/publish_markdown_doc.py doc/active-jira-report-长期未处理Jira报告查询.md --dry-run
python active-lark/scripts/publish_markdown_doc.py doc/active-jira-report-长期未处理Jira报告查询.md
```

长期未处理 Jira 报告也有端到端发布入口，可生成报告、创建飞书文档，并在提供 `chat_id` 后推送到飞书群聊：

```bash
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py --project GENEVA --age 1w --dry-run
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py --project GENEVA --age 1w --report-input reports/geneva-stale-jira.md --chat-id oc_xxx --grant-chat-view --dry-run
```

发送消息、创建日程、覆盖文档、删除文件、审批等写操作都属于外部副作用；`active-lark` 会要求目标、内容和身份明确，并优先使用 `--dry-run` 预览。

### `active-jira`

基础能力来自本地 `jira` 命令，Agent 会优先使用可解析的输出：

```bash
jira issue list --raw -q '<JQL>'
jira issue view ISSUE-1 --raw
jira epic list --table --plain
jira sprint list --table --plain --columns id,name,start,end,state
jira project list
jira board list -p PROJECT
jira me
jira serverinfo
```

当用户明确要求修改 Jira 时，Skill 也提供正确的 jira-cli 命令提示，例如：

```bash
jira issue create -tTask -s"Summary" -b"Description" --no-input
jira issue edit ISSUE-1 -s"New summary" --no-input
jira issue move ISSUE-1 "In Progress" --comment "Started working on it"
jira issue comment add ISSUE-1 "Comment body"
jira issue assign ISSUE-1 $(jira me)
```

删除类命令属于高风险操作，只有在用户明确要求时才应执行：

```bash
jira issue delete ISSUE-1
jira issue delete ISSUE-1 --cascade
```

### `active-jira-report`

这个 Skill 负责把 Jira 数据整理成适合项目汇报和规则执行的结果，比如：

- GENEVA 过期未关闭 Jira 查询
- 按 assignee / status / risk 汇总 Jira
- 生成周报、发布风险报告、遗留问题报告
- 按项目要求创建 defect Jira，并优先复用已有字段约定

用户可以直接对 Agent 说：

```text
帮我按 GENEVA 项目要求整理一份 Jira 周报
帮我汇总这个项目的 Jira 风险，突出 blocker 和超过一周未关闭的问题
帮我创建一个新的 defect Jira，按项目规范自动填写字段
```

### GENEVA 过期未关闭 Jira 查询

这是当前内置的 Active 场景化用法。用户可以直接对 Agent 说：

```text
帮我查询GENEVA项目超过1周没有关闭的Jira
```

Skill 会使用仓库内脚本：

```bash
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w
```

常用变体：

```bash
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1mo
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 14d
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w --assignee-current-user
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w --dry-run
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w --output reports/geneva-stale-jira.md
```

输出 Markdown 报告固定包含查询信息、开头 Highlight、按归属Team分组的完整 Jira 清单，以及文档末尾汇总。Highlight 用于给 PM/PL 快速识别最应该立即修复或确认责任人的 Jira，表格固定为：

| Jira | 紧急程度 | 超期天数 | 状态 | 责任人 | 推荐理由 | 摘要 |
| --- | --- | --- | --- | --- | --- | --- |

Jira 清单会先按 `归属Team` 分组，每组给出数量、状态分布、紧急程度分布、未分配责任人数量、平均超期、最久未处理和责任人 Top 3，然后列出该组全部 Jira。组内表格固定为：

| 排序 | Jira | Severity/紧急程度 | 创建时间 | 超期时长(天) | 状态 | 责任人 | 问题摘要 | 评论摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

文档末尾汇总包含总数、状态分布、紧急程度分布、未分配数量、最久未处理 Jira、责任人数量 Top 5、最久未处理 Top 5、评论抓取策略、紧急程度字段来源和归属Team字段来源。

默认 JQL 语义：

```jql
project = GENEVA AND created <= "YYYY-MM-DD" AND status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved
```

这个场景和 jira-cli 的通用能力是分开的：通用能力负责“怎么查 Jira”，场景化脚本负责“Active/Geneva 业务口径是什么、结果怎么展示”。

Markdown 报告生成后，Agent 会先询问是否继续创建飞书云文档并发送到指定群组。用户确认后，优先复用已经生成的报告文件，避免重复查询 Jira。`--dry-run` 会预览飞书写请求；真正发送前请先确认稳定的 `oc_...` 群聊 ID：

```bash
python active-jira-report/scripts/publish_stale_jira_report_to_lark.py \
  --project GENEVA \
  --age 1w \
  --report-input reports/geneva-stale-jira.md \
  --chat-id oc_xxx \
  --grant-chat-view \
  --dry-run
```

确认后去掉 `--dry-run` 即可创建飞书文档、为目标群授予查看权限，并发送文档链接。也可以用 `--doc <DOC_URL_OR_TOKEN> --doc-command append|overwrite` 更新已有文档，用 `--parent-token` 或 `--parent-position` 指定新文档位置。

如果你只想安装其中一个 Skill，也可以覆盖默认行为：

```bash
PROJECT_DIR="$(pwd)" SKILL_REL_PATH="active-jira" sh install.sh skills
PROJECT_DIR="$(pwd)" SKILL_REL_PATH="active-jira-report" sh install.sh skills
PROJECT_DIR="$(pwd)" SKILL_REL_PATH="active-lark" sh install.sh skills
PROJECT_DIR="$(pwd)" SKILL_REL_PATHS="active-jira active-jira-report active-lark" sh install.sh skills
```

## 维护与更新

更新源码和 jira-cli：

```bash
active-jira update
```

仅查看版本：

```bash
active-jira version
```

如果源码目录有本地修改，更新命令不会自动覆盖。请先提交或处理本地修改后再执行更新。

## 新功能迭代约定

本仓库会持续增加新的 Jira、报告和飞书自动化能力。新增功能时，建议同步维护这些位置，避免 README 和 Skill 行为脱节：

- `README.md`：在“能力概览”和“常用入口速查”中补充用户最常用命令。
- `active-*/SKILL.md`：补充 Agent 触发条件、执行流程、安全边界和 dry-run 策略。
- `active-*/references/`：沉淀字段规则、报告口径、CLI 使用细节等长期参考资料。
- `active-*/scripts/`：新增脚本时保持参数可发现，至少支持 `--help`；涉及外部写操作时优先支持 `--dry-run`。
- `doc/`：记录设计方案、任务拆分、验收清单和外部依赖变化。

涉及 Jira 创建/编辑、飞书文档写入、权限授权、消息发送等外部副作用时，文档中必须写清楚目标对象、身份、权限要求和回滚或重试注意事项。

## 作者与版权

作者：Gan GAN

所属机构：Zepp Health, Active BU AI Lab

Copyright (c) 2026 Zepp Health. All rights reserved.
