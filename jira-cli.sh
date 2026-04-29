#!/usr/bin/env bash
# Copyright (c) 2026 Zepp Health. All rights reserved.
# Author: Gan GAN
# Affiliation: Zepp Health, Active BU AI Lab
set -euo pipefail

REPO="ankitpokhrel/jira-cli"
INSTALL_DIR="${JIRA_CLI_BIN_DIR:-/usr/local/bin}"
BINARY_NAME="jira"
GITHUB_LATEST_URL="https://github.com/${REPO}/releases/latest"
GITHUB_RELEASE_BASE="https://github.com/${REPO}/releases/download"
TMP_DIR_TO_CLEAN=""

usage() {
  cat <<EOF
Usage:
  $0 install     Install latest jira-cli
  $0 update      Update jira-cli if a newer version exists
  $0 version     Show local and latest versions
  $0 help        Show this help

Examples:
  $0 install
  $0 update
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_binary() {
  local source="$1"
  local target="$2"

  mkdir -p "$(dirname "$target")"

  if install -m 0755 "$source" "$target" 2>/dev/null; then
    return 0
  fi

  if ! need_cmd sudo; then
    echo "Permission denied installing to ${target}, and sudo is not available."
    exit 1
  fi

  sudo install -m 0755 "$source" "$target"
}

ensure_deps() {
  echo "[1/7] Checking dependencies..."

  local missing=()

  for cmd in curl tar find grep sed sort; do
    if ! need_cmd "$cmd"; then
      missing+=("$cmd")
    fi
  done

  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "Installing missing packages: ${missing[*]}"
    sudo apt-get update
    sudo apt-get install -y curl tar findutils grep sed coreutils ca-certificates
  fi
}

detect_platform() {
  OS="linux"
  ARCH="$(uname -m)"

  case "$ARCH" in
    x86_64 | amd64)
      ASSET_ARCH="x86_64"
      ;;
    aarch64 | arm64)
      ASSET_ARCH="arm64"
      ;;
    i386 | i686)
      ASSET_ARCH="i386"
      ;;
    armv6l)
      ASSET_ARCH="armv6"
      ;;
    armv7l)
      ASSET_ARCH="armv7"
      ;;
    *)
      echo "Unsupported architecture: $ARCH"
      exit 1
      ;;
  esac
}

fetch_latest_tag() {
  local effective_url tag

  effective_url="$(curl -fsSL -o /dev/null -w '%{url_effective}' "$GITHUB_LATEST_URL")"
  tag="${effective_url##*/}"

  if [[ -z "$tag" || "$tag" == "$effective_url" || "$tag" != v* ]]; then
    echo "Failed to resolve latest jira-cli release tag from ${GITHUB_LATEST_URL}." >&2
    return 1
  fi

  echo "$tag"
}

get_latest_version() {
  fetch_latest_tag | sed 's/^v//'
}

get_local_version() {
  if ! need_cmd "$BINARY_NAME"; then
    return 1
  fi

  local output version

  output="$(
    {
      "$BINARY_NAME" version 2>/dev/null || true
      "$BINARY_NAME" --version 2>/dev/null || true
    } | head -n 5
  )"

  version="$(
    echo "$output" |
      grep -Eo 'v?[0-9]+(\.[0-9]+){1,3}([-+][0-9A-Za-z.-]+)?' |
      head -n 1 |
      sed 's/^v//'
  )"

  if [[ -z "$version" ]]; then
    return 1
  fi

  echo "$version"
}

resolve_download_url() {
  local version="$1"

  echo "${GITHUB_RELEASE_BASE}/v${version}/jira_${version}_${OS}_${ASSET_ARCH}.tar.gz"
}

install_version() {
  local latest_version="$1"
  detect_platform

  local tag_name download_url tmp_dir archive jira_bin

  if [[ -z "$latest_version" ]]; then
    echo "Failed to resolve latest version."
    exit 1
  fi

  tag_name="v${latest_version}"

  echo "[2/7] Latest release: ${tag_name}"
  echo "[3/7] Detected platform: ${OS}/${ASSET_ARCH}"

  download_url="$(resolve_download_url "$latest_version")"

  if ! curl -fsSIL "$download_url" >/dev/null; then
    echo "Could not find a release asset for ${OS}/${ASSET_ARCH}:"
    echo "$download_url"
    exit 1
  fi

  echo "[4/7] Downloading:"
  echo "$download_url"

  tmp_dir="$(mktemp -d)"
  TMP_DIR_TO_CLEAN="$tmp_dir"
  trap 'rm -rf "$TMP_DIR_TO_CLEAN"' EXIT

  archive="${tmp_dir}/jira-cli.tar.gz"

  curl -fL "$download_url" -o "$archive"

  echo "[5/7] Extracting..."
  tar -xzf "$archive" -C "$tmp_dir"

  jira_bin="$(find "$tmp_dir" -type f -name "$BINARY_NAME" | head -n 1)"

  if [[ -z "$jira_bin" ]]; then
    echo "Could not find jira binary in extracted archive."
    exit 1
  fi

  chmod +x "$jira_bin"

  echo "[6/7] Installing to ${INSTALL_DIR}/${BINARY_NAME}..."
  install_binary "$jira_bin" "${INSTALL_DIR}/${BINARY_NAME}"

  echo "[7/7] Verifying installation..."
  "${INSTALL_DIR}/${BINARY_NAME}" version || "${INSTALL_DIR}/${BINARY_NAME}" --version || true

  echo
  echo "jira-cli ${latest_version} installed successfully."
}

cmd_install() {
  ensure_deps

  echo "Installing latest jira-cli..."
  local latest_version
  latest_version="$(get_latest_version)"

  install_version "$latest_version"

  echo
  echo "Next step:"
  echo "  jira init"
}

cmd_update() {
  ensure_deps

  echo "Checking for jira-cli updates..."

  local latest_version local_version
  latest_version="$(get_latest_version)"

  if [[ -z "$latest_version" || "$latest_version" == "null" ]]; then
    echo "Failed to resolve latest version."
    exit 1
  fi

  if ! local_version="$(get_local_version)"; then
    echo "jira-cli is not installed or local version could not be detected."
    echo "Installing latest version: ${latest_version}"
    install_version "$latest_version"
    return
  fi

  echo "Local version : ${local_version}"
  echo "Latest version: ${latest_version}"

  if [[ "$(printf '%s\n%s\n' "$local_version" "$latest_version" | sort -V | tail -n 1)" == "$latest_version" \
    && "$latest_version" != "$local_version" ]]; then
    echo "New version available. Updating jira-cli..."
    install_version "$latest_version"
  else
    echo "Already up to date."
  fi
}

cmd_version() {
  ensure_deps

  local latest_version local_version
  latest_version="$(get_latest_version)"

  if local_version="$(get_local_version)"; then
    echo "Local version : ${local_version}"
  else
    echo "Local version : not installed"
  fi

  echo "Latest version: ${latest_version}"
}

main() {
  local command="${1:-help}"

  case "$command" in
    install)
      cmd_install
      ;;
    update)
      cmd_update
      ;;
    version)
      cmd_version
      ;;
    help | -h | --help)
      usage
      ;;
    *)
      echo "Unknown command: $command"
      echo
      usage
      exit 1
      ;;
  esac
}

main "$@"
