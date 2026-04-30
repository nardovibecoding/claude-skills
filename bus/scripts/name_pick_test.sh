#!/bin/bash
# name_pick_test.sh — race test for join.sh.
# Spawns N parallel joins (default 5) with distinct BUS_FORCE_SID values;
# verifies all N picked DISTINCT names; cleans up.
# Exit 0 = pass; 1 = collision detected.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
N="${RACE_N:-5}"
TMP_OUT=$(mktemp -d)
trap 'rm -rf "$TMP_OUT"' EXIT

# Sandbox to a temp BUS_DIR so we don't pollute real registry/sentinels.
export BUS_DIR="$TMP_OUT/bus"
mkdir -p "$BUS_DIR/opted-in" "$BUS_DIR/plugin-pid"

echo "[race-test] N=$N, sandbox BUS_DIR=$BUS_DIR"

# Launch N joins in parallel; each gets a unique fake SID 90000+i.
i=1
while [ "$i" -le "$N" ]; do
  ( BUS_FORCE_SID=$((90000 + i)) BUS_DIR="$BUS_DIR" \
      bash "$SCRIPT_DIR/join.sh" > "$TMP_OUT/out.$i" 2>&1 ) &
  i=$((i + 1))
done
wait

# Collect names.
NAMES=$(cat "$TMP_OUT"/out.* | jq -r 'select(.ok==true) | .name' 2>/dev/null | sort)
COUNT=$(echo "$NAMES" | grep -c .)
DISTINCT=$(echo "$NAMES" | sort -u | grep -c .)
REG_COUNT=$(wc -l < "$BUS_DIR/registry.jsonl" 2>/dev/null | tr -d ' ')

echo "[race-test] outputs:"
for f in "$TMP_OUT"/out.*; do
  echo "  $(basename "$f"): $(cat "$f")"
done
echo "[race-test] names_picked: $(echo "$NAMES" | tr '\n' ',' | sed 's/,$//')"
echo "[race-test] count=$COUNT distinct=$DISTINCT registry_lines=$REG_COUNT expected=$N"

if [ "$COUNT" -eq "$N" ] && [ "$DISTINCT" -eq "$N" ] && [ "$REG_COUNT" -eq "$N" ]; then
  echo "[race-test] PASS — all $N joins got distinct names"
  exit 0
else
  echo "[race-test] FAIL — collision or missing entries"
  exit 1
fi
