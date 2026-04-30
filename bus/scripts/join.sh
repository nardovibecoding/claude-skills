#!/bin/bash
# join.sh — atomic /radio join. Picks A..Z (fallback AA..AZ); writes registry + sentinel.
# Inputs (env): BUS_NAME (optional, force a name); BUS_FORCE_SID (optional, test override).
# Output: JSON to stdout. Exit 0 on success, 1 on failure.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/_lock_lib.sh"

# Resolve session_id BEFORE lock (cheap, fail-fast).
SID=$(_bus_resolve_sid) || {
  _bus_emit_json false "" "" "no_claude_ancestor"
  exit 1
}

# Validate name input if provided. Auto-uppercase.
REQUESTED=""
if [ -n "${BUS_NAME:-}" ]; then
  REQUESTED=$(echo "$BUS_NAME" | tr '[:lower:]' '[:upper:]')
  if ! _bus_validate_name "$REQUESTED"; then
    _bus_emit_json false "" "$SID" "invalid_name"
    exit 1
  fi
fi

# Acquire lock; trap release on any exit path.
if ! _bus_lock_acquire; then
  _bus_emit_json false "" "$SID" "lock_timeout"
  exit 1
fi
trap _bus_lock_release EXIT INT TERM

# Critical section: sweep stale, read used, pick, append.
_bus_sweep_stale_sentinels

USED=$(_bus_used_names)

if [ -n "$REQUESTED" ]; then
  if echo "$USED" | grep -qx "$REQUESTED"; then
    _bus_emit_json false "" "$SID" "name_taken"
    exit 1
  fi
  NAME="$REQUESTED"
else
  NAME=$(_bus_pick_name "$USED") || {
    _bus_emit_json false "" "$SID" "all_names_exhausted"
    exit 1
  }
fi

TS=$(date +%s)
HOSTNAME_S=$(hostname -s 2>/dev/null || echo unknown)

# Append registry entry (single jq call, no manual escaping).
jq -cn \
  --arg n "$NAME" \
  --arg sid "$SID" \
  --argjson ts "$TS" \
  --arg host "$HOSTNAME_S" \
  '{name:$n, session_id:($sid|tonumber), ts:$ts, hostname:$host}' \
  >> "$BUS_REGISTRY"

# Write sentinel.
echo "joined $(date -u +%FT%TZ) name=$NAME" > "$BUS_OPTIN_DIR/$SID"

_bus_emit_json true "$NAME" "$SID" ""
exit 0
