#!/usr/bin/env bash
set -euo pipefail

REPO="ankitpokhrel/jira-cli"
INSTALL_DIR="/usr/local/bin"
BINARY_NAME="jira"
GITHUB_API="https://api.github.com/repos/${REPO}/releases/latest"

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

ensure_deps() {
  echo "[1/7] Checking dependencies..."

  local missing=()

  for cmd in curl jq tar find grep sed dpkg; do
    if ! need_cmd "$cmd"; then
      missing+=("$cmd")
    fi
  done

  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "Installing missing packages: ${missing[*]}"
    sudo apt-get update
    sudo apt-get install -y curl jq tar findutils grep sed dpkg ca-certificates
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

fetch_latest_release_json() {
  curl -fsSL "$GITHUB_API"
}

get_latest_version_from_json() {
  jq -r '.tag_name' | sed 's/^v//'
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
  local release_json="$1"

  echo "$release_json" |
    jq -r --arg os "$OS" --arg arch "$ASSET_ARCH" '
      .assets[]
      | select(.name | test("jira_[0-9.]+_" + $os + "_" + $arch + "\\.tar\\.gz$"))
      | .browser_download_url
    ' |
    head -n 1
}

install_from_release_json() {
  local release_json="$1"

  detect_platform

  local tag_name latest_version download_url tmp_dir archive jira_bin

  tag_name="$(echo "$release_json" | jq -r '.tag_name')"
  latest_version="${tag_name#v}"

  if [[ -z "$tag_name" || "$tag_name" == "null" ]]; then
    echo "Failed to resolve latest release tag."
    exit 1
  fi

  echo "[2/7] Latest release: ${tag_name}"
  echo "[3/7] Detected platform: ${OS}/${ASSET_ARCH}"

  download_url="$(resolve_download_url "$release_json")"

  if [[ -z "$download_url" || "$download_url" == "null" ]]; then
    echo "Could not find a release asset for ${OS}/${ASSET_ARCH}."
    echo
    echo "Available assets:"
    echo "$release_json" | jq -r '.assets[].name'
    exit 1
  fi

  echo "[4/7] Downloading:"
  echo "$download_url"

  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT

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
  sudo install -m 0755 "$jira_bin" "${INSTALL_DIR}/${BINARY_NAME}"

  echo "[7/7] Verifying installation..."
  "${INSTALL_DIR}/${BINARY_NAME}" version || "${INSTALL_DIR}/${BINARY_NAME}" --version || true

  echo
  echo "jira-cli ${latest_version} installed successfully."
}

cmd_install() {
  ensure_deps

  echo "Installing latest jira-cli..."
  local release_json
  release_json="$(fetch_latest_release_json)"

  install_from_release_json "$release_json"

  echo
  echo "Next step:"
  echo "  jira init"
}

cmd_update() {
  ensure_deps

  echo "Checking for jira-cli updates..."

  local release_json latest_version local_version

  release_json="$(fetch_latest_release_json)"
  latest_version="$(echo "$release_json" | get_latest_version_from_json)"

  if [[ -z "$latest_version" || "$latest_version" == "null" ]]; then
    echo "Failed to resolve latest version."
    exit 1
  fi

  if ! local_version="$(get_local_version)"; then
    echo "jira-cli is not installed or local version could not be detected."
    echo "Installing latest version: ${latest_version}"
    install_from_release_json "$release_json"
    return
  fi

  echo "Local version : ${local_version}"
  echo "Latest version: ${latest_version}"

  if dpkg --compare-versions "$latest_version" gt "$local_version"; then
    echo "New version available. Updating jira-cli..."
    install_from_release_json "$release_json"
  else
    echo "Already up to date."
  fi
}

cmd_version() {
  ensure_deps

  local release_json latest_version local_version

  release_json="$(fetch_latest_release_json)"
  latest_version="$(echo "$release_json" | get_latest_version_from_json)"

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