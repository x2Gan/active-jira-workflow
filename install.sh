#!/usr/bin/env sh
set -eu

###############################################################################
# zeppos-jira installer
#
# Install:
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)" -- /path/to/parent
#
# Update:
#   zeppos-jira update
#   or
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)" -- update
#
###############################################################################

APP_NAME="${APP_NAME:-zeppos-jira}"
INSTALLER_VERSION="${INSTALLER_VERSION:-0.3.0}"
REPO_URL="${REPO_URL:-https://github.com/active-ailab/zeppos-jira-workflow.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
RAW_BASE_URL="${RAW_BASE_URL:-https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/${REPO_BRANCH}}"
REPO_DIR_NAME="${REPO_DIR_NAME:-zeppos-jira-workflow}"
PROJECT_VERSION_FILE="${PROJECT_VERSION_FILE:-VERSION}"

# Source checkout parent. Defaults under the directory where the command is run.
RUN_DIR="$(pwd)"
INSTALL_DIR="${INSTALL_DIR:-$RUN_DIR}"
PROJECT_DIR="${PROJECT_DIR:-}"

# Skill directory inside this repository.
SKILL_REL_PATH="${SKILL_REL_PATH:-zeppos-jira}"

# Where to install the local management command: zeppos-jira update.
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

# Codex skill install directory. Override this if you use another skills path.
DEFAULT_SKILL_INSTALL_DIR="${DEFAULT_SKILL_INSTALL_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}"

# jira-cli installer bundled in this repository.
JIRA_CLI_REPO="${JIRA_CLI_REPO:-ankitpokhrel/jira-cli}"
JIRA_CLI_LATEST_URL="${JIRA_CLI_LATEST_URL:-https://github.com/${JIRA_CLI_REPO}/releases/latest}"
JIRA_CLI_SCRIPT_REL_PATH="${JIRA_CLI_SCRIPT_REL_PATH:-jira-cli.sh}"
DEFAULT_JIRA_CLI_INSTALL_URL="${RAW_BASE_URL}/${JIRA_CLI_SCRIPT_REL_PATH}"
JIRA_CLI_INSTALL_URL_PROVIDED="${JIRA_CLI_INSTALL_URL+x}"
JIRA_CLI_INSTALL_URL="${JIRA_CLI_INSTALL_URL:-$DEFAULT_JIRA_CLI_INSTALL_URL}"
JIRA_CLI_UPDATE_CMD="${JIRA_CLI_UPDATE_CMD:-}"

# Optional non-interactive configuration.
SKILL_INSTALL_DIR="${SKILL_INSTALL_DIR:-}"
JIRA_SERVER="${JIRA_SERVER:-}"
JIRA_ACCOUNT="${JIRA_ACCOUNT:-}"
JIRA_API_TOKEN="${JIRA_API_TOKEN:-${JIRA_TOKEN:-${JIRA_PASSWORD:-}}}"
JIRA_INSTALLATION="${JIRA_INSTALLATION:-}"
JIRA_AUTH_TYPE="${JIRA_AUTH_TYPE:-}"
JIRA_PROJECT="${JIRA_PROJECT:-}"
JIRA_BOARD="${JIRA_BOARD:-}"
JIRA_INIT_FORCE="${JIRA_INIT_FORCE:-1}"
JIRA_INSECURE="${JIRA_INSECURE:-0}"
INIT_JIRA_CLI="${INIT_JIRA_CLI:-1}"
RUN_JIRA_INIT="${RUN_JIRA_INIT:-1}"
INSTALL_JIRA_CLI="${INSTALL_JIRA_CLI:-1}"

# Temporary switch: keep skill/launcher setup disabled while the rest of the
# workflow is being iterated. jira-cli installation and init still run.
SKIP_CONFIG_STEPS="${SKIP_CONFIG_STEPS:-${SKIP_POST_SOURCE_STEPS:-1}}"

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
  install.sh [安装父目录]           下载源码到父目录/${REPO_DIR_NAME}；默认：当前目录
  install.sh install [安装父目录]   下载源码到父目录/${REPO_DIR_NAME}；默认：当前目录
  install.sh install --path PATH    下载源码到 PATH/${REPO_DIR_NAME}
  install.sh update [安装父目录]    先更新源码，再检查/更新 jira-cli
  install.sh version [安装父目录]   显示安装器、源码、jira-cli 版本
  install.sh help         显示帮助

One-line install:
  sh -c "\$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)"
  sh -c "\$(curl -fsSL https://raw.githubusercontent.com/active-ailab/zeppos-jira-workflow/main/install.sh)" -- /path/to/parent

Environment:
  APP_NAME                本地管理命令名，默认：zeppos-jira
  INSTALLER_VERSION       安装器版本，默认：${INSTALLER_VERSION}
  REPO_URL                Git 仓库地址，默认：${REPO_URL}
  REPO_BRANCH             Git 分支，默认：main
  RAW_BASE_URL            raw 文件基础 URL
  REPO_DIR_NAME           源码目录名，默认：zeppos-jira-workflow
  PROJECT_VERSION_FILE    源码版本文件，默认：VERSION
  INSTALL_DIR             源码安装父目录，默认：当前目录
  PROJECT_DIR             精确源码目录，兼容旧变量；优先级高于 INSTALL_DIR
  SKILL_REL_PATH          工程内 skill 目录，默认：zeppos-jira
  SKILL_INSTALL_DIR       skill 安装目录，默认：${DEFAULT_SKILL_INSTALL_DIR}
  BIN_DIR                 本地命令安装目录，默认：~/.local/bin
  JIRA_SERVER             Jira 地址，例如：https://jira.example.com
  JIRA_ACCOUNT            Jira 账号
  JIRA_API_TOKEN          Jira 密码或 API Token，也兼容 JIRA_TOKEN/JIRA_PASSWORD
  JIRA_INSTALLATION       Jira 类型：cloud 或 local，默认按 server 推断
  JIRA_AUTH_TYPE          认证类型：basic、bearer 或 mtls，默认：basic
  JIRA_PROJECT            默认 Jira 项目 key；为空则由 jira init 交互选择
  JIRA_BOARD              默认 Jira board；为空则由 jira init 交互选择
  JIRA_INIT_FORCE         是否覆盖已有 jira-cli 配置，默认：1
  JIRA_INSECURE           是否跳过 TLS 证书校验，默认：0
  INIT_JIRA_CLI           是否执行 jira-cli 初始化，默认：1
  INSTALL_JIRA_CLI        是否自动安装 jira-cli，默认：1；设为 0 跳过
  RUN_JIRA_INIT           兼容旧变量；设为 0 时跳过 jira-cli 初始化
  SKIP_CONFIG_STEPS       临时开关：跳过 skill/launcher 配置，默认：1
  JIRA_CLI_LATEST_URL     jira-cli latest release URL，默认：GitHub releases/latest
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

is_empty_dir() {
  [ -d "$1" ] || return 1
  [ -z "$(ls -A "$1" 2>/dev/null)" ]
}

set_project_dir_from_install_dir() {
  INSTALL_DIR="$1"

  if [ "$(basename "$INSTALL_DIR")" = "$REPO_DIR_NAME" ]; then
    PROJECT_DIR="$INSTALL_DIR"
  else
    PROJECT_DIR="$INSTALL_DIR/$REPO_DIR_NAME"
  fi
}

strip_leading_v() {
  printf '%s\n' "$1" | sed 's/^v//'
}

read_first_line() {
  sed -n '1{s/[[:space:]]*$//;p;q;}' "$1"
}

get_project_version_from_dir() {
  _dir="$1"
  _version_file="$_dir/$PROJECT_VERSION_FILE"

  if [ -f "$_version_file" ]; then
    read_first_line "$_version_file"
    return 0
  fi

  if [ -d "$_dir/.git" ]; then
    (
      cd "$_dir"
      git describe --tags --always --dirty 2>/dev/null || git rev-parse --short HEAD
    )
    return 0
  fi

  return 1
}

get_remote_project_version() {
  if ! has_cmd curl; then
    return 1
  fi

  _version="$(curl -fsSL "$RAW_BASE_URL/$PROJECT_VERSION_FILE" 2>/dev/null | sed -n '1{s/[[:space:]]*$//;p;q;}' || true)"
  [ -n "$_version" ] || return 1
  printf '%s\n' "$_version"
}

get_remote_project_commit() {
  has_cmd git || return 1
  git ls-remote "$REPO_URL" "refs/heads/$REPO_BRANCH" 2>/dev/null | awk 'NR == 1 { print substr($1, 1, 12) }'
}

get_local_project_commit() {
  [ -d "$PROJECT_DIR/.git" ] || return 1
  (
    cd "$PROJECT_DIR"
    git rev-parse --short=12 HEAD
  )
}

get_fetched_remote_project_version() {
  [ -d "$PROJECT_DIR/.git" ] || return 1

  (
    cd "$PROJECT_DIR"

    if git cat-file -e "origin/$REPO_BRANCH:$PROJECT_VERSION_FILE" 2>/dev/null; then
      git show "origin/$REPO_BRANCH:$PROJECT_VERSION_FILE" | sed -n '1{s/[[:space:]]*$//;p;q;}'
    else
      git rev-parse --short=12 "origin/$REPO_BRANCH"
    fi
  )
}

get_fetched_remote_project_commit() {
  [ -d "$PROJECT_DIR/.git" ] || return 1

  (
    cd "$PROJECT_DIR"
    git rev-parse --short=12 "origin/$REPO_BRANCH"
  )
}

get_local_jira_cli_version() {
  has_cmd jira || return 1

  _output="$(
    {
      jira version 2>/dev/null || true
      jira --version 2>/dev/null || true
    } | head -n 5
  )"

  _version="$(
    printf '%s\n' "$_output" |
      grep -Eo 'v?[0-9]+([.][0-9]+){1,3}([-+][0-9A-Za-z.-]+)?' |
      head -n 1
  )"
  [ -n "$_version" ] || return 1
  strip_leading_v "$_version"
}

get_latest_jira_cli_version() {
  has_cmd curl || return 1

  _effective_url="$(curl -fsSL -o /dev/null -w '%{url_effective}' "$JIRA_CLI_LATEST_URL" 2>/dev/null || true)"
  [ -n "$_effective_url" ] || return 1

  _tag="${_effective_url##*/}"

  case "$_tag" in
    v*) ;;
    *) return 1 ;;
  esac

  strip_leading_v "$_tag"
}

normalize_jira_server() {
  printf '%s\n' "$1" | sed 's#/*$##'
}

infer_jira_installation() {
  case "$1" in
    *".atlassian.net"*)
      printf '%s\n' "cloud"
      ;;
    *)
      printf '%s\n' "local"
      ;;
  esac
}

normalize_jira_installation() {
  case "$(printf '%s\n' "$1" | tr '[:upper:]' '[:lower:]')" in
    cloud)
      printf '%s\n' "cloud"
      ;;
    local|server|onprem|on-prem|on-premise)
      printf '%s\n' "local"
      ;;
    *)
      return 1
      ;;
  esac
}

normalize_jira_auth_type() {
  case "$(printf '%s\n' "$1" | tr '[:upper:]' '[:lower:]')" in
    ""|basic|password)
      printf '%s\n' "basic"
      ;;
    bearer|pat|token)
      printf '%s\n' "bearer"
      ;;
    mtls)
      printf '%s\n' "mtls"
      ;;
    *)
      return 1
      ;;
  esac
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
    if is_empty_dir "$PROJECT_DIR"; then
      say "目标目录已存在且为空，将源码下载到：$PROJECT_DIR"
      git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$PROJECT_DIR"
      return 0
    fi

    die "源码安装目录已存在但不是 Git 仓库或空目录：$PROJECT_DIR"
  fi

  say "正在下载工程源码：$REPO_URL"
  mkdir -p "$(dirname "$PROJECT_DIR")"
  git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$PROJECT_DIR"
}

install_jira_cli_with_project_script() {
  _script="$PROJECT_DIR/$JIRA_CLI_SCRIPT_REL_PATH"

  [ -f "$_script" ] || return 1

  # Keep the release download/install details in jira-cli.sh. This installer
  # only orchestrates it after the repository has been checked out.
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

  warn "工程内 jira-cli 安装脚本执行失败。"
  return 1
}

install_jira_cli_with_custom_script() {
  if [ -z "$JIRA_CLI_INSTALL_URL" ]; then
    return 1
  fi

  if [ -z "$JIRA_CLI_INSTALL_URL_PROVIDED" ]; then
    return 1
  fi

  if [ "$JIRA_CLI_INSTALL_URL" = "$DEFAULT_JIRA_CLI_INSTALL_URL" ] \
    && [ "$(uname -s 2>/dev/null || printf unknown)" != "Linux" ]; then
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
    warn "jira-cli 子安装脚本下载失败。"
    return 1
  fi

  # Avoid executing a web page if a wrong URL is supplied.
  if grep -qi '<html\|<!doctype html\|share_not_found\|not found' "$_tmp"; then
    rm -f "$_tmp"
    warn "jira-cli 子安装脚本看起来不是 raw shell 文件。"
    return 1
  fi

  if bash "$_tmp" install; then
    rm -f "$_tmp"
    has_cmd jira
    return $?
  fi

  rm -f "$_tmp"
  warn "jira-cli 子安装脚本执行失败。"
  return 1
}

install_jira_cli_fallback() {
  die "jira-cli 自动安装失败；brew/go fallback 已暂时停用。请检查 ${PROJECT_DIR}/${JIRA_CLI_SCRIPT_REL_PATH} 的输出，或显式提供 JIRA_CLI_INSTALL_URL。"
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

    printf '%s\n' "$_end"
  } >> "$_netrc"

  chmod 600 "$_netrc"
  say "已写入 $_netrc，并设置权限为 600。"
}

jira_config_file_path() {
  if [ -n "${JIRA_CONFIG_FILE:-}" ]; then
    expand_user_path "$JIRA_CONFIG_FILE"
    return 0
  fi

  if [ -n "${XDG_CONFIG_HOME:-}" ]; then
    printf '%s\n' "$(expand_user_path "$XDG_CONFIG_HOME")/.jira/.config.yml"
  else
    printf '%s\n' "$HOME/.config/.jira/.config.yml"
  fi
}

read_simple_yaml_value() {
  _key="$1"
  _file="$2"

  sed -n "s/^[[:space:]]*${_key}:[[:space:]]*//p" "$_file" \
    | sed -n '1{s/^["'\'']//;s/["'\'']$//;p;q;}'
}

sync_netrc_from_jira_config() {
  _token="$1"
  _fallback_server="$2"
  _fallback_login="$3"
  _config_file="$(jira_config_file_path)"

  if [ ! -f "$_config_file" ]; then
    return 0
  fi

  _configured_server="$(read_simple_yaml_value "server" "$_config_file" || true)"
  _configured_login="$(read_simple_yaml_value "login" "$_config_file" || true)"

  [ -n "$_configured_server" ] || _configured_server="$_fallback_server"
  [ -n "$_configured_login" ] || _configured_login="$_fallback_login"

  if [ -n "$_configured_server" ] && [ -n "$_configured_login" ] && [ -n "$_token" ]; then
    write_netrc "$_configured_server" "$_configured_login" "$_token"
  fi
}

resolve_jira_cli_init_config() {
  if [ -n "$JIRA_SERVER" ]; then
    _jira_server="$(normalize_jira_server "$JIRA_SERVER")"
  else
    _jira_server="$(prompt_required "请输入 Jira 服务器地址，例如 https://jira.example.com" "" "JIRA_SERVER")"
    _jira_server="$(normalize_jira_server "$_jira_server")"
  fi

  if [ -n "$JIRA_INSTALLATION" ]; then
    _jira_installation="$(normalize_jira_installation "$JIRA_INSTALLATION")" \
      || die "JIRA_INSTALLATION 只能是 cloud 或 local。"
  else
    _default_installation="$(infer_jira_installation "$_jira_server")"
    _jira_installation="$(prompt_required "请输入 Jira 类型 cloud/local" "$_default_installation" "JIRA_INSTALLATION")"
    _jira_installation="$(normalize_jira_installation "$_jira_installation")" \
      || die "Jira 类型只能是 cloud 或 local。"
  fi

  if [ -n "$JIRA_AUTH_TYPE" ]; then
    _jira_auth_type="$(normalize_jira_auth_type "$JIRA_AUTH_TYPE")" \
      || die "JIRA_AUTH_TYPE 只能是 basic、bearer 或 mtls。"
  else
    _jira_auth_type="$(prompt_required "请输入 Jira 认证类型 basic/bearer/mtls" "basic" "JIRA_AUTH_TYPE")"
    _jira_auth_type="$(normalize_jira_auth_type "$_jira_auth_type")" \
      || die "Jira 认证类型只能是 basic、bearer 或 mtls。"
  fi

  if [ -n "$JIRA_ACCOUNT" ]; then
    _jira_account="$JIRA_ACCOUNT"
  else
    if [ "$_jira_installation" = "cloud" ]; then
      _jira_account="$(prompt_required "请输入 Jira 登录邮箱" "" "JIRA_ACCOUNT")"
    else
      _jira_account="$(prompt_required "请输入 Jira 登录用户名" "" "JIRA_ACCOUNT")"
    fi
  fi

  if [ "$_jira_auth_type" = "mtls" ]; then
    _jira_password="${JIRA_API_TOKEN:-}"
  elif [ -n "$JIRA_API_TOKEN" ]; then
    _jira_password="$JIRA_API_TOKEN"
  else
    _jira_password="$(prompt_secret "请输入 Jira 密码或 API Token/PAT" "JIRA_API_TOKEN")"
  fi
}

run_jira_init() {
  if is_disabled "$INIT_JIRA_CLI" || is_disabled "$RUN_JIRA_INIT"; then
    warn "已按 INIT_JIRA_CLI=0 或 RUN_JIRA_INIT=0 跳过 jira init。"
    return 0
  fi

  if ! has_cmd jira; then
    die "找不到 jira 命令，无法执行 jira init。"
  fi

  resolve_jira_cli_init_config

  if [ "$_jira_auth_type" != "mtls" ]; then
    write_netrc "$_jira_server" "$_jira_account" "$_jira_password"
    JIRA_API_TOKEN="$_jira_password"
    export JIRA_API_TOKEN
  fi

  JIRA_AUTH_TYPE="$_jira_auth_type"
  export JIRA_AUTH_TYPE

  set -- init \
    --installation "$_jira_installation" \
    --server "$_jira_server" \
    --login "$_jira_account" \
    --auth-type "$_jira_auth_type"

  if ! is_disabled "$JIRA_INIT_FORCE"; then
    set -- "$@" --force
  fi

  if ! is_disabled "$JIRA_INSECURE"; then
    set -- "$@" --insecure
  fi

  if [ -n "$JIRA_PROJECT" ]; then
    set -- "$@" --project "$JIRA_PROJECT"
  elif [ ! -t 0 ]; then
    die "当前不是交互式终端，请通过 JIRA_PROJECT 提供默认 Jira 项目 key。"
  fi

  if [ -n "$JIRA_BOARD" ]; then
    set -- "$@" --board "$JIRA_BOARD"
  elif [ ! -t 0 ]; then
    die "当前不是交互式终端，请通过 JIRA_BOARD 提供默认 Jira board 名称。"
  fi

  say "准备执行 jira init。项目和 board 若未通过环境变量提供，将由 jira-cli 交互选择。"
  jira "$@"

  if [ "$_jira_auth_type" != "mtls" ]; then
    sync_netrc_from_jira_config "$_jira_password" "$_jira_server" "$_jira_account"
  fi
}

install_launcher() {
  mkdir -p "$BIN_DIR"

  _launcher="$BIN_DIR/$APP_NAME"

  {
    printf '%s\n' '#!/usr/bin/env sh'
    printf 'APP_NAME=%s\n' "$(shell_quote "$APP_NAME")"
    printf 'INSTALLER_VERSION=%s\n' "$(shell_quote "$INSTALLER_VERSION")"
    printf 'PROJECT_DIR=%s\n' "$(shell_quote "$PROJECT_DIR")"
    printf 'REPO_URL=%s\n' "$(shell_quote "$REPO_URL")"
    printf 'REPO_BRANCH=%s\n' "$(shell_quote "$REPO_BRANCH")"
    printf 'RAW_BASE_URL=%s\n' "$(shell_quote "$RAW_BASE_URL")"
    printf 'REPO_DIR_NAME=%s\n' "$(shell_quote "$REPO_DIR_NAME")"
    printf 'PROJECT_VERSION_FILE=%s\n' "$(shell_quote "$PROJECT_VERSION_FILE")"
    printf 'SKILL_REL_PATH=%s\n' "$(shell_quote "$SKILL_REL_PATH")"
    printf 'JIRA_CLI_REPO=%s\n' "$(shell_quote "$JIRA_CLI_REPO")"
    printf 'JIRA_CLI_LATEST_URL=%s\n' "$(shell_quote "$JIRA_CLI_LATEST_URL")"
    printf 'JIRA_CLI_SCRIPT_REL_PATH=%s\n' "$(shell_quote "$JIRA_CLI_SCRIPT_REL_PATH")"
    printf 'JIRA_CLI_INSTALL_URL=%s\n' "$(shell_quote "$JIRA_CLI_INSTALL_URL")"
    printf 'export APP_NAME INSTALLER_VERSION PROJECT_DIR REPO_URL REPO_BRANCH RAW_BASE_URL REPO_DIR_NAME PROJECT_VERSION_FILE SKILL_REL_PATH JIRA_CLI_REPO JIRA_CLI_LATEST_URL JIRA_CLI_SCRIPT_REL_PATH JIRA_CLI_INSTALL_URL\n'
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

    _local_version="$(get_project_version_from_dir "$PROJECT_DIR" 2>/dev/null || true)"
    _local_commit="$(get_local_project_commit 2>/dev/null || true)"

    git fetch origin "$REPO_BRANCH"

    _remote_version="$(get_fetched_remote_project_version 2>/dev/null || true)"
    _remote_commit="$(get_fetched_remote_project_commit 2>/dev/null || true)"
    _current="$(git rev-parse HEAD)"
    _remote="$(git rev-parse "origin/$REPO_BRANCH")"

    say "本地源码版本：${_local_version:-unknown} (${_local_commit:-unknown})"
    say "远端源码版本：${_remote_version:-unknown} (${_remote_commit:-unknown})"

    if [ "$_current" = "$_remote" ]; then
      say "工程源码已是最新版本。"
    elif git merge-base --is-ancestor "$_current" "$_remote"; then
      say "发现工程源码更新，正在执行 fast-forward pull。"
      git pull --ff-only origin "$REPO_BRANCH"
      _after_version="$(get_project_version_from_dir "$PROJECT_DIR" 2>/dev/null || true)"
      _after_commit="$(get_local_project_commit 2>/dev/null || true)"
      say "更新后源码版本：${_after_version:-unknown} (${_after_commit:-unknown})"
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

  die "无法通过项目脚本更新 jira-cli；brew/go fallback 已暂时停用。你可以设置 JIRA_CLI_UPDATE_CMD 来指定升级命令。"
}

resolve_install_config() {
  if [ -n "$SKILL_INSTALL_DIR" ]; then
    _skill_install_path="$SKILL_INSTALL_DIR"
  else
    _skill_install_path="$(prompt_required "请输入 skill 安装路径" "$DEFAULT_SKILL_INSTALL_DIR" "SKILL_INSTALL_DIR")"
  fi
}

install_flow() {
  ensure_project_source
  ensure_jira_cli
  run_jira_init

  if ! is_disabled "$SKIP_CONFIG_STEPS"; then
    say ""
    say "源码、jira-cli 安装和 jira-cli 初始化完成，已按临时开关 SKIP_CONFIG_STEPS=1 跳过 skill/launcher 配置。"
    say "源码目录：$PROJECT_DIR"
    return 0
  fi

  say ""
  say "开始初始化配置。"

  resolve_install_config
  create_skill_symlink "$_skill_install_path"
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

  if ! is_disabled "$SKIP_CONFIG_STEPS"; then
    say ""
    say "源码和 jira-cli 更新检查完成，已按临时开关 SKIP_CONFIG_STEPS=1 跳过 skill/netrc/jira init。"
    say "源码目录：$PROJECT_DIR"
    return 0
  fi

  say "更新流程完成。"
}

version_flow() {
  say "${APP_NAME} installer version: $INSTALLER_VERSION"
  say "source path: $PROJECT_DIR"

  if [ -d "$PROJECT_DIR/.git" ]; then
    _local_version="$(get_project_version_from_dir "$PROJECT_DIR" 2>/dev/null || true)"
    _local_commit="$(get_local_project_commit 2>/dev/null || true)"
    _remote_version="$(get_remote_project_version 2>/dev/null || true)"
    _remote_commit="$(get_remote_project_commit 2>/dev/null || true)"

    say "source local : ${_local_version:-unknown} (${_local_commit:-unknown})"
    say "source remote: ${_remote_version:-unknown} (${_remote_commit:-unknown})"
  else
    say "source local : not installed"
    _remote_version="$(get_remote_project_version 2>/dev/null || true)"
    _remote_commit="$(get_remote_project_commit 2>/dev/null || true)"
    say "source remote: ${_remote_version:-unknown} (${_remote_commit:-unknown})"
  fi

  if _jira_local="$(get_local_jira_cli_version 2>/dev/null)"; then
    say "jira-cli local : $_jira_local"
  else
    say "jira-cli local : not installed"
  fi

  if _jira_latest="$(get_latest_jira_cli_version 2>/dev/null)"; then
    say "jira-cli latest: $_jira_latest"
  else
    say "jira-cli latest: unknown"
  fi
}

parse_path_args() {
  _install_path_arg=""

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --path|-p|--dir|--install-dir)
        _opt="$1"
        shift
        [ "$#" -gt 0 ] || die "${_opt} 需要路径参数。"
        _install_path_arg="$1"
        ;;
      --)
        shift
        [ "$#" -gt 0 ] || die "-- 后面需要路径参数。"
        if [ -n "$_install_path_arg" ]; then
          die "安装路径重复：$_install_path_arg 和 $1"
        fi
        _install_path_arg="$1"
        ;;
      -*)
        die "未知参数：$1"
        ;;
      *)
        if [ -n "$_install_path_arg" ]; then
          die "多余参数：$1"
        fi
        _install_path_arg="$1"
        ;;
    esac

    shift
  done

  if [ -n "$_install_path_arg" ]; then
    set_project_dir_from_install_dir "$_install_path_arg"
  fi
}

parse_args() {
  _cmd="install"

  if [ "$#" -eq 0 ]; then
    return 0
  fi

  case "$1" in
    install)
      _cmd="install"
      shift
      parse_path_args "$@"
      ;;
    update|upgrade)
      _cmd="update"
      shift
      parse_path_args "$@"
      ;;
    version|-v|--version)
      _cmd="version"
      shift
      parse_path_args "$@"
      ;;
    help|-h|--help)
      _cmd="help"
      ;;
    --path|-p|--dir|--install-dir)
      _cmd="install"
      parse_path_args "$@"
      ;;
    -*)
      usage
      die "未知参数：$1"
      ;;
    *)
      _cmd="install"
      parse_path_args "$@"
      ;;
  esac
}

normalize_paths() {
  if [ -z "$PROJECT_DIR" ]; then
    set_project_dir_from_install_dir "$INSTALL_DIR"
  fi

  INSTALL_DIR="$(expand_user_path "$INSTALL_DIR")"
  PROJECT_DIR="$(expand_user_path "$PROJECT_DIR")"
  BIN_DIR="$(expand_user_path "$BIN_DIR")"
  DEFAULT_SKILL_INSTALL_DIR="$(expand_user_path "$DEFAULT_SKILL_INSTALL_DIR")"
  if [ -n "$SKILL_INSTALL_DIR" ]; then
    SKILL_INSTALL_DIR="$(expand_user_path "$SKILL_INSTALL_DIR")"
  fi
}

main() {
  parse_args "$@"
  normalize_paths

  case "$_cmd" in
    install)
      install_flow
      ;;
    update)
      update_flow
      ;;
    version)
      version_flow
      ;;
    help)
      usage
      ;;
    *)
      usage
      die "未知命令：$_cmd"
      ;;
  esac
}

main "$@"
