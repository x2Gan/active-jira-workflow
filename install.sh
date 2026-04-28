#!/usr/bin/env sh
set -eu

###############################################################################
# XXX installer
#
# Usage:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/XXX/main/install.sh)"
#
# Update:
#   xxx update
#   or
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/XXX/main/install.sh)" -- update
#
# Required repo layout:
#   XXX proj top/
#     xxxx skill/
#     install.sh
#
###############################################################################

APP_NAME="${APP_NAME:-xxx}"

# 改成你的真实 Git 仓库地址
REPO_URL="${REPO_URL:-https://github.com/YOUR_ORG/XXX.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"

# 源码安装位置，类似 oh-my-zsh 的 ~/.oh-my-zsh
PROJECT_DIR="${PROJECT_DIR:-$HOME/.${APP_NAME}/src}"

# 工程内 skill 目录相对路径
# 如果你的真实目录名就是 "xxxx skill"，保持不变；否则改成真实路径。
SKILL_REL_PATH="${SKILL_REL_PATH:-xxxx skill}"

# 安装一个本地命令：xxx update
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

# jira-cli 子安装脚本地址。
# 不建议填 ChatGPT share URL；应使用 raw shell URL。
# 示例：
#   JIRA_CLI_INSTALL_URL=https://raw.githubusercontent.com/YOUR_ORG/XXX/main/tools/install-jira-cli.sh
JIRA_CLI_INSTALL_URL="${JIRA_CLI_INSTALL_URL:-}"

# 可选：自定义 jira-cli 升级命令。
# 示例：
#   JIRA_CLI_UPDATE_CMD='brew upgrade jira-cli'
JIRA_CLI_UPDATE_CMD="${JIRA_CLI_UPDATE_CMD:-}"


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

usage() {
  cat <<EOF
Usage:
  install.sh              安装并初始化 ${APP_NAME}
  install.sh install      安装并初始化 ${APP_NAME}
  install.sh update       更新工程源码，并尝试更新 jira-cli
  install.sh help         显示帮助

Environment:
  APP_NAME                默认：xxx
  REPO_URL                Git 仓库地址
  REPO_BRANCH             Git 分支，默认：main
  PROJECT_DIR             源码下载目录，默认：~/.xxx/src
  SKILL_REL_PATH          工程内 skill 目录相对路径，默认：xxxx skill
  BIN_DIR                 本地命令安装目录，默认：~/.local/bin
  JIRA_CLI_INSTALL_URL    jira-cli 子安装脚本 raw URL
  JIRA_CLI_UPDATE_CMD     自定义 jira-cli 升级命令
EOF
}

prompt_required() {
  _prompt="$1"
  _default="${2:-}"

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

  while :; do
    printf '%s: ' "$_prompt" >&2

    if [ -t 0 ]; then
      _old_stty="$(stty -g 2>/dev/null || true)"
      stty -echo 2>/dev/null || true
      IFS= read -r _answer || true
      if [ -n "$_old_stty" ]; then
        stty "$_old_stty" 2>/dev/null || true
      fi
      printf '\n' >&2
    else
      IFS= read -r _answer || true
    fi

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

normalize_jira_server() {
  printf '%s\n' "$1" | sed 's#/*$##'
}

jira_host_from_url() {
  printf '%s\n' "$1" \
    | sed -e 's#^[a-zA-Z][a-zA-Z0-9+.-]*://##' \
          -e 's#/.*$##' \
          -e 's/:.*$##'
}

ensure_project_source() {
  need_cmd git

  if [ -d "$PROJECT_DIR/.git" ]; then
    say "检测到已有源码目录：$PROJECT_DIR"
    (
      cd "$PROJECT_DIR"
      git fetch origin "$REPO_BRANCH"
      git checkout "$REPO_BRANCH" >/dev/null 2>&1 || true
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

install_jira_cli_with_custom_script() {
  if [ -z "$JIRA_CLI_INSTALL_URL" ]; then
    return 1
  fi

  need_cmd curl

  say "正在通过子安装脚本安装 jira-cli：$JIRA_CLI_INSTALL_URL"

  _tmp="${TMPDIR:-/tmp}/${APP_NAME}-jira-cli-install.$$"
  rm -f "$_tmp"

  if ! curl -fsSL "$JIRA_CLI_INSTALL_URL" -o "$_tmp"; then
    rm -f "$_tmp"
    warn "jira-cli 子安装脚本下载失败，将尝试官方安装 fallback。"
    return 1
  fi

  # 粗略防止把 HTML 页面当 shell 执行。
  if grep -qi '<html\|<!doctype html\|share_not_found' "$_tmp"; then
    rm -f "$_tmp"
    warn "jira-cli 子安装脚本看起来不是 raw shell 文件，将尝试官方安装 fallback。"
    return 1
  fi

  sh "$_tmp"
  rm -f "$_tmp"

  has_cmd jira
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
  if has_cmd jira; then
    say "已检测到 jira-cli：$(command -v jira)"
    return 0
  fi

  say "未检测到 jira-cli，准备安装。"

  if ! install_jira_cli_with_custom_script; then
    install_jira_cli_fallback
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

  # 移除旧的托管块，避免重复 machine 条目导致旧密码优先匹配。
  awk -v begin="$_begin" -v end="$_end" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    skip != 1 { print }
  ' "$_netrc" > "$_tmp"

  mv "$_tmp" "$_netrc"

  {
    printf '%s\n' "$_begin"

    # jira-cli / netrc 解析通常会按配置里的 server 匹配。
    # 这里同时写入完整 server 和 host，兼容不同匹配策略。
    printf 'machine %s\n' "$_jira_server"
    printf '  login %s\n' "$_jira_account"
    printf '  password %s\n' "$_jira_password"

    if [ "$_jira_host" != "$_jira_server" ]; then
      printf 'machine %s\n' "$_jira_host"
      printf '  login %s\n' "$_jira_account"
      printf '  password %s\n' "$_jira_password"
    fi

    printf '%s\n' "$_end"
  } >> "$_netrc"

  chmod 600 "$_netrc"
  say "已写入 $_netrc，并设置权限为 600。"
}

run_jira_init() {
  if ! has_cmd jira; then
    die "找不到 jira 命令，无法执行 jira init。"
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

  cat > "$_launcher" <<EOF
#!/usr/bin/env sh
exec "$PROJECT_DIR/install.sh" "\$@"
EOF

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
    else
      say "发现工程源码更新，正在执行 fast-forward pull。"
      git pull --ff-only origin "$REPO_BRANCH"
    fi
  )
}

update_jira_cli() {
  say "正在检查 jira-cli 更新。"

  if ! has_cmd jira; then
    warn "当前未安装 jira-cli，将执行安装流程。"
    ensure_jira_cli
    return 0
  fi

  if [ -n "$JIRA_CLI_UPDATE_CMD" ]; then
    say "使用自定义 jira-cli 升级命令：$JIRA_CLI_UPDATE_CMD"
    sh -c "$JIRA_CLI_UPDATE_CMD"
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

install_flow() {
  ensure_project_source
  ensure_jira_cli

  say ""
  say "开始初始化配置。"

  _default_skill_dir="$HOME/.chatgpt/skills"
  _skill_install_path="$(prompt_required "请输入 SKILL 安装路径" "$_default_skill_dir")"
  _jira_server="$(prompt_required "请输入 Jira 服务器路径，例如 https://jira.example.com" "")"
  _jira_account="$(prompt_required "请输入 Jira 账号" "")"
  _jira_password="$(prompt_secret "请输入 Jira 密码或 API Token")"

  create_skill_symlink "$_skill_install_path"
  write_netrc "$_jira_server" "$_jira_account" "$_jira_password"
  run_jira_init
  install_launcher

  say ""
  say "安装完成。"
  say "源码目录：$PROJECT_DIR"
  say "更新命令：$APP_NAME update"
}

update_flow() {
  update_project_source
  update_jira_cli
  say "更新流程完成。"
}

main() {
  _cmd="${1:-install}"

  case "$_cmd" in
    install)
      install_flow
      ;;
    update)
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