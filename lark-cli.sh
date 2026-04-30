#!/usr/bin/env sh
set -eu

###############################################################################
# Lark CLI helper
#
# Manages the official Lark/Feishu CLI used by this repository to prepare the
# later Jira Markdown report -> Lark document publishing flow.
###############################################################################

LARK_CLI_NPM_PACKAGE="${LARK_CLI_NPM_PACKAGE:-@larksuite/cli}"
LARK_CLI_SKILL_SOURCE="${LARK_CLI_SKILL_SOURCE:-https://open.feishu.cn}"
LARK_CLI_SKIP_SKILL="${LARK_CLI_SKIP_SKILL:-0}"
LARK_CLI_NPM_FALLBACK_PREFIX="${LARK_CLI_NPM_FALLBACK_PREFIX:-$HOME/.local/npm}"

NPM_INSTALL_MODE="global"
NPM_INSTALL_PREFIX=""

say() {
  printf '%s\n' "$*"
}

warn() {
  printf '! %s\n' "$*" >&2
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

blank() {
  say ""
}

section() {
  blank
  say "== $1 =="
}

summary_item() {
  _label="$1"
  _value="${2:-}"

  [ -n "$_value" ] || _value="-"
  say "  - ${_label}: ${_value}"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

need_cmd() {
  has_cmd "$1" || die "缺少必要命令：$1"
}

is_disabled() {
  case "${1:-}" in
    0|false|FALSE|no|NO|off|OFF|"")
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
  sh lark-cli.sh help        显示帮助
  sh lark-cli.sh doctor      检查 Node/npm/npx、PATH、lark-cli 和登录状态
  sh lark-cli.sh install     安装官方 Lark CLI 和 CLI Skill，不执行配置或登录
  sh lark-cli.sh config      执行 lark-cli config init --new
  sh lark-cli.sh login       执行 lark-cli auth login --recommend
  sh lark-cli.sh status      显示 lark-cli auth status
  sh lark-cli.sh update      升级官方 Lark CLI 并刷新 CLI Skill
  sh lark-cli.sh bootstrap   安装、配置、登录并检查状态

Environment:
  LARK_CLI_NPM_PACKAGE       npm 包名，默认：${LARK_CLI_NPM_PACKAGE}
  LARK_CLI_SKILL_SOURCE      CLI Skill 来源，默认：${LARK_CLI_SKILL_SOURCE}
  LARK_CLI_SKIP_SKILL        设为 1/true 时跳过 Skill 安装，默认：0
  LARK_CLI_NPM_FALLBACK_PREFIX npm 全局目录无权限时的用户级安装目录，默认：${LARK_CLI_NPM_FALLBACK_PREFIX}

Official flow:
  npm install -g @larksuite/cli
  npx -y skills add https://open.feishu.cn --skill -y
  lark-cli config init --new
  lark-cli auth login --recommend
  lark-cli auth status
EOF
}

get_npm_prefix() {
  if has_cmd npm; then
    npm config get prefix 2>/dev/null || true
  fi
}

get_npm_global_bin() {
  _prefix="$(get_npm_prefix)"
  if [ -n "$_prefix" ] && [ "$_prefix" != "undefined" ]; then
    printf '%s\n' "${_prefix%/}/bin"
  fi
}

get_npm_global_root() {
  if has_cmd npm; then
    npm root -g 2>/dev/null || true
  fi
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

path_write_target() {
  _path="$1"

  if [ -d "$_path" ]; then
    printf '%s\n' "$_path"
    return 0
  fi

  dirname "$_path"
}

is_npm_global_writable() {
  _root="$(get_npm_global_root)"
  [ -n "$_root" ] || return 1

  _target="$(path_write_target "$_root")"
  [ -d "$_target" ] && [ -w "$_target" ]
}

prompt_yes_no() {
  _prompt="$1"
  _default="${2:-n}"

  if [ ! -t 0 ]; then
    return 1
  fi

  while :; do
    if [ "$_default" = "y" ]; then
      printf '? %s [Y/n]: ' "$_prompt" >&2
    else
      printf '? %s [y/N]: ' "$_prompt" >&2
    fi

    IFS= read -r _answer || true
    if [ -z "$_answer" ]; then
      _answer="$_default"
    fi

    case "$(printf '%s\n' "$_answer" | tr '[:upper:]' '[:lower:]')" in
      y|yes)
        return 0
        ;;
      n|no)
        return 1
        ;;
      *)
        warn "请输入 y 或 n。"
        ;;
    esac
  done
}

is_path_contains() {
  _needle="$1"

  [ -n "$_needle" ] || return 1
  case ":${PATH:-}:" in
    *:"$_needle":*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

print_path_hint() {
  _bin="$(get_npm_global_bin)"

  if [ -z "$_bin" ]; then
    warn "无法推导 npm 全局 bin 目录，请检查 npm config get prefix。"
    return 0
  fi

  if is_path_contains "$_bin"; then
    warn "npm 全局 bin 已在 PATH 中：$_bin"
    return 0
  fi

  warn "如果安装后找不到 lark-cli，请把 npm 全局 bin 目录加入 PATH："
  warn "  export PATH=\"$_bin:\$PATH\""
}

print_fallback_path_hint() {
  _prefix="$(expand_user_path "$LARK_CLI_NPM_FALLBACK_PREFIX")"
  _bin="${_prefix%/}/bin"

  warn "用户级 npm bin 目录为：$_bin"
  if is_path_contains "$_bin"; then
    warn "该目录已在当前 PATH 中。"
  else
    warn "安装完成后请把下面这行加入 ~/.zshrc 或 ~/.bashrc："
    warn "  export PATH=\"$_bin:\$PATH\""
  fi
}

prepare_npm_install_permission() {
  NPM_INSTALL_MODE="global"
  NPM_INSTALL_PREFIX=""

  _prefix="$(get_npm_prefix)"
  _root="$(get_npm_global_root)"
  summary_item "npm prefix" "$_prefix"
  summary_item "npm global root" "$_root"

  if is_npm_global_writable; then
    summary_item "npm global writable" "yes"
    return 0
  fi

  summary_item "npm global writable" "no"
  warn "当前用户没有权限写入 npm 全局目录：${_root:-unknown}"

  if has_cmd sudo && [ -t 0 ]; then
    warn "将尝试通过 sudo 获取一次安装权限；sudo 会直接提示你输入系统密码。"
    if sudo -v; then
      NPM_INSTALL_MODE="sudo"
      summary_item "npm install mode" "sudo"
      return 0
    fi

    warn "sudo 授权未完成或被拒绝。"
  elif ! has_cmd sudo; then
    warn "当前环境没有 sudo 命令。"
  else
    warn "当前不是交互式终端，无法请求 sudo 密码。"
  fi

  _fallback_prefix="$(expand_user_path "$LARK_CLI_NPM_FALLBACK_PREFIX")"
  if prompt_yes_no "是否改为安装到用户级 fallback 路径 $_fallback_prefix？" "y"; then
    mkdir -p "${_fallback_prefix%/}/bin"
    NPM_INSTALL_MODE="user"
    NPM_INSTALL_PREFIX="$_fallback_prefix"
    PATH="${_fallback_prefix%/}/bin:$PATH"
    export PATH
    summary_item "npm install mode" "user prefix: $_fallback_prefix"
    print_fallback_path_hint
    return 0
  fi

  warn "未获得 sudo 权限，也未选择 fallback 路径，结束 Lark CLI 安装流程。"
  return 1
}

run_npm_global_install() {
  _package="$1"

  case "$NPM_INSTALL_MODE" in
    sudo)
      sudo npm install -g "$_package"
      ;;
    user)
      npm install -g --prefix "$NPM_INSTALL_PREFIX" "$_package"
      ;;
    *)
      npm install -g "$_package"
      ;;
  esac
}

get_lark_cli_version() {
  if ! has_cmd lark-cli; then
    return 1
  fi

  lark-cli --version 2>/dev/null \
    || lark-cli version 2>/dev/null \
    || true
}

get_npm_latest_version() {
  if has_cmd npm; then
    npm view "$LARK_CLI_NPM_PACKAGE" version 2>/dev/null || true
  fi
}

require_lark_cli() {
  if ! has_cmd lark-cli; then
    warn "未找到 lark-cli。"
    warn "请先执行：sh lark-cli.sh install"
    print_path_hint
    return 1
  fi
}

install_skill() {
  if is_disabled "$LARK_CLI_SKIP_SKILL"; then
    section "安装 Lark CLI Skill"
    if npx -y skills add "$LARK_CLI_SKILL_SOURCE" --skill -y; then
      return 0
    fi

    warn "CLI Skill 安装失败，可稍后重试：npx -y skills add ${LARK_CLI_SKILL_SOURCE} --skill -y"
    return 1
  else
    warn "已按 LARK_CLI_SKIP_SKILL=${LARK_CLI_SKIP_SKILL} 跳过 CLI Skill 安装。"
    return 2
  fi
}

doctor_cmd() {
  section "Lark CLI 环境检查"

  if has_cmd node; then
    summary_item "Node.js" "$(node -v 2>/dev/null || true)"
  else
    summary_item "Node.js" "not installed"
  fi

  if has_cmd npm; then
    summary_item "npm" "$(npm -v 2>/dev/null || true)"
    summary_item "npm prefix" "$(get_npm_prefix)"
    summary_item "npm global root" "$(get_npm_global_root)"
    if is_npm_global_writable; then
      summary_item "npm global writable" "yes"
    else
      summary_item "npm global writable" "no"
    fi
    _npm_bin="$(get_npm_global_bin)"
    summary_item "npm global bin" "$_npm_bin"
    if [ -n "$_npm_bin" ]; then
      if is_path_contains "$_npm_bin"; then
        summary_item "PATH contains npm bin" "yes"
      else
        summary_item "PATH contains npm bin" "no"
      fi
    fi
  else
    summary_item "npm" "not installed"
  fi

  if has_cmd npx; then
    summary_item "npx" "$(command -v npx)"
  else
    summary_item "npx" "not installed"
  fi

  if has_cmd lark-cli; then
    summary_item "lark-cli" "$(command -v lark-cli)"
    _version="$(get_lark_cli_version | sed -n '1p')"
    summary_item "lark-cli version" "$_version"

    section "Lark CLI 登录状态"
    if lark-cli auth status; then
      summary_item "auth" "ok"
    else
      warn "lark-cli auth status 执行失败，通常表示尚未登录或授权已失效。"
      summary_item "auth" "needs login"
    fi
  else
    summary_item "lark-cli" "not installed"
    summary_item "auth" "not checked"
  fi

  if ! has_cmd node || ! has_cmd npm || ! has_cmd npx || ! has_cmd lark-cli; then
    section "建议"
    if ! has_cmd node; then
      say "  - 请先安装 Node.js LTS。"
    fi
    if ! has_cmd npm || ! has_cmd npx; then
      say "  - 请修复 Node.js/npm 环境，确保 npm 和 npx 可用。"
    fi
    if ! has_cmd lark-cli; then
      say "  - 执行 sh lark-cli.sh install 安装官方 Lark CLI。"
    fi
    print_path_hint
  fi
}

install_cmd() {
  section "检查基础环境"
  need_cmd node
  need_cmd npm
  need_cmd npx
  summary_item "Node.js" "$(node -v 2>/dev/null || true)"
  summary_item "npm" "$(npm -v 2>/dev/null || true)"
  summary_item "npx" "$(command -v npx)"
  prepare_npm_install_permission || return 1

  section "安装 Lark CLI"
  run_npm_global_install "$LARK_CLI_NPM_PACKAGE"

  _skill_status="installed"
  install_skill || _skill_status="failed or skipped"

  section "安装结果"
  if has_cmd lark-cli; then
    summary_item "lark-cli" "$(command -v lark-cli)"
    _version="$(get_lark_cli_version | sed -n '1p')"
    summary_item "version" "$_version"
    summary_item "CLI Skill" "$_skill_status"
  else
    warn "npm 安装已执行，但当前 PATH 中仍找不到 lark-cli。"
    print_path_hint
    return 1
  fi

  section "后续步骤"
  say "  sh lark-cli.sh config"
  say "  sh lark-cli.sh login"
  say "  sh lark-cli.sh status"
}

config_cmd() {
  require_lark_cli || return 1

  section "初始化 Lark CLI 配置"
  warn "该步骤可能会打开浏览器或输出链接，需要你完成飞书应用配置确认。"
  warn "本项目不会保存 App Secret、access token 或 refresh token。"
  if lark-cli config init --new; then
    return 0
  fi

  warn "配置流程未完成，可稍后重新执行：sh lark-cli.sh config"
  return 1
}

login_cmd() {
  require_lark_cli || return 1

  section "登录 Lark CLI"
  warn "该步骤会进入飞书 OAuth 授权流程，授权范围以飞书官方页面展示为准。"
  warn "本项目不会读取或保存飞书 token。"
  if ! lark-cli auth login --recommend; then
    warn "登录流程未完成，可稍后重新执行：sh lark-cli.sh login"
    return 1
  fi

  section "登录状态"
  if lark-cli auth status; then
    return 0
  fi

  warn "登录状态检查失败，可稍后重新执行：sh lark-cli.sh login"
  return 1
}

status_cmd() {
  require_lark_cli || return 1

  section "Lark CLI 登录状态"
  if lark-cli auth status; then
    return 0
  fi

  warn "当前可能尚未登录或授权已失效。"
  warn "请执行：sh lark-cli.sh login"
  return 1
}

update_cmd() {
  section "检查基础环境"
  need_cmd npm
  need_cmd npx
  prepare_npm_install_permission || return 1

  _before=""
  if has_cmd lark-cli; then
    _before="$(get_lark_cli_version | sed -n '1p')"
  fi
  _latest="$(get_npm_latest_version)"
  summary_item "current" "$_before"
  summary_item "latest" "$_latest"

  section "升级 Lark CLI"
  run_npm_global_install "${LARK_CLI_NPM_PACKAGE}@latest"

  _skill_status="installed"
  install_skill || _skill_status="failed or skipped"

  section "升级结果"
  if has_cmd lark-cli; then
    summary_item "lark-cli" "$(command -v lark-cli)"
    _after="$(get_lark_cli_version | sed -n '1p')"
    summary_item "version" "$_after"
    summary_item "CLI Skill" "$_skill_status"
  else
    warn "升级命令已执行，但当前 PATH 中仍找不到 lark-cli。"
    print_path_hint
    return 1
  fi

  section "登录状态"
  if lark-cli auth status; then
    return 0
  fi

  warn "登录状态检查失败，升级已完成；如需授权请执行：sh lark-cli.sh login"
}

bootstrap_cmd() {
  section "Lark CLI 一键接入"
  say "该流程用于准备后续将 Jira Markdown 报告发布为飞书云文档，并发送给指定对象。"
  warn "流程中会安装官方 Lark CLI，随后需要你在浏览器中完成配置和 OAuth 授权。"
  warn "授权范围以飞书官方页面展示为准，本项目不会读取或保存飞书凭据。"

  doctor_cmd
  install_cmd
  config_cmd
  login_cmd
  status_cmd
}

cmd="${1:-help}"
case "$cmd" in
  help|-h|--help)
    usage
    ;;
  doctor)
    doctor_cmd
    ;;
  install)
    install_cmd
    ;;
  config)
    config_cmd
    ;;
  login)
    login_cmd
    ;;
  status)
    status_cmd
    ;;
  update)
    update_cmd
    ;;
  bootstrap)
    bootstrap_cmd
    ;;
  *)
    usage >&2
    die "未知命令：$cmd"
    ;;
esac
