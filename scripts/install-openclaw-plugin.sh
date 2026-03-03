#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR_DEFAULT="$ROOT_DIR/plugins/ts-openclaw-channel"
PLUGIN_DIR="${1:-$PLUGIN_DIR_DEFAULT}"
PLUGIN_ID="ts-openclaw-channel"
TIMEOUT_SEC="${OPENCLAW_CMD_TIMEOUT_SEC:-20}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "error: openclaw command not found in PATH" >&2
  exit 1
fi

if [ ! -d "$PLUGIN_DIR" ]; then
  echo "error: plugin directory not found: $PLUGIN_DIR" >&2
  exit 1
fi

run_openclaw_cmd() {
  local label="$1"
  local success_regex="$2"
  shift 2
  local tmp
  tmp="$(mktemp)"
  set +e
  timeout "${TIMEOUT_SEC}s" "$@" >"$tmp" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -ne 0 ]; then
    if [ "$rc" -eq 124 ] && rg -q "$success_regex" "$tmp"; then
      echo "warn: command timed out but success marker detected (${label})" >&2
    else
      echo "error: command failed or timed out (${label})" >&2
      sed -n '1,160p' "$tmp" >&2
      rm -f "$tmp"
      exit 1
    fi
  fi

  sed -n '1,160p' "$tmp"
  rm -f "$tmp"
}

echo "==> install (link): $PLUGIN_DIR"
run_openclaw_cmd "plugins install" "Linked plugin path|already installed|Install path" \
  openclaw plugins install --link "$PLUGIN_DIR"

echo "==> enable: $PLUGIN_ID"
run_openclaw_cmd "plugins enable" "Enabled plugin|already enabled" \
  openclaw plugins enable "$PLUGIN_ID"

echo "==> verify: list enabled plugins"
run_openclaw_cmd "plugins list" "ts-openclaw-channel" \
  openclaw plugins list --enabled --verbose

echo "==> verify: plugin info"
run_openclaw_cmd "plugins info" "id: ts-openclaw-channel|\"id\": \"ts-openclaw-channel\"" \
  openclaw plugins info "$PLUGIN_ID"

cat <<'EOF'
done.
if openclaw gateway is already running, restart it to load the latest plugin build.
EOF
