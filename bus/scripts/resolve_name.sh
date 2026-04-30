#!/usr/bin/env bash
# resolve_name.sh — translate bus name → session_id for use by send.ts reply verb.
#
# Usage:
#   bash resolve_name.sh <name-or-sid>
#
# If arg is numeric: print it unchanged, exit 0.
# If arg is a bus name (e.g. "B"): look up registry for most-recent active entry
#   with ts >= (now - 60); print session_id, exit 0.
# If not found: print nothing, exit 1.
#
# Registry path: ~/.claude/bus/registry.jsonl
# BUS_DIR override (for tests): BUS_DIR=/tmp/xxx/bus
#
# Example:
#   resolve_name.sh B         → "22222"  (exit 0)
#   resolve_name.sh 22222     → "22222"  (exit 0)
#   resolve_name.sh zombie    → ""       (exit 1)

set -euo pipefail

BUS_DIR="${BUS_DIR:-${HOME}/.claude/bus}"
REGISTRY="${BUS_DIR}/registry.jsonl"
ARG="${1:-}"

if [ -z "$ARG" ]; then
  echo "[resolve_name] usage: resolve_name.sh <name-or-sid>" >&2
  exit 1
fi

# Numeric: pass through
if [[ "$ARG" =~ ^[0-9]+$ ]]; then
  echo "$ARG"
  exit 0
fi

# Name lookup
if [ ! -f "$REGISTRY" ]; then
  echo "[resolve_name] registry not found: $REGISTRY" >&2
  exit 1
fi

NOW=$(date +%s)
CUTOFF=$((NOW - 60))

SID=$(jq -sr --arg n "$ARG" --argjson cutoff "$CUTOFF" \
  '[.[] | select(.name == $n) | select(.ts != null) |
    select((.ts | sub("\\.[0-9]+Z$";"Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) >= $cutoff)] |
    if length == 0 then empty
    else max_by(.ts | sub("\\.[0-9]+Z$";"Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) | .session_id
    end' \
  "$REGISTRY" 2>/dev/null | tr -d '"')

if [ -z "$SID" ] || [ "$SID" = "null" ]; then
  echo "[resolve_name] no active peer named '$ARG' within 60s" >&2
  exit 1
fi

echo "$SID"
exit 0
