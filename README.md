# zeppos-jira-workflow

`zeppos-jira-workflow` 是 ZeppOS 团队使用 Jira 的 Agent 工作流仓库。它把本地开源工具 [`ankitpokhrel/jira-cli`](https://github.com/ankitpokhrel/jira-cli) 封装成一个可安装的 Skill，让 Codex 或 GitHub Copilot 这类 Agent 在需要查询 Jira 时，能按固定方式构造 JQL、调用本地 `jira` 命令，并把结果整理成稳定输出。

当前内置的 ZeppOS 场景包括：

- 查询 Jira issue、epic、sprint、release、project、board 等通用 Jira 信息。
- 查看、创建、编辑、流转、评论、指派、链接、克隆、关注 Jira issue。
- 查询 `GENEVA` 项目中超过指定时间仍未关闭的 Jira，并输出标准 Markdown 表格。

## 仓库摘要

仓库主要内容：

```text
install.sh                         一键安装、更新、配置入口
jira-cli.sh                        Linux 下安装/更新 ankitpokhrel/jira-cli 的辅助脚本
VERSION                            仓库版本
zeppos-jira/SKILL.md               Agent Skill 主说明
zeppos-jira/references/            jira-cli 用法参考
zeppos-jira/scripts/               场景化查询脚本
zeppos-jira/agents/openai.yaml     Skill 展示信息
```

安装后会得到三部分能力：

- 源码目录：默认安装到当前目录下的 `zeppos-jira-workflow/`。
- Skill 软链接：安装到 Codex 或 GitHub Copilot 项目的 skills 目录。
- 本地管理命令：默认安装为 `~/.local/bin/zeppos-jira`，用于后续更新和查看版本。

## 分发方式

推荐分发方式是一行安装脚本：

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"
```

也可以指定源码安装父目录：

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)" -- /path/to/parent
```

源码会被放到：

```text
/path/to/parent/zeppos-jira-workflow
```

如果需要先手动克隆仓库，也可以在仓库内执行：

```bash
git clone https://github.com/active-ailab/zeppos-jira-workflow.git
cd zeppos-jira-workflow
PROJECT_DIR="$(pwd)" sh install.sh
```

从已克隆源码目录直接运行 `install.sh` 时，建议显式设置 `PROJECT_DIR="$(pwd)"`，表示复用当前源码目录。

## 安装

交互式完整安装：

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"
```

安装流程会依次做这些事：

1. 下载或更新本仓库源码。
2. 检查本地是否存在 `jira` 命令。
3. 如果缺少 `jira`，在 Linux 环境下通过 `jira-cli.sh` 安装 `ankitpokhrel/jira-cli`。
4. 执行 `jira init`，生成 JiraCLI 配置。
5. 将 `zeppos-jira` Skill 软链接到目标 Agent 的 skills 目录。
6. 安装本地管理命令 `zeppos-jira`。

常用命令：

```bash
# 只安装/更新 Skill 和本地管理命令，不重新初始化 jira-cli
zeppos-jira skills

# 更新本仓库源码，并检查/更新 jira-cli
zeppos-jira update

# 查看安装器、源码、jira-cli 版本
zeppos-jira version

# 查看安装器帮助
zeppos-jira help
```

如果 `~/.local/bin` 不在 `PATH` 中，请把下面这行加入 `~/.zshrc` 或 `~/.bashrc`：

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
SKILL_PROJECT_ROOT="/path/to/zeppos/project" \
SKILL_PLUGIN="codex" \
sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"
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

### Skill 安装位置

安装器默认会询问 ZeppOS 项目根目录和目标插件：

- Codex：`<ZeppOS 项目根目录>/.codex/skills/`
- GitHub Copilot：`<ZeppOS 项目根目录>/.github/skills/`

也可以直接指定 skills 目录：

```bash
PROJECT_DIR="$(pwd)" SKILL_INSTALL_DIR="/path/to/project/.codex/skills" sh install.sh
```

安装结果是一个软链接：

```text
/path/to/project/.codex/skills/zeppos-jira -> /path/to/zeppos-jira-workflow/zeppos-jira
```

这样仓库更新后，Skill 内容会跟随源码目录同步更新。

## SKILL 介绍与用法

`zeppos-jira` Skill 的定位是“Jira 能力底座 + ZeppOS 场景化查询”。

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

### GENEVA 过期未关闭 Jira 查询

这是当前内置的 ZeppOS 场景化用法。用户可以直接对 Agent 说：

```text
帮我查询GENEVA项目超过1周没有关闭的Jira
```

Skill 会使用仓库内脚本：

```bash
python zeppos-jira/scripts/query_stale_jiras.py --project GENEVA --age 1w
```

常用变体：

```bash
python zeppos-jira/scripts/query_stale_jiras.py --project GENEVA --age 1mo
python zeppos-jira/scripts/query_stale_jiras.py --project GENEVA --age 14d
python zeppos-jira/scripts/query_stale_jiras.py --project GENEVA --age 1w --assignee-current-user
python zeppos-jira/scripts/query_stale_jiras.py --project GENEVA --age 1w --dry-run
```

输出表格固定为：

| Jira | Assignee | Status | Created | Summary |
| --- | --- | --- | --- | --- |

默认 JQL 语义：

```jql
project = GENEVA AND created <= "YYYY-MM-DD" AND status in (Open, "In Progress", Reopened, Resolved, "In Review", Pending) AND resolution = Unresolved
```

这个场景和 jira-cli 的通用能力是分开的：通用能力负责“怎么查 Jira”，场景化脚本负责“ZeppOS/Geneva 业务口径是什么、结果怎么展示”。

## 维护与更新

更新源码和 jira-cli：

```bash
zeppos-jira update
```

仅查看版本：

```bash
zeppos-jira version
```

如果源码目录有本地修改，更新命令不会自动覆盖。请先提交或处理本地修改后再执行更新。
