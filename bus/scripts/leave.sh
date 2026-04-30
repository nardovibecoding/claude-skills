#!/bin/bash
# leave.sh — atomic /radio leave. Removes registry entries + sentinel + plugin-pid;
# SIGTERMs plugin if PID file present.
# Inputs (env): BUS_FORCE_SID (optional, test override).
# Output: JSON to stdout. Exit 0 on success, 1 on failure.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/_lock_lib.sh"

SID=$(_bus_resolve_sid) || {
  _bus_emit_json false "" "" "no_claude_ancestor"
  exit 1
}

if ! _bus_lock_acquire; then
  _bus_emit_json false "" "$SID" "lock_timeout"
  exit 1
fi
trap _bus_lock_release EXIT INT TERM

# Release all own claims before teardown (prevents orphan claim files).
bash "$SCRIPT_DIR/release.sh" --all 2>/dev/null || true

# SIGTERM plugin if its PID file exists. Read before delete; ignore kill failures.
PLUGIN_PID_FILE="$BUS_PLUGIN_PID_DIR/$SID"
if [ -f "$PLUGIN_PID_FILE" ]; then
  PPID_VAL=$(cat "$PLUGIN_PID_FILE" 2>/dev/null)
  case "$PPID_VAL" in
    ''|*[!0-9]*) ;;
    *) kill -TERM "$PPID_VAL" 2>/dev/null || true ;;
  esac
  rm -f "$PLUGIN_PID_FILE"
fi

# Remove sentinel.
rm -f "$BUS_OPTIN_DIR/$SID"

# Drop registry entries matching this SID. Filter+rewrite atomically via temp file.
if [ -f "$BUS_REGISTRY" ]; then
  TMP=$(mktemp "$BUS_DIR/.registry.XXXXXX")
  jq -c --argjson sid "$SID" 'select(.session_id != $sid)' "$BUS_REGISTRY" > "$TMP" 2>/dev/null || true
  mv "$TMP" "$BUS_REGISTRY"
fi

jq -cn --arg sid "$SID" '{ok:true, session_id:($sid|tonumber)}'
exit 0
