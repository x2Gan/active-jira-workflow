# Active Lark CLI 接入方案

## 1. 背景

`active-jira-workflow` 当前已经能通过 JiraCLI 查询 Jira、生成规则化 Markdown 报告，并把报告保存为本地文档。下一步希望把报告链路继续延伸到飞书：

1. Agent 生成 Jira 报告 Markdown。
2. Agent 通过飞书 CLI 将 Markdown 创建为飞书云文档。
3. 后续可将飞书文档链接发送给指定用户、群或项目相关对象。

为避免把飞书安装、鉴权和升级逻辑硬塞进现有 Jira 安装器，建议新增一个独立的 `lark-cli.sh`，专门负责飞书 CLI 的安装、配置、登录、状态检查和升级管理；再由主安装器 `install.sh` 在交互流程中可选调用。

## 2. 官方依据

飞书官方安装指南给出的 Agent 安装流程如下：

```sh
# 安装 CLI
npm install -g @larksuite/cli

# 安装 CLI Skill
npx -y skills add https://open.feishu.cn --skill -y

# 配置应用凭证
lark-cli config init --new

# 登录授权
lark-cli auth login --recommend

# 验证状态
lark-cli auth status
```

官方文档：

- 飞书 CLI 安装指南: https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md
- 飞书 CLI 能力说明: https://open.feishu.cn/document/mcp_open_tools/feishu-cli-let-ai-actually-do-your-work-in-feishu
- 开源仓库: https://github.com/larksuite/cli

关键结论：

- 飞书 CLI 使用 Node.js/npm 分发，推荐通过 npm 全局安装。
- CLI Skill 是 Agent 使用飞书能力的关键部分，需要单独安装。
- `config init` 和 `auth login` 都可能需要用户在浏览器中完成确认，不能完全无人值守。
- 未登录用户身份时，仍可使用部分应用身份能力；但访问个人文档、日历、消息、私有资源时通常需要用户授权。
- 对本项目最重要的能力是 `lark-cli docs +create --api-version v2 --doc-format markdown`，可把现有 Jira Markdown 报告创建为飞书云文档。

## 3. 目标

### 3.1 功能目标

新增 `lark-cli.sh`，提供独立的飞书 CLI 管理入口：

- 检查 Node.js、npm、npx、PATH、`lark-cli` 等环境状态。
- 安装 `@larksuite/cli`。
- 安装飞书 CLI Skill。
- 初始化飞书应用配置。
- 引导用户完成飞书 OAuth 登录。
- 检查当前登录和授权状态。
- 升级飞书 CLI 和 Skill。
- 为后续“Jira 报告发布到飞书文档”提供稳定基础。

在 `install.sh` 主流程中追加可选接入：

- 安装 Jira 工作流时检查当前 Lark CLI 状态。
- 询问用户是否继续安装和配置 Lark CLI。
- 默认不安装。
- 交互提示中说明安装目的：用于将生成的 Jira 报告继续生成飞书文档，并发送给指定对象。

### 3.2 非目标

本阶段不直接实现完整的“发送给指定对象”业务流。建议先完成安装和鉴权基础，再分阶段添加：

- 阶段 1: 创建飞书文档并输出 URL。
- 阶段 2: 支持给用户或群发送文档链接。
- 阶段 3: 支持权限配置、Wiki 挂载、模板化报告发布。

本阶段也不自研飞书 OpenAPI 鉴权逻辑。应用配置、OAuth、token 存储、权限申请全部交给官方 `lark-cli` 处理。

## 4. 总体设计

建议采用“两层入口”的结构：

```text
install.sh
  └─ 可选调用 lark-cli.sh bootstrap

lark-cli.sh
  ├─ doctor       环境与状态检查
  ├─ install      安装 CLI 和 Skill
  ├─ config       初始化飞书应用配置
  ├─ login        用户授权登录
  ├─ status       查看登录状态
  ├─ update       升级 CLI 和 Skill
  ├─ bootstrap    一键安装 + 配置 + 登录 + 验证
  └─ help         帮助
```

`install.sh` 只负责询问和调用，不复制飞书 CLI 的细节。这样主安装器仍然是 Jira 工作流安装器，飞书能力作为可选增强模块存在。

## 5. `lark-cli.sh` 命令设计

### 5.1 `doctor`

用途：只读检查，不产生副作用。

检查项：

- `node` 是否存在及版本。
- `npm` 是否存在及版本。
- `npx` 是否存在。
- `lark-cli` 是否存在。
- 全局 npm bin 目录是否在 `PATH` 中。
- 当前飞书登录状态，若 `lark-cli` 已安装则执行 `lark-cli auth status`。

建议输出：

```text
== Lark CLI 环境检查 ==
Node.js: v20.20.1
npm: 10.8.2
npx: /usr/bin/npx
lark-cli: not installed
auth: not checked

建议:
  - 执行 ./lark-cli.sh install 安装飞书 CLI
```

### 5.2 `install`

用途：安装飞书 CLI 和 Skill，但不强制登录。

执行步骤：

1. 检查 `node`、`npm`、`npx`。
2. 执行 `npm install -g @larksuite/cli`。
3. 执行 `npx -y skills add https://open.feishu.cn --skill -y`。
4. 检查 `lark-cli` 是否可用。
5. 提示用户是否需要继续执行 `config` 和 `login`，或建议使用 `bootstrap`。

安装应保持幂等：

- 已安装时仍可重复执行 npm 安装，等价于刷新到当前 npm 解析版本。
- Skill 安装命令可重复执行。
- 不在仓库中保存任何飞书凭据。

### 5.3 `config`

用途：初始化飞书应用配置。

执行命令：

```sh
lark-cli config init --new
```

注意事项：

- 该命令会触发浏览器配置流程或输出授权链接。
- Agent 应把授权链接展示给用户，由用户在浏览器中完成确认。
- 如果用户已有飞书应用配置，后续可以扩展 `--existing` 或 `--no-new` 模式，但 MVP 先使用官方推荐的 `--new`。

### 5.4 `login`

用途：完成用户身份授权。

执行命令：

```sh
lark-cli auth login --recommend
```

注意事项：

- 该命令需要用户在浏览器中确认授权。
- `--recommend` 使用官方推荐权限，适合 Agent 初次接入。
- 未来若只需要文档能力，可扩展 `--domain doc` 或精确 scope 模式，降低授权范围。

### 5.5 `status`

用途：查看当前飞书 CLI 状态。

执行命令：

```sh
lark-cli auth status
```

建议行为：

- 如果 `lark-cli` 不存在，提示执行 `install`。
- 如果未登录，提示执行 `login`。
- 如果登录正常，显示当前状态并返回成功。

### 5.6 `update`

用途：升级飞书 CLI 和刷新 Skill。

执行步骤：

```sh
npm install -g @larksuite/cli@latest
npx -y skills add https://open.feishu.cn --skill -y
lark-cli auth status
```

可选增强：

- 使用 `npm view @larksuite/cli version` 查询最新版本。
- 使用 `npm list -g @larksuite/cli --depth=0` 或 `lark-cli --version` 查询本地版本。
- 更新前后打印版本差异。

### 5.7 `bootstrap`

用途：面向主安装流程的一键入口。

建议执行顺序：

1. `doctor`
2. `install`
3. `config`
4. `login`
5. `status`

该命令可以做到“一键拉起完整流程”，但必须明确提示用户：

- 中途需要浏览器确认。
- 用户可以随时中止。
- 登录授权范围以飞书官方页面展示为准。
- 本项目不会读取或保存飞书 token。

## 6. `install.sh` 接入设计

### 6.1 交互策略

主流程应在 JiraCLI、Active Jira Skill、本地管理命令安装完成后，追加一个可选步骤：

```text
[6/6] 可选安装 Lark CLI
检测到本项目可以通过 Lark CLI 将生成的 Jira Markdown 报告发布为飞书云文档，
并在后续发送给指定用户或群。该步骤需要安装官方飞书 CLI，并可能要求你在浏览器中完成飞书授权。

是否现在安装并配置 Lark CLI？[y/N]:
```

默认值必须是 `N`，避免用户在只需要 Jira 能力时被动安装飞书工具。

### 6.2 非交互策略

建议新增环境变量：

```sh
INSTALL_LARK_CLI="${INSTALL_LARK_CLI:-prompt}"
LARK_CLI_SETUP_MODE="${LARK_CLI_SETUP_MODE:-bootstrap}"
LARK_CLI_SCRIPT_REL_PATH="${LARK_CLI_SCRIPT_REL_PATH:-lark-cli.sh}"
```

行为规则：

- `INSTALL_LARK_CLI=1`: 不询问，直接执行 `lark-cli.sh bootstrap`。
- `INSTALL_LARK_CLI=0`: 跳过。
- 未设置或 `prompt`: 交互终端中询问，默认不安装；非交互终端中跳过。
- `LARK_CLI_SETUP_MODE=install`: 只安装 CLI 和 Skill，不执行配置和登录。
- `LARK_CLI_SETUP_MODE=bootstrap`: 安装、配置、登录、验证完整流程。

### 6.3 主流程边界

`install.sh` 不应直接写入飞书相关逻辑细节，只做：

1. 检查 `lark-cli.sh` 是否存在。
2. 检查当前 `lark-cli` 状态，用于生成提示文案。
3. 询问用户是否安装。
4. 根据选择执行：

```sh
sh "$PROJECT_DIR/lark-cli.sh" "$LARK_CLI_SETUP_MODE"
```

这样未来飞书 CLI 安装流程变化时，只需要更新 `lark-cli.sh`。

## 7. 与 Jira 报告链路的关系

现有报告生成链路：

```sh
python active-jira-report/scripts/generate_stale_jira_report.py --project GENEVA --age 1w
```

后续发布到飞书文档的最小命令：

```sh
lark-cli docs +create \
  --api-version v2 \
  --doc-format markdown \
  --content "$(cat doc/active-jira-report-长期未处理Jira报告查询.md)"
```

建议后续新增一个独立发布脚本或 Skill 工作流，而不是直接塞进安装脚本：

```text
active-jira-report
  ├─ 生成 Markdown 报告
  ├─ 调用 lark-cli docs +create 创建飞书文档
  ├─ 获取文档 URL
  ├─ 可选配置文档权限
  └─ 可选发送给指定用户或群
```

最小可行业务闭环：

1. 用户要求查询长期未处理 Jira。
2. Agent 生成本地 Markdown 报告。
3. 如果检测到 Lark CLI 已配置，Agent 询问是否发布到飞书文档。
4. 用户确认后创建飞书文档。
5. Agent 返回飞书文档 URL。

发送能力建议作为下一阶段：

- 先通过用户或群名解析目标对象。
- 再设置文档权限。
- 最后通过 IM 发送文档链接。

## 8. 安全与权限

安全原则：

- 不在本仓库保存 App Secret、access token、refresh token 或 OAuth code。
- 不把飞书授权链接、token、用户私有信息写入日志文件。
- 不绕过飞书官方授权页面。
- 不默认安装或登录飞书 CLI。
- 不在 `install.sh` 中静默申请飞书权限。
- 所有会产生外部副作用的发布、发送、授权操作都应有明确用户确认。

权限建议：

- 初期使用 `lark-cli auth login --recommend`，以官方推荐权限快速跑通。
- 稳定后可为“仅发布 Jira 报告”收敛到文档、云空间、IM 相关权限。
- 如果只是创建文档并返回 URL，不应默认发送消息。
- 如果要发送给群或用户，应在发送前展示目标对象和文档标题。

## 9. 错误处理

`lark-cli.sh` 应覆盖以下常见错误：

| 场景 | 处理建议 |
| --- | --- |
| 缺少 Node.js | 提示安装 Node.js LTS，并停止安装 |
| 缺少 npm/npx | 提示修复 Node.js/npm 环境 |
| npm 全局安装权限不足 | 提示配置用户级 npm prefix、使用 nvm/volta，或由用户自行处理权限 |
| npm 安装成功但找不到 `lark-cli` | 检查 npm 全局 bin 目录是否在 `PATH` 中，并输出 PATH 修复提示 |
| Skill 安装失败 | 保留 CLI 安装结果，提示用户重试 `npx -y skills add https://open.feishu.cn --skill -y` |
| `config init` 中断 | 提示可稍后执行 `./lark-cli.sh config` |
| OAuth 登录超时 | 提示重新执行 `./lark-cli.sh login` |
| 权限不足 | 提示根据 `lark-cli` 报错补充授权，或执行 `lark-cli auth login --recommend` |

## 10. 实现建议

### 10.1 脚本风格

`lark-cli.sh` 建议采用 POSIX `sh`，与当前 `install.sh` 保持一致：

```sh
#!/usr/bin/env sh
set -eu
```

建议复用当前安装器的基础 helper 风格：

- `say`
- `warn`
- `die`
- `has_cmd`
- `need_cmd`
- `section`
- `summary_item`
- `is_disabled`

但不建议从 `install.sh` source 这些函数，避免两个脚本互相耦合。可以在 `lark-cli.sh` 内保留一份小而独立的 helper。

### 10.2 版本检测

可使用：

```sh
npm view @larksuite/cli version
npm list -g @larksuite/cli --depth=0
lark-cli --version
lark-cli version
```

由于不同版本 CLI 的 version 命令可能变化，脚本应宽容处理：

- 优先 `lark-cli --version`。
- 失败则尝试 `lark-cli version`。
- 仍失败则只显示命令路径。

### 10.3 npm PATH 检查

建议通过：

```sh
npm config get prefix
```

推导全局 bin 目录：

```text
<npm-prefix>/bin
```

如果 `lark-cli` 安装后仍不可见，输出类似提示：

```sh
export PATH="<npm-prefix>/bin:$PATH"
```

## 11. 推荐文件改动

本需求建议分三步实现：

### 第一步：新增 `lark-cli.sh`

实现命令：

- `help`
- `doctor`
- `install`
- `config`
- `login`
- `status`
- `update`
- `bootstrap`

### 第二步：接入 `install.sh`

新增：

- Lark CLI 相关环境变量。
- Lark CLI 状态检查函数。
- Lark CLI 安装询问函数。
- 安装总结中的 Lark CLI 状态。
- `install_flow` 末尾的可选 Lark CLI 步骤。

默认交互不安装，非交互不安装。

### 第三步：补充 README

在 README 中补充：

- 为什么需要 Lark CLI。
- 如何单独安装：

```sh
sh lark-cli.sh bootstrap
```

- 如何在主安装器中启用：

```sh
INSTALL_LARK_CLI=1 sh install.sh
```

- 如何升级：

```sh
sh lark-cli.sh update
```

## 11.1 当前实现状态

截至 2026-04-30，仓库已按本方案落地以下能力：

- `lark-cli.sh` 已提供 `help`、`doctor`、`install`、`config`、`login`、`status`、`update`、`bootstrap`。
- `install.sh` 已接入默认关闭的 Lark CLI 可选步骤，支持 `INSTALL_LARK_CLI=prompt|1|0` 和 `LARK_CLI_SETUP_MODE=bootstrap|install`。
- README 已补充 Lark CLI 的可选定位、主安装器启用方式、单独安装方式和常见故障排查。

仍需在真实飞书环境中执行 `sh lark-cli.sh install`、`config`、`login`、`bootstrap` 以及主安装器 `INSTALL_LARK_CLI=1` 路径，完成外部副作用相关验收。

## 12. 验收标准

### 12.1 `lark-cli.sh`

- 在缺少 Node.js 时，`doctor` 能给出明确错误，不执行安装。
- 在已有 Node/npm/npx 但缺少 `lark-cli` 时，`install` 能安装 CLI 和 Skill。
- 重复执行 `install` 不会破坏已有配置。
- `bootstrap` 能按官方流程拉起安装、配置、登录、验证。
- `update` 能升级 `@larksuite/cli` 并刷新 Skill。
- `status` 能清楚区分未安装、未登录、已登录三类状态。

### 12.2 `install.sh`

- 默认交互时询问是否安装 Lark CLI，默认选项为 `N`。
- 用户直接回车时不安装 Lark CLI。
- `INSTALL_LARK_CLI=0` 时不询问、不安装。
- `INSTALL_LARK_CLI=1` 时自动调用 `lark-cli.sh bootstrap`。
- 非交互环境中未设置 `INSTALL_LARK_CLI=1` 时自动跳过。
- 提示文案明确说明用途：为了把 Jira 报告继续生成飞书文档，并发送给指定对象。

### 12.3 报告发布准备

- 安装完成后，执行 `lark-cli auth status` 能看到有效登录状态。
- 对已有 Markdown 报告可手动执行 `lark-cli docs +create --api-version v2 --doc-format markdown` 创建飞书文档。
- 创建成功后能拿到飞书文档 URL。

## 13. 推荐实施顺序

1. 先提交本设计文档，统一范围和交互边界。
2. 实现 `lark-cli.sh doctor/install/status/update`，先覆盖无浏览器授权的部分。
3. 增加 `config/login/bootstrap`，跑通官方完整流程。
4. 在 `install.sh` 中加入默认关闭的可选调用。
5. 用一台未安装 `lark-cli` 的机器验证全流程。
6. 再设计 Jira 报告发布到飞书文档的具体命令或 Skill 工作流。

## 14. 最终建议

本需求具备明确可行性，推荐采用“独立脚本 + 主安装器可选调用”的方案：

- `lark-cli.sh` 负责飞书 CLI 的完整生命周期。
- `install.sh` 只负责发现、询问和调用。
- 默认不安装，避免扩大安装器副作用。
- 先打通 Jira Markdown 报告到飞书文档的最小闭环，再扩展权限配置和消息发送。

这种设计能保持现有 Jira 工作流稳定，同时为团队报告自动发布到飞书留出清晰、可维护的演进路径。
