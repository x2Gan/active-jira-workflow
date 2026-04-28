#!/usr/bin/env sh
set -eu

###############################################################################
# zeppos-jira installer
#
# Install:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"
#
# Update:
#   zeppos-jira update
#   or
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)" -- update
#
###############################################################################

APP_NAME="${APP_NAME:-zeppos-jira}"
REPO_URL="${REPO_URL:-https://github.com/active-ailab/zeppos-jira-workflow.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
RAW_BASE_URL="${RAW_BASE_URL:-https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/${REPO_BRANCH}}"

# Source checkout, similar to ~/.oh-my-zsh.
PROJECT_DIR="${PROJECT_DIR:-$HOME/.${APP_NAME}/src}"

# Skill directory inside this repository.
SKILL_REL_PATH="${SKILL_REL_PATH:-zeppos-jira}"

# Where to install the local management command: zeppos-jira update.
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

# Codex skill install directory. Override this if you use another skills path.
DEFAULT_SKILL_INSTALL_DIR="${DEFAULT_SKILL_INSTALL_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}"

# jira-cli installer bundled in this repository.
JIRA_CLI_SCRIPT_REL_PATH="${JIRA_CLI_SCRIPT_REL_PATH:-jira-cli.sh}"
JIRA_CLI_INSTALL_URL="${JIRA_CLI_INSTALL_URL:-${RAW_BASE_URL}/${JIRA_CLI_SCRIPT_REL_PATH}}"
JIRA_CLI_UPDATE_CMD="${JIRA_CLI_UPDATE_CMD:-}"

# Optional non-interactive configuration.
SKILL_INSTALL_DIR="${SKILL_INSTALL_DIR:-}"
JIRA_SERVER="${JIRA_SERVER:-}"
JIRA_ACCOUNT="${JIRA_ACCOUNT:-}"
JIRA_API_TOKEN="${JIRA_API_TOKEN:-${JIRA_TOKEN:-${JIRA_PASSWORD:-}}}"
RUN_JIRA_INIT="${RUN_JIRA_INIT:-1}"
INSTALL_JIRA_CLI="${INSTALL_JIRA_CLI:-1}"

say() {
  printf '%s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*" >&2
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

need_cmd() {
  has_cmd "$1" || die "缺少必要命令：$1"
}

is_disabled() {
  case "${1:-}" in
    0|false|FALSE|no|NO|off|OFF)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

usage() {
  cat <<EOF
Usage:
  install.sh              安装并初始化 ${APP_NAME}
  install.sh install      安装并初始化 ${APP_NAME}
  install.sh update       更新工程源码，并尝试更新 jira-cli
  install.sh help         显示帮助

One-line install:
  sh -c "\$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"

Environment:
  APP_NAME                本地管理命令名，默认：zeppos-jira
  REPO_URL                Git 仓库地址，默认：${REPO_URL}
  REPO_BRANCH             Git 分支，默认：main
  RAW_BASE_URL            raw 文件基础 URL
  PROJECT_DIR             源码下载目录，默认：~/.zeppos-jira/src
  SKILL_REL_PATH          工程内 skill 目录，默认：zeppos-jira
  SKILL_INSTALL_DIR       skill 安装目录，默认：${DEFAULT_SKILL_INSTALL_DIR}
  BIN_DIR                 本地命令安装目录，默认：~/.local/bin
  JIRA_SERVER             Jira 地址，例如：https://jira.example.com
  JIRA_ACCOUNT            Jira 账号
  JIRA_API_TOKEN          Jira 密码或 API Token，也兼容 JIRA_TOKEN/JIRA_PASSWORD
  INSTALL_JIRA_CLI        是否自动安装 jira-cli，默认：1；设为 0 跳过
  RUN_JIRA_INIT           是否执行 jira init，默认：1；设为 0 跳过
  JIRA_CLI_INSTALL_URL    jira-cli 子安装脚本 raw URL
  JIRA_CLI_UPDATE_CMD     自定义 jira-cli 升级命令
EOF
}

prompt_required() {
  _prompt="$1"
  _default="${2:-}"
  _env_name="${3:-}"

  if [ ! -t 0 ]; then
    if [ -n "$_default" ]; then
      printf '%s\n' "$_default"
      return 0
    fi

    if [ -n "$_env_name" ]; then
      die "当前不是交互式终端，请通过环境变量 ${_env_name} 提供配置。"
    fi

    die "当前不是交互式终端，缺少必要配置。"
  fi

  while :; do
    if [ -n "$_default" ]; then
      printf '%s [%s]: ' "$_prompt" "$_default" >&2
    else
      printf '%s: ' "$_prompt" >&2
    fi

    IFS= read -r _answer || true

    if [ -z "$_answer" ] && [ -n "$_default" ]; then
      _answer="$_default"
    fi

    if [ -n "$_answer" ]; then
      printf '%s\n' "$_answer"
      return 0
    fi

    warn "该项不能为空。"
  done
}

prompt_secret() {
  _prompt="$1"
  _env_name="${2:-JIRA_API_TOKEN}"

  if [ ! -t 0 ]; then
    die "当前不是交互式终端，请通过环境变量 ${_env_name} 提供 Jira 密码或 API Token。"
  fi

  while :; do
    printf '%s: ' "$_prompt" >&2

    _old_stty="$(stty -g 2>/dev/null || true)"
    stty -echo 2>/dev/null || true
    IFS= read -r _answer || true
    if [ -n "$_old_stty" ]; then
      stty "$_old_stty" 2>/dev/null || true
    fi
    printf '\n' >&2

    if [ -n "$_answer" ]; then
      printf '%s\n' "$_answer"
      return 0
    fi

    warn "该项不能为空。"
  done
}

expand_user_path() {
  _path="$1"

  case "$_path" in
    "~")
      printf '%s\n' "$HOME"
      ;;
    "~/"*)
      printf '%s\n' "$HOME/${_path#~/}"
      ;;
    *)
      printf '%s\n' "$_path"
      ;;
  esac
}

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

normalize_jira_server() {
  printf '%s\n' "$1" | sed 's#/*$##'
}

jira_host_from_url() {
  printf '%s\n' "$1" \
    | sed -e 's#^[a-zA-Z][a-zA-Z0-9+.-]*://##' \
          -e 's#/.*$##' \
          -e 's#:.*$##'
}

ensure_project_source() {
  need_cmd git

  if [ -d "$PROJECT_DIR/.git" ]; then
    say "检测到已有源码目录：$PROJECT_DIR"
    (
      cd "$PROJECT_DIR"

      _origin="$(git config --get remote.origin.url || true)"
      if [ -n "$_origin" ] && [ "$_origin" != "$REPO_URL" ]; then
        warn "当前源码 origin 为 $_origin，本次配置的 REPO_URL 为 $REPO_URL。"
      fi

      git fetch origin "$REPO_BRANCH"

      if git show-ref --verify --quiet "refs/heads/$REPO_BRANCH"; then
        git checkout "$REPO_BRANCH" >/dev/null 2>&1
      else
        git checkout -b "$REPO_BRANCH" "origin/$REPO_BRANCH" >/dev/null 2>&1
      fi

      git pull --ff-only origin "$REPO_BRANCH"
    )
    return 0
  fi

  if [ -e "$PROJECT_DIR" ]; then
    die "源码安装目录已存在但不是 Git 仓库：$PROJECT_DIR"
  fi

  say "正在下载工程源码：$REPO_URL"
  mkdir -p "$(dirname "$PROJECT_DIR")"
  git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$PROJECT_DIR"
}

install_jira_cli_with_project_script() {
  _script="$PROJECT_DIR/$JIRA_CLI_SCRIPT_REL_PATH"

  [ -f "$_script" ] || return 1

  if [ "$(uname -s 2>/dev/null || printf unknown)" != "Linux" ]; then
    return 1
  fi

  if ! has_cmd bash; then
    warn "发现工程内 jira-cli 安装脚本，但当前环境没有 bash。"
    return 1
  fi

  say "正在通过工程内脚本安装 jira-cli：$_script"

  if bash "$_script" install; then
    has_cmd jira
    return $?
  fi

  warn "工程内 jira-cli 安装脚本执行失败，将尝试 fallback。"
  return 1
}

install_jira_cli_with_custom_script() {
  if [ -z "$JIRA_CLI_INSTALL_URL" ]; then
    return 1
  fi

  need_cmd curl

  if ! has_cmd bash; then
    warn "无法执行 jira-cli 子安装脚本：当前环境没有 bash。"
    return 1
  fi

  say "正在通过 raw 脚本安装 jira-cli：$JIRA_CLI_INSTALL_URL"

  _tmp="${TMPDIR:-/tmp}/${APP_NAME}-jira-cli-install.$$"
  rm -f "$_tmp"

  if ! curl -fsSL "$JIRA_CLI_INSTALL_URL" -o "$_tmp"; then
    rm -f "$_tmp"
    warn "jira-cli 子安装脚本下载失败，将尝试 fallback。"
    return 1
  fi

  # Avoid executing a web page if a wrong URL is supplied.
  if grep -qi '<html\|<!doctype html\|share_not_found\|not found' "$_tmp"; then
    rm -f "$_tmp"
    warn "jira-cli 子安装脚本看起来不是 raw shell 文件，将尝试 fallback。"
    return 1
  fi

  if bash "$_tmp" install; then
    rm -f "$_tmp"
    has_cmd jira
    return $?
  fi

  rm -f "$_tmp"
  warn "jira-cli 子安装脚本执行失败，将尝试 fallback。"
  return 1
}

install_jira_cli_fallback() {
  say "正在尝试安装 jira-cli fallback。"

  if has_cmd brew; then
    say "使用 Homebrew 安装 jira-cli。"
    brew tap ankitpokhrel/jira-cli
    brew install jira-cli
    return 0
  fi

  if has_cmd go; then
    say "使用 Go 安装 jira-cli。"
    go install github.com/ankitpokhrel/jira-cli/cmd/jira@latest

    _gopath="$(go env GOPATH 2>/dev/null || true)"
    if [ -n "$_gopath" ] && [ -x "$_gopath/bin/jira" ]; then
      PATH="$_gopath/bin:$PATH"
      export PATH
    fi

    return 0
  fi

  die "未找到 jira-cli，且当前环境没有 brew 或 go。请安装 brew/go，或提供 JIRA_CLI_INSTALL_URL。"
}

ensure_jira_cli() {
  if is_disabled "$INSTALL_JIRA_CLI"; then
    warn "已按 INSTALL_JIRA_CLI=0 跳过 jira-cli 安装。"
    return 0
  fi

  if has_cmd jira; then
    say "已检测到 jira-cli：$(command -v jira)"
    return 0
  fi

  say "未检测到 jira-cli，准备安装。"

  if ! install_jira_cli_with_project_script; then
    if ! install_jira_cli_with_custom_script; then
      install_jira_cli_fallback
    fi
  fi

  has_cmd jira || die "jira-cli 安装完成后仍找不到 jira 命令，请检查 PATH。"

  say "jira-cli 安装完成：$(command -v jira)"
}

create_skill_symlink() {
  _skill_install_dir="$(expand_user_path "$1")"
  _skill_src="$PROJECT_DIR/$SKILL_REL_PATH"
  _skill_name="$(basename "$SKILL_REL_PATH")"
  _skill_target="$_skill_install_dir/$_skill_name"

  [ -d "$_skill_src" ] || die "工程源码中不存在 skill 目录：$_skill_src"

  mkdir -p "$_skill_install_dir"

  if [ -L "$_skill_target" ]; then
    _current_link="$(readlink "$_skill_target" 2>/dev/null || true)"

    if [ "$_current_link" = "$_skill_src" ]; then
      say "skill 软链接已存在：$_skill_target -> $_skill_src"
      return 0
    fi

    say "发现已有软链接，将替换：$_skill_target"
    rm -f "$_skill_target"
  elif [ -e "$_skill_target" ]; then
    _backup="${_skill_target}.backup.$(date +%Y%m%d%H%M%S)"
    warn "目标路径已存在且不是软链接，将备份为：$_backup"
    mv "$_skill_target" "$_backup"
  fi

  ln -s "$_skill_src" "$_skill_target"
  say "已创建 skill 软链接：$_skill_target -> $_skill_src"
}

write_netrc() {
  _jira_server="$(normalize_jira_server "$1")"
  _jira_host="$(jira_host_from_url "$_jira_server")"
  _jira_account="$2"
  _jira_password="$3"
  _netrc="$HOME/.netrc"
  _tmp="${_netrc}.tmp.$$"
  _begin="# BEGIN ${APP_NAME} managed jira credentials"
  _end="# END ${APP_NAME} managed jira credentials"

  touch "$_netrc"
  chmod 600 "$_netrc" 2>/dev/null || true

  # Remove old managed block to avoid stale credentials taking precedence.
  awk -v begin="$_begin" -v end="$_end" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    skip != 1 { print }
  ' "$_netrc" > "$_tmp"

  mv "$_tmp" "$_netrc"

  {
    printf '%s\n' "$_begin"
    printf 'machine %s\n' "$_jira_host"
    printf '  login %s\n' "$_jira_account"
    printf '  password %s\n' "$_jira_password"

    if [ "$_jira_server" != "$_jira_host" ]; then
      printf 'machine %s\n' "$_jira_server"
      printf '  login %s\n' "$_jira_account"
      printf '  password %s\n' "$_jira_password"
    fi

    printf '%s\n' "$_end"
  } >> "$_netrc"

  chmod 600 "$_netrc"
  say "已写入 $_netrc，并设置权限为 600。"
}

run_jira_init() {
  if is_disabled "$RUN_JIRA_INIT"; then
    warn "已按 RUN_JIRA_INIT=0 跳过 jira init。"
    return 0
  fi

  if ! has_cmd jira; then
    warn "找不到 jira 命令，跳过 jira init。"
    return 0
  fi

  if [ -t 0 ] && [ -t 1 ]; then
    say "准备执行 jira init。请按提示选择 Jira 类型、认证类型、项目等信息。"
    jira init
  else
    warn "当前不是交互式终端，跳过 jira init。请稍后手动执行：jira init"
  fi
}

install_launcher() {
  mkdir -p "$BIN_DIR"

  _launcher="$BIN_DIR/$APP_NAME"

  {
    printf '%s\n' '#!/usr/bin/env sh'
    printf 'APP_NAME=%s\n' "$(shell_quote "$APP_NAME")"
    printf 'PROJECT_DIR=%s\n' "$(shell_quote "$PROJECT_DIR")"
    printf 'REPO_URL=%s\n' "$(shell_quote "$REPO_URL")"
    printf 'REPO_BRANCH=%s\n' "$(shell_quote "$REPO_BRANCH")"
    printf 'RAW_BASE_URL=%s\n' "$(shell_quote "$RAW_BASE_URL")"
    printf 'SKILL_REL_PATH=%s\n' "$(shell_quote "$SKILL_REL_PATH")"
    printf 'JIRA_CLI_SCRIPT_REL_PATH=%s\n' "$(shell_quote "$JIRA_CLI_SCRIPT_REL_PATH")"
    printf 'export APP_NAME PROJECT_DIR REPO_URL REPO_BRANCH RAW_BASE_URL SKILL_REL_PATH JIRA_CLI_SCRIPT_REL_PATH\n'
    printf 'exec sh %s "$@"\n' "$(shell_quote "$PROJECT_DIR/install.sh")"
  } > "$_launcher"

  chmod +x "$_launcher"

  say "已安装命令：$_launcher"
  case ":$PATH:" in
    *":$BIN_DIR:"*)
      ;;
    *)
      warn "$BIN_DIR 不在 PATH 中。你可以把下面这行加入 ~/.zshrc 或 ~/.bashrc："
      warn "export PATH=\"$BIN_DIR:\$PATH\""
      ;;
  esac
}

update_project_source() {
  [ -d "$PROJECT_DIR/.git" ] || die "找不到源码 Git 仓库：$PROJECT_DIR"

  say "正在检查工程源码更新。"

  (
    cd "$PROJECT_DIR"

    git fetch origin "$REPO_BRANCH"

    _current="$(git rev-parse HEAD)"
    _remote="$(git rev-parse "origin/$REPO_BRANCH")"

    if [ "$_current" = "$_remote" ]; then
      say "工程源码已是最新版本。"
    elif git merge-base --is-ancestor "$_current" "$_remote"; then
      say "发现工程源码更新，正在执行 fast-forward pull。"
      git pull --ff-only origin "$REPO_BRANCH"
    else
      warn "源码目录存在本地提交或分叉，未自动覆盖：$PROJECT_DIR"
      warn "请进入源码目录手动检查：git status && git pull --ff-only origin $REPO_BRANCH"
    fi
  )
}

update_jira_cli_with_project_script() {
  _script="$PROJECT_DIR/$JIRA_CLI_SCRIPT_REL_PATH"

  [ -f "$_script" ] || return 1
  has_cmd bash || return 1

  if [ "$(uname -s 2>/dev/null || printf unknown)" != "Linux" ]; then
    return 1
  fi

  say "使用工程内脚本检查/升级 jira-cli：$_script"
  bash "$_script" update
}

update_jira_cli() {
  if is_disabled "$INSTALL_JIRA_CLI"; then
    warn "已按 INSTALL_JIRA_CLI=0 跳过 jira-cli 更新。"
    return 0
  fi

  say "正在检查 jira-cli 更新。"

  if [ -n "$JIRA_CLI_UPDATE_CMD" ]; then
    say "使用自定义 jira-cli 升级命令：$JIRA_CLI_UPDATE_CMD"
    sh -c "$JIRA_CLI_UPDATE_CMD"
    return 0
  fi

  if update_jira_cli_with_project_script; then
    return 0
  fi

  if ! has_cmd jira; then
    warn "当前未安装 jira-cli，将执行安装流程。"
    ensure_jira_cli
    return 0
  fi

  if has_cmd brew && brew list jira-cli >/dev/null 2>&1; then
    say "使用 Homebrew 检查/升级 jira-cli。"
    brew update
    brew upgrade jira-cli || true
    return 0
  fi

  if has_cmd go; then
    say "使用 Go 检查/升级 jira-cli。"
    go install github.com/ankitpokhrel/jira-cli/cmd/jira@latest

    _gopath="$(go env GOPATH 2>/dev/null || true)"
    if [ -n "$_gopath" ] && [ -x "$_gopath/bin/jira" ]; then
      PATH="$_gopath/bin:$PATH"
      export PATH
    fi

    return 0
  fi

  warn "无法自动判断 jira-cli 的安装方式。你可以设置 JIRA_CLI_UPDATE_CMD 来指定升级命令。"
}

resolve_install_config() {
  if [ -n "$SKILL_INSTALL_DIR" ]; then
    _skill_install_path="$SKILL_INSTALL_DIR"
  else
    _skill_install_path="$(prompt_required "请输入 skill 安装路径" "$DEFAULT_SKILL_INSTALL_DIR" "SKILL_INSTALL_DIR")"
  fi

  if [ -n "$JIRA_SERVER" ]; then
    _jira_server="$JIRA_SERVER"
  else
    _jira_server="$(prompt_required "请输入 Jira 服务器地址，例如 https://jira.example.com" "" "JIRA_SERVER")"
  fi

  if [ -n "$JIRA_ACCOUNT" ]; then
    _jira_account="$JIRA_ACCOUNT"
  else
    _jira_account="$(prompt_required "请输入 Jira 账号" "" "JIRA_ACCOUNT")"
  fi

  if [ -n "$JIRA_API_TOKEN" ]; then
    _jira_password="$JIRA_API_TOKEN"
  else
    _jira_password="$(prompt_secret "请输入 Jira 密码或 API Token" "JIRA_API_TOKEN")"
  fi
}

install_flow() {
  ensure_project_source
  ensure_jira_cli

  say ""
  say "开始初始化配置。"

  resolve_install_config
  create_skill_symlink "$_skill_install_path"
  write_netrc "$_jira_server" "$_jira_account" "$_jira_password"
  run_jira_init
  install_launcher

  say ""
  say "安装完成。"
  say "源码目录：$PROJECT_DIR"
  say "skill 目录：$(expand_user_path "$_skill_install_path")/$(basename "$SKILL_REL_PATH")"
  say "更新命令：$APP_NAME update"
}

update_flow() {
  update_project_source
  update_jira_cli
  say "更新流程完成。"
}

normalize_paths() {
  PROJECT_DIR="$(expand_user_path "$PROJECT_DIR")"
  BIN_DIR="$(expand_user_path "$BIN_DIR")"
  DEFAULT_SKILL_INSTALL_DIR="$(expand_user_path "$DEFAULT_SKILL_INSTALL_DIR")"
  if [ -n "$SKILL_INSTALL_DIR" ]; then
    SKILL_INSTALL_DIR="$(expand_user_path "$SKILL_INSTALL_DIR")"
  fi
}

main() {
  normalize_paths

  _cmd="${1:-install}"

  case "$_cmd" in
    install)
      install_flow
      ;;
    update|upgrade)
      update_flow
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      usage
      die "未知命令：$_cmd"
      ;;
  esac
}

main "$@"
