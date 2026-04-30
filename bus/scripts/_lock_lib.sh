#!/bin/bash
# _lock_lib.sh — shared helpers for join.sh / leave.sh.
# Locking primitive: mkdir-as-lock (atomic on POSIX). flock(1) absent on macOS Bash 3.2.
#
# Usage:
#   source _lock_lib.sh
#   _bus_lock_acquire || exit 1
#   trap _bus_lock_release EXIT INT TERM
#   ... critical section ...

BUS_DIR="${BUS_DIR:-$HOME/.claude/bus}"
BUS_REGISTRY="$BUS_DIR/registry.jsonl"
BUS_LOCK_DIR="$BUS_DIR/registry.lock"
BUS_OPTIN_DIR="$BUS_DIR/opted-in"
BUS_PLUGIN_PID_DIR="$BUS_DIR/plugin-pid"
BUS_LOCK_TIMEOUT_S="${BUS_LOCK_TIMEOUT_S:-5}"   # max wait for lock
BUS_LIVE_WINDOW_S="${BUS_LIVE_WINDOW_S:-60}"    # registry entry liveness window

mkdir -p "$BUS_DIR" "$BUS_OPTIN_DIR" "$BUS_PLUGIN_PID_DIR"

# Atomic lock via mkdir; bounded wait; stale-lock break (>30s old).
_bus_lock_acquire() {
  local waited=0
  local sleep_s="0.05"
  while ! mkdir "$BUS_LOCK_DIR" 2>/dev/null; do
    # Stale-lock breaker: if lock dir older than 30s, remove and retry.
    if [ -d "$BUS_LOCK_DIR" ]; then
      local age
      # macOS stat -f "%m"; GNU stat -c "%Y"
      age=$(stat -f "%m" "$BUS_LOCK_DIR" 2>/dev/null || stat -c "%Y" "$BUS_LOCK_DIR" 2>/dev/null || echo 0)
      local now=$(date +%s)
      if [ $((now - age)) -gt 30 ]; then
        rmdir "$BUS_LOCK_DIR" 2>/dev/null || rm -rf "$BUS_LOCK_DIR" 2>/dev/null
        continue
      fi
    fi
    sleep "$sleep_s"
    waited=$((waited + 1))
    if [ "$waited" -gt $((BUS_LOCK_TIMEOUT_S * 20)) ]; then
      return 1
    fi
  done
  return 0
}

_bus_lock_release() {
  rmdir "$BUS_LOCK_DIR" 2>/dev/null || rm -rf "$BUS_LOCK_DIR" 2>/dev/null
}

# Walk parents up to 16 hops; first ancestor whose argv0 basename = "claude" wins.
# BUS_FORCE_SID overrides for tests.
_bus_resolve_sid() {
  if [ -n "${BUS_FORCE_SID:-}" ]; then
    echo "$BUS_FORCE_SID"
    return 0
  fi
  local p=$(ps -p $$ -o ppid= 2>/dev/null | tr -d ' ')
  local i=0
  while [ "$i" -lt 16 ] && [ -n "$p" ] && [ "$p" != "1" ]; do
    local cmd base
    cmd=$(ps -p "$p" -o command= 2>/dev/null | awk '{print $1}')
    base="${cmd##*/}"
    if [ "$base" = "claude" ]; then
      echo "$p"
      return 0
    fi
    p=$(ps -p "$p" -o ppid= 2>/dev/null | tr -d ' ')
    i=$((i + 1))
  done
  return 1
}

# Stale sentinel sweep: kill -0 each PID; rm sentinel if process gone.
_bus_sweep_stale_sentinels() {
  local f pid
  for f in "$BUS_OPTIN_DIR"/*; do
    [ -f "$f" ] || continue
    pid=$(basename "$f")
    case "$pid" in
      ''|*[!0-9]*) rm -f "$f"; continue ;;
    esac
    kill -0 "$pid" 2>/dev/null || rm -f "$f"
  done
}

# Print used names (active within BUS_LIVE_WINDOW_S), one per line.
_bus_used_names() {
  [ -f "$BUS_REGISTRY" ] || return 0
  jq -rs --argjson win "$BUS_LIVE_WINDOW_S" '
    group_by(.name)
    | map(max_by(.ts))
    | map(select(.ts >= (now - $win)))
    | .[].name
  ' "$BUS_REGISTRY" 2>/dev/null
}

# Validate name: ^[A-Z]+$ only. Reject empty / lowercase-mixed / specials.
_bus_validate_name() {
  local n="$1"
  [ -n "$n" ] || return 1
  case "$n" in
    *[!A-Z]*) return 1 ;;
    *) return 0 ;;
  esac
}

# Pick lowest unused name. A..Z, fallback AA..AZ.
_bus_pick_name() {
  local used="$1"
  local L
  for L in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z; do
    echo "$used" | grep -qx "$L" || { echo "$L"; return 0; }
  done
  for L in AA AB AC AD AE AF AG AH AI AJ AK AL AM AN AO AP AQ AR AS AT AU AV AW AX AY AZ; do
    echo "$used" | grep -qx "$L" || { echo "$L"; return 0; }
  done
  return 1
}

# Emit JSON to stdout. ok=true/false; reason optional.
_bus_emit_json() {
  local ok="$1" name="$2" sid="$3" reason="$4"
  if [ "$ok" = "true" ]; then
    jq -cn --arg n "$name" --arg sid "$sid" \
      '{ok:true, name:$n, session_id:($sid|tonumber)}'
  else
    jq -cn --arg r "$reason" '{ok:false, reason:$r}'
  fi
}
