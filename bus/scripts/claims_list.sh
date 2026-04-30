#!/bin/bash
# claims_list.sh — list active /radio path claims.
# Usage: bash claims_list.sh [--json]
# Output: human table (default) or JSON array (--json).
# Side-effect: auto-removes claims from dead sessions older than 1h.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/_lock_lib.sh"

BUS_CLAIMS_DIR="${BUS_DIR}/claims"
mkdir -p "$BUS_CLAIMS_DIR"

OWN_SID=$(_bus_resolve_sid 2>/dev/null) || OWN_SID=""

JSON_MODE=false
for arg in "$@"; do
  [ "$arg" = "--json" ] && JSON_MODE=true
done

NOW=$(date +%s)
STALE_THRESHOLD=3600   # 1 hour

ROWS=()       # for human table: "name|age_s|path|mine"
JSON_ITEMS=() # for --json

for claim_file in "$BUS_CLAIMS_DIR"/*; do
  [ -f "$claim_file" ] || continue

  CLAIM_JSON=$(cat "$claim_file" 2>/dev/null) || continue
  CLAIM_SID=$(printf '%s' "$CLAIM_JSON" | jq -r '.session_id' 2>/dev/null || echo "")
  CLAIM_PATH=$(printf '%s' "$CLAIM_JSON" | jq -r '.path' 2>/dev/null || echo "?")
  CLAIM_NAME=$(printf '%s' "$CLAIM_JSON" | jq -r '.name' 2>/dev/null || echo "?")
  CLAIM_TS=$(printf '%s' "$CLAIM_JSON" | jq -r '.ts' 2>/dev/null || echo "")

  # Compute age in seconds from ISO ts.
  if [ -n "$CLAIM_TS" ]; then
    CLAIM_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$CLAIM_TS" +%s 2>/dev/null \
      || date -d "$CLAIM_TS" +%s 2>/dev/null \
      || echo "$NOW")
    AGE_S=$((NOW - CLAIM_EPOCH))
  else
    AGE_S=0
  fi

  # Stale sweep: dead PID + older than threshold.
  IS_DEAD=false
  if [ -n "$CLAIM_SID" ]; then
    case "$CLAIM_SID" in
      ''|*[!0-9]*) IS_DEAD=true ;;
      *) kill -0 "$CLAIM_SID" 2>/dev/null || IS_DEAD=true ;;
    esac
  else
    IS_DEAD=true
  fi

  if $IS_DEAD && [ "$AGE_S" -gt "$STALE_THRESHOLD" ]; then
    rm -f "$claim_file"
    printf '[radio-claims] swept stale claim (dead PID %s, age %ds): %s\n' \
      "$CLAIM_SID" "$AGE_S" "$CLAIM_PATH" >&2
    continue
  fi

  # Mine?
  if [ -n "$OWN_SID" ] && [ "$CLAIM_SID" = "$OWN_SID" ]; then
    MINE="YES"
  else
    MINE="no"
  fi

  # Format age.
  if [ "$AGE_S" -lt 60 ]; then
    AGE_LABEL="${AGE_S}s"
  elif [ "$AGE_S" -lt 3600 ]; then
    AGE_LABEL="$((AGE_S / 60))m"
  else
    AGE_LABEL="$((AGE_S / 3600))h"
  fi

  ROWS+=("${CLAIM_NAME}|${AGE_LABEL}|${CLAIM_PATH}|${MINE}")
  JSON_ITEMS+=("$(printf '%s' "$CLAIM_JSON" | jq -c \
    --arg mine "$MINE" --argjson age "$AGE_S" \
    '. + {mine:($mine == "YES"), age_s:$age}' 2>/dev/null || echo '{}')")
done

if $JSON_MODE; then
  # Output JSON array.
  if [ ${#JSON_ITEMS[@]} -eq 0 ]; then
    echo '[]'
  else
    printf '%s\n' "${JSON_ITEMS[@]}" | jq -s '.'
  fi
  exit 0
fi

# Human table.
if [ ${#ROWS[@]} -eq 0 ]; then
  echo "(no active claims)"
  exit 0
fi

printf '%-10s %-6s %-50s %s\n' "NAME" "AGE" "PATH" "MINE?"
printf '%-10s %-6s %-50s %s\n' "----" "---" "----" "-----"
for row in "${ROWS[@]}"; do
  IFS='|' read -r rname rage rpath rmine <<< "$row"
  printf '%-10s %-6s %-50s %s\n' "$rname" "$rage" "$rpath" "$rmine"
done
exit 0
