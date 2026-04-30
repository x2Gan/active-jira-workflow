# Active Lark CLI 工程任务拆分

## 1. 任务目标

基于 `doc/active-lark-cli-design.md`，将飞书 CLI 接入拆成可执行工程任务。最终交付目标是：

1. 新增独立脚本 `lark-cli.sh`，负责飞书 CLI 的环境检查、安装、配置、登录、状态检查和升级。
2. 将 Lark CLI 安装作为 `install.sh` 主流程的可选增强步骤，默认不安装。
3. 为后续“Jira Markdown 报告 -> 飞书云文档 -> 发送给指定对象”的自动化链路打好基础。

本任务清单按阶段推进，前一阶段稳定后再进入下一阶段。

## 2. 阶段总览

| 阶段 | 名称 | 主要产物 | 风险等级 |
| --- | --- | --- | --- |
| P0 | 设计冻结与基线确认 | 设计文档、任务拆分、当前安装器边界确认 | 低 |
| P1 | `lark-cli.sh` 最小可用版本 | `doctor/install/status/update/help` | 中 |
| P2 | 飞书配置与登录流程 | `config/login/bootstrap` | 中 |
| P3 | 接入 `install.sh` 主流程 | 默认关闭的可选安装入口 | 中 |
| P4 | 文档与用户指引 | README、设计文档补充、故障排查 | 低 |
| P5 | 报告发布能力预研与铺垫 | 发布命令草案、Skill 工作流方案 | 中 |

## 3. P0 设计冻结与基线确认

### P0.1 确认官方命令

- [ ] 固化官方安装命令：

```sh
npm install -g @larksuite/cli
npx -y skills add larksuite/cli -g -y
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

- [ ] 在设计文档中保留官方文档链接。
- [ ] 明确 `config init` 和 `auth login` 需要用户浏览器确认，不能无人值守。

验收：

- [ ] `doc/active-lark-cli-design.md` 已描述官方依据、边界和非目标。
- [ ] `doc/active-lark-cli-todo.md` 已覆盖任务拆分。

### P0.2 确认当前仓库状态

- [x] 确认 `install.sh` 当前职责仍是 Active Jira 工作流安装器。
- [x] 确认 `lark-cli.sh` 是独立入口，不被 Jira 初始化逻辑污染。
- [x] 确认未跟踪或用户修改文件不会被覆盖。

验收：

```sh
git status --short
```

需要确认：

- [x] 本次只改动目标文件。
- [x] 不回滚用户已有改动。

## 4. P1 `lark-cli.sh` 最小可用版本

目标：先实现不依赖浏览器授权的命令，让脚本具备安装、升级、检查能力。

### P1.1 创建脚本骨架

文件：`lark-cli.sh`

- [x] 添加 shebang 和严格模式：

```sh
#!/usr/bin/env sh
set -eu
```

- [x] 添加基础 helper：
  - [x] `say`
  - [x] `warn`
  - [x] `die`
  - [x] `has_cmd`
  - [x] `need_cmd`
  - [x] `section`
  - [x] `summary_item`
  - [x] `is_disabled`
- [x] 添加 `usage`。
- [x] 添加命令分发：
  - [x] `help`
  - [x] `doctor`
  - [x] `install`
  - [x] `status`
  - [x] `update`
  - [x] 预留 `config/login/bootstrap`

验收：

```sh
sh -n lark-cli.sh
sh lark-cli.sh help
```

### P1.2 实现环境检测

命令：`doctor`

检查项：

- [x] `node` 是否存在。
- [x] `node -v`。
- [x] `npm` 是否存在。
- [x] `npm -v`。
- [x] `npx` 是否存在。
- [x] `lark-cli` 是否存在。
- [x] npm prefix 和全局 bin 目录。
- [x] npm global root 写权限。
- [x] 全局 bin 是否在 `PATH`。
- [x] 如果 `lark-cli` 存在，尝试获取版本。
- [x] 如果 `lark-cli` 存在，尝试执行 `lark-cli auth status`，失败不导致 `doctor` 整体退出。

建议实现函数：

- [x] `get_npm_prefix`
- [x] `get_npm_global_bin`
- [x] `get_npm_global_root`
- [x] `is_path_contains`
- [x] `get_lark_cli_version`
- [x] `print_path_hint`

验收：

```sh
sh lark-cli.sh doctor
```

预期：

- [x] 缺少 `lark-cli` 时能明确显示 `not installed`。
- [x] 不会因为未登录而失败退出。
- [x] PATH 问题有可复制的修复提示。

### P1.3 实现安装命令

命令：`install`

执行步骤：

- [x] 检查 `node/npm/npx`。
- [x] 安装前检测 npm 全局目录写权限；需要时触发 `sudo`。
- [x] 用户拒绝 `sudo` 后询问是否安装到 fallback 路径。
- [x] 用户拒绝 fallback 后结束安装流程。
- [x] 执行 `npm install -g @larksuite/cli`。
- [x] 执行 `npx -y skills add larksuite/cli -g -y`。
- [x] 检查 `lark-cli` 是否可用。
- [x] 如果不可用，输出 npm global bin 的 PATH 修复提示。
- [x] 安装完成后提示后续命令：

```sh
sh lark-cli.sh config
sh lark-cli.sh login
sh lark-cli.sh status
```

环境变量建议：

- [x] `LARK_CLI_NPM_PACKAGE="${LARK_CLI_NPM_PACKAGE:-@larksuite/cli}"`
- [x] `LARK_CLI_SKILL_SOURCE="${LARK_CLI_SKILL_SOURCE:-larksuite/cli}"`
- [x] `LARK_CLI_SKIP_SKILL="${LARK_CLI_SKIP_SKILL:-0}"`
- [x] `LARK_CLI_NPM_FALLBACK_PREFIX="${LARK_CLI_NPM_FALLBACK_PREFIX:-$HOME/.local/npm}"`

验收：

```sh
sh lark-cli.sh install
command -v lark-cli
lark-cli auth status
```

注意：

- [x] `install` 不执行 `config init`。
- [x] `install` 不执行 `auth login`。
- [x] `install` 可重复执行。

### P1.4 实现状态命令

命令：`status`

行为：

- [x] 如果没有 `lark-cli`，提示执行 `sh lark-cli.sh install` 并返回非零。
- [x] 如果有 `lark-cli`，执行 `lark-cli auth status`。
- [x] 原样展示 CLI 的状态输出。
- [x] 如果未登录，提示执行 `sh lark-cli.sh login`。

验收：

```sh
sh lark-cli.sh status
```

### P1.5 实现升级命令

命令：`update`

执行步骤：

- [x] 查询本地版本。
- [x] 查询 npm 最新版本：

```sh
npm view @larksuite/cli version
```

- [x] 执行：

```sh
npm install -g @larksuite/cli@latest
npx -y skills add larksuite/cli -g -y
```

- [x] 更新后打印版本和状态。

验收：

```sh
sh lark-cli.sh update
sh lark-cli.sh doctor
```

## 5. P2 飞书配置与登录流程

目标：实现完整官方 Agent 安装流程。

### P2.1 实现配置命令

命令：`config`

执行：

```sh
lark-cli config init --new
```

任务：

- [x] 执行前检查 `lark-cli`。
- [x] 清楚提示用户该步骤会打开浏览器或输出链接。
- [x] 明确本项目不保存 App Secret 或 token。
- [x] 命令失败时提示可重试。

验收：

```sh
sh lark-cli.sh config
```

### P2.2 实现登录命令

命令：`login`

执行：

```sh
lark-cli auth login --recommend
```

任务：

- [x] 执行前检查 `lark-cli`。
- [x] 清楚提示用户会进入 OAuth 授权。
- [x] 登录完成后自动执行 `lark-cli auth status`。
- [x] 登录失败时提示重新执行。

验收：

```sh
sh lark-cli.sh login
sh lark-cli.sh status
```

### P2.3 实现一键流程

命令：`bootstrap`

流程：

1. [x] 执行 `doctor`。
2. [x] 执行 `install`。
3. [x] 执行 `config`。
4. [x] 执行 `login`。
5. [x] 执行 `status`。

交互提示：

- [x] 开始前说明用途：用于将 Jira 报告生成飞书文档并后续发送给指定对象。
- [x] 说明中途需要用户浏览器确认。
- [x] 说明授权范围以飞书官方页面为准。

验收：

```sh
sh lark-cli.sh bootstrap
```

## 6. P3 接入 `install.sh` 主流程

目标：主安装器可选安装 Lark CLI，默认不安装。

### P3.1 增加配置变量

文件：`install.sh`

新增变量：

```sh
INSTALL_LARK_CLI="${INSTALL_LARK_CLI:-prompt}"
LARK_CLI_SETUP_MODE="${LARK_CLI_SETUP_MODE:-bootstrap}"
LARK_CLI_SCRIPT_REL_PATH="${LARK_CLI_SCRIPT_REL_PATH:-lark-cli.sh}"
```

可选 summary：

```sh
SUMMARY_LARK_CLI=""
SUMMARY_LARK_CLI_INSTALL=""
```

验收：

- [x] `install.sh help` 中说明这些变量。
- [x] launcher 生成时保留相关变量，或明确不需要保留。

### P3.2 实现 Lark CLI 状态检查函数

建议函数：

- [x] `get_lark_cli_status_summary`
- [x] `should_install_lark_cli`
- [x] `run_lark_cli_setup`

状态摘要建议：

- `not installed`
- `installed: /path/to/lark-cli`
- `installed, auth unknown`
- `installed, auth ok`
- `installed, auth needed`

验收：

- [x] 没有 `lark-cli` 时提示缺失。
- [x] 有 `lark-cli` 但未登录时提示需要登录。
- [x] 状态检查不影响 Jira 安装主流程。

### P3.3 增加交互询问

安装流程末尾追加：

```text
可选安装 Lark CLI
本项目可以通过 Lark CLI 将生成的 Jira Markdown 报告发布为飞书云文档，
并在后续发送给指定用户或群。该步骤需要安装官方飞书 CLI，
并可能要求你在浏览器中完成飞书授权。

是否现在安装并配置 Lark CLI？[y/N]:
```

任务：

- [x] 默认答案为 `N`。
- [x] 非交互环境默认跳过。
- [x] `INSTALL_LARK_CLI=1` 时不询问，直接安装。
- [x] `INSTALL_LARK_CLI=0` 时不询问，直接跳过。
- [x] `INSTALL_LARK_CLI=prompt` 时只在 TTY 中询问。

验收：

```sh
INSTALL_LARK_CLI=0 PROJECT_DIR="$(pwd)" sh install.sh skills
INSTALL_LARK_CLI=1 LARK_CLI_SETUP_MODE=install PROJECT_DIR="$(pwd)" sh install.sh skills
```

注意：

- [ ] 使用 `LARK_CLI_SETUP_MODE=install` 测试，避免 CI 或本地验证时拉起浏览器授权。

### P3.4 调整安装步骤和总结

任务：

- [x] `install_flow` 的步骤总数根据是否跳过配置步骤合理显示。
- [x] 如果 Lark CLI 是可选步骤，可以显示为“可选步骤”而不是强行改成固定 `[6/6]`。
- [x] 安装总结中加入 Lark CLI 结果：
  - [x] `已跳过`
  - [x] `已安装`
  - [x] `已安装并登录`
  - [x] `安装失败`

验收：

- [x] 不安装 Lark CLI 时总结清晰。
- [x] 安装失败时 Jira 安装结果仍能被理解。

## 7. P4 文档与用户指引

### P4.1 更新 README

文件：`README.md`

新增内容：

- [x] Lark CLI 是可选能力。
- [x] 用途：将 Jira 报告发布为飞书云文档，并后续发送给指定对象。
- [x] 默认不会安装。
- [x] 主安装器启用方式：

```sh
INSTALL_LARK_CLI=1 sh install.sh
```

- [x] 单独安装方式：

```sh
sh lark-cli.sh bootstrap
```

- [x] 只安装不登录：

```sh
sh lark-cli.sh install
```

- [x] 升级：

```sh
sh lark-cli.sh update
```

### P4.2 增加故障排查

建议加入 README 或独立 doc：

- [x] 缺少 Node.js。
- [x] npm 全局安装权限不足。
- [x] `lark-cli` 安装后命令不存在。
- [x] OAuth 授权码过期。
- [x] 权限不足。
- [x] 非交互安装中跳过 Lark CLI 的原因。

### P4.3 更新设计文档状态

文件：`doc/active-lark-cli-design.md`

- [x] 实现完成后同步实际命令和行为。
- [ ] 如果官方 CLI 命令有变化，同步更新。

## 8. P5 报告发布能力预研与铺垫

目标：不在本轮安装器中直接实现完整业务发布，但提前明确后续工作。

### P5.1 验证 Markdown 创建飞书文档

手动验证命令：

```sh
lark-cli docs +create \
  --api-version v2 \
  --doc-format markdown \
  --content @doc/active-jira-report-长期未处理Jira报告查询.md
```

任务：

- [ ] 确认 Markdown 表格渲染效果。
- [ ] 确认返回 JSON 中的文档 URL 字段。
- [ ] 确认长报告是否需要分段 append。
- [ ] 确认是否需要指定 `--parent-token` 或 `--parent-position`。

### P5.2 设计发布脚本或 Skill 工作流

候选方案：

1. [ ] 新增 `active-jira-report/scripts/publish_lark_doc.sh`。
2. [ ] 在 `active-jira-report/SKILL.md` 中加入“发布到飞书文档”工作流。
3. [ ] 不新增脚本，由 Agent 直接调用 `lark-cli docs +create`。

推荐先选方案 2 或 3，避免过早封装。

### P5.3 发送给指定对象

后续能力拆分：

- [ ] 解析目标对象：用户、群、邮箱、open_id、chat_id。
- [ ] 搜索或确认群聊。
- [ ] 配置文档权限。
- [ ] 发送文档 URL。
- [ ] 发送前展示目标对象和文档标题，要求用户确认。

注意：

- [ ] 不默认发送。
- [ ] 不默认公开文档。
- [ ] 不猜测目标对象。

## 9. 测试计划

### 9.1 静态检查

```sh
sh -n lark-cli.sh
sh -n install.sh
```

### 9.2 只读检查

```sh
sh lark-cli.sh help
sh lark-cli.sh doctor
sh lark-cli.sh status
```

### 9.3 安装检查

```sh
sh lark-cli.sh install
command -v lark-cli
sh lark-cli.sh doctor
```

### 9.4 升级检查

```sh
sh lark-cli.sh update
```

### 9.5 主安装器跳过检查

```sh
INSTALL_LARK_CLI=0 PROJECT_DIR="$(pwd)" sh install.sh skills
```

预期：

- [ ] 不调用 `lark-cli.sh`。
- [ ] Jira Skill 安装逻辑不受影响。

### 9.6 主安装器可选安装检查

```sh
INSTALL_LARK_CLI=1 LARK_CLI_SETUP_MODE=install PROJECT_DIR="$(pwd)" sh install.sh skills
```

预期：

- [ ] 调用 `sh "$PROJECT_DIR/lark-cli.sh" install`。
- [ ] 不触发浏览器授权。
- [ ] 安装总结包含 Lark CLI 状态。

### 9.7 完整人工验证

```sh
sh lark-cli.sh bootstrap
```

预期：

- [ ] 用户能在浏览器完成配置和登录。
- [ ] `lark-cli auth status` 成功。
- [ ] 能创建测试飞书文档。

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| npm 全局安装权限不足 | 无法安装 CLI | 安装前检测写权限；交互触发 sudo；拒绝后询问 fallback prefix |
| `lark-cli` 安装后 PATH 不可见 | 用户以为安装失败 | 检测 npm global bin 并输出 export PATH |
| OAuth 需要浏览器确认 | 无法完全自动化 | 在提示中明确说明，bootstrap 允许中断后重试 |
| 官方 CLI 命令变化 | 脚本失效 | 将命令集中在 `lark-cli.sh`，主安装器只调用脚本 |
| 飞书权限过大 | 安全顾虑 | 默认不安装；发送/发布前确认；后续收敛 scope |
| 主安装器变复杂 | 维护成本上升 | `install.sh` 只做询问和调用，细节放在 `lark-cli.sh` |
| CI 中误触发登录 | 阻塞流水线 | 非交互默认跳过；测试使用 `LARK_CLI_SETUP_MODE=install` |

## 11. 文件改动清单

### 必改

- [x] `lark-cli.sh`
- [x] `install.sh`
- [x] `doc/active-lark-cli-todo.md`

### 建议改

- [x] `README.md`
- [x] `doc/active-lark-cli-design.md`

### 后续可能新增

- [ ] `active-jira-report/references/lark-report-publish.md`
- [ ] `active-jira-report/scripts/publish_lark_doc.sh`

## 12. 交付里程碑

### M1: 独立脚本可用

完成：

- [x] `lark-cli.sh help`
- [x] `lark-cli.sh doctor`
- [ ] `lark-cli.sh install`
- [x] `lark-cli.sh status`
- [ ] `lark-cli.sh update`

### M2: 官方完整流程可跑通

完成：

- [ ] `lark-cli.sh config`
- [ ] `lark-cli.sh login`
- [ ] `lark-cli.sh bootstrap`

### M3: 主安装器可选接入

完成：

- [ ] `INSTALL_LARK_CLI=0` 跳过。
- [ ] `INSTALL_LARK_CLI=1 LARK_CLI_SETUP_MODE=install` 自动安装。
- [x] 交互默认不安装。

### M4: 文档与验证

完成：

- [x] README 更新。
- [x] 故障排查更新。
- [ ] Markdown 报告创建飞书文档验证通过。

## 13. 推荐下一步

建议下一轮进入真实环境验收：

1. 执行 `sh lark-cli.sh install`，确认 npm 全局安装、Skill 安装和 PATH 表现。
2. 执行 `sh lark-cli.sh config`、`sh lark-cli.sh login`、`sh lark-cli.sh status`，完成浏览器授权验证。
3. 执行 `INSTALL_LARK_CLI=1 LARK_CLI_SETUP_MODE=install PROJECT_DIR="$(pwd)" sh install.sh skills`，确认主安装器可选入口。
4. 验证 `lark-cli docs +create --api-version v2 --doc-format markdown` 能创建测试飞书文档。
