#!/usr/bin/env bash
# test_consensus_e2e.sh -- End-to-end test for consensus.sh protocol.
#
# Spawns 4 fake peer sessions (A/B/C/D) via BUS_FORCE_SID override.
# Initiator (sid 99999, name "Z") runs consensus with BUS_ROUND_TIMEOUT=5.
# 3 of 4 peers vote agree, 1 votes disagree (75% exactly -- CONSENSUS edge).
# Verifies:
#   - Verdict envelope written with payload="CONSENSUS"
#   - Round 1 threshold met -> early exit (final_round=1)
#
# Usage: bash test_consensus_e2e.sh
# Exit: 0 = all assertions pass; 1 = at least one assertion failed.

set -euo pipefail

BUS_HOME="${HOME}/.claude/bus"
WRITER="${HOME}/.claude/skills/bus/plugin/src/writer.js"
SEND="bun run ${HOME}/.claude/skills/bus/plugin/src/cli/send.ts"
CONSENSUS="${HOME}/.claude/skills/bus/scripts/consensus.sh"

# Peer SIDs + names
INITIATOR_SID="99999"
PEER_SIDS=("11111" "22222" "33333" "44444")
PEER_NAMES=("A" "B" "C" "D")

ALL_SIDS=("$INITIATOR_SID" "${PEER_SIDS[@]}")

echo ""
echo "=== consensus e2e test ==="
echo "Initiator: SID=$INITIATOR_SID name=Z"
echo "Peers: A(11111) B(22222) C(33333) D(44444)"
echo "Stance: A=agree B=agree C=agree D=disagree (3/4=75% -> CONSENSUS)"
echo ""

FAIL=0

cleanup() {
  # Remove test inbox files.
  for sid in "${ALL_SIDS[@]}"; do
    rm -f "${BUS_HOME}/inbox/${sid}.jsonl"
  done
  # Remove test entries from all.jsonl (consensus_id prefix filter).
  if [ -f "${BUS_HOME}/all.jsonl" ] && [ -n "${CONSENSUS_ID:-}" ]; then
    local tmpf
    tmpf=$(mktemp)
    jq -c --arg cid "$CONSENSUS_ID" 'select(.consensus_id != $cid)' \
      "${BUS_HOME}/all.jsonl" > "$tmpf" 2>/dev/null && mv "$tmpf" "${BUS_HOME}/all.jsonl" || true
  fi
}
trap 'cleanup' EXIT

mkdir -p "${BUS_HOME}/inbox"
# Clear any stale test inboxes.
for sid in "${ALL_SIDS[@]}"; do
  rm -f "${BUS_HOME}/inbox/${sid}.jsonl"
done

# Step 1: Run initiator consensus.sh with short timeout (5s per round).
# We run it in background and let it block; peers will inject votes into
# the initiator's inbox after a brief delay.
echo "Starting consensus.sh (timeout=5s/round)..."

BUS_HOME="$BUS_HOME" \
BUS_NAME="Z" \
BUS_SID="$INITIATOR_SID" \
BUS_ROUND_TIMEOUT=5 \
bash "$CONSENSUS" "should we deploy?" > /tmp/consensus_e2e_out.txt 2>&1 &
INITIATOR_PID=$!

# Give the initiator a moment to broadcast round 1 question.
sleep 1

# Step 2: Read the question envelope from all.jsonl to extract consensus_id.
echo "Extracting consensus_id from all.jsonl..."

# Wait up to 10s for the question envelope to appear.
CONSENSUS_ID=""
for i in $(seq 1 20); do
  if [ -f "${BUS_HOME}/all.jsonl" ]; then
    CID=$(jq -r 'select(.kind == "question" and .from_session_id == "'"$INITIATOR_SID"'") | .consensus_id' \
      "${BUS_HOME}/all.jsonl" 2>/dev/null | tail -1)
    if [ -n "$CID" ] && [ "$CID" != "null" ]; then
      CONSENSUS_ID="$CID"
      break
    fi
  fi
  sleep 0.5
done

if [ -z "$CONSENSUS_ID" ]; then
  echo "FAIL: consensus_id not found in all.jsonl after 10s" >&2
  FAIL=1
  wait "$INITIATOR_PID" || true
  exit 1
fi
echo "consensus_id = $CONSENSUS_ID"

# Step 3: Peers cast votes directly into initiator's inbox.
# A, B, C vote agree; D votes disagree. (3/4 = 75% -> CONSENSUS)
echo "Peers casting votes..."

_cast_vote() {
  local peer_sid="$1" peer_name="$2" stance="$3" reason="$4"
  local ts msg_id
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  msg_id="${peer_sid}-v1-$(date +%s%N | head -c 13)"

  # Write vote envelope directly to initiator's inbox using appendTargeted.
  BUS_FORCE_SID="$peer_sid" \
  BUS_NAME="$peer_name" \
  bun --eval "
import { appendTargeted } from '$WRITER';
await appendTargeted('${INITIATOR_SID}', {
  msg_id: '${msg_id}',
  from: '${peer_name}',
  from_session_id: '${peer_sid}',
  to: '${INITIATOR_SID}',
  mode: 'consensus',
  ts: '${ts}',
  payload: '${stance}: ${reason}',
  round: 1,
  kind: 'vote',
  consensus_id: '${CONSENSUS_ID}',
});
" 2>&1
}

_cast_vote "11111" "A" "agree"    "looks good to me"
_cast_vote "22222" "B" "agree"    "tests all pass"
_cast_vote "33333" "C" "agree"    "no blockers"
_cast_vote "44444" "D" "disagree" "risk too high"

echo "Votes injected. Waiting for initiator to complete..."

# Wait for initiator to finish (max 30s to handle up to 3 rounds of 5s each + margin).
wait "$INITIATOR_PID" || INITIATOR_EXIT=$?
INITIATOR_EXIT="${INITIATOR_EXIT:-0}"

echo ""
echo "--- Initiator output ---"
cat /tmp/consensus_e2e_out.txt
echo "--- end ---"
echo ""

# Step 4: Parse the machine-readable result (last line of stdout).
RESULT_JSON=$(tail -1 /tmp/consensus_e2e_out.txt)
echo "Result JSON: $RESULT_JSON"

VERDICT=$(echo "$RESULT_JSON" | jq -r '.verdict // "MISSING"' 2>/dev/null || echo "PARSE_ERROR")
FINAL_ROUND=$(echo "$RESULT_JSON" | jq -r '.final_round // -1' 2>/dev/null || echo "-1")

# Step 5: Assertions.
echo ""
echo "=== Assertions ==="

assert_eq() {
  local label="$1" got="$2" want="$3"
  if [ "$got" = "$want" ]; then
    echo "  PASS: $label ($got)"
  else
    echo "  FAIL: $label -- got='$got' want='$want'"
    FAIL=1
  fi
}

# VP3a: verdict = CONSENSUS
assert_eq "verdict=CONSENSUS" "$VERDICT" "CONSENSUS"

# VP3b: early exit in round 1 (3/4 met threshold immediately)
assert_eq "final_round=1 (early exit)" "$FINAL_ROUND" "1"

# VP3c: verdict envelope written to all.jsonl
VERDICT_IN_ALL=$(jq -r --arg cid "$CONSENSUS_ID" \
  'select(.consensus_id == $cid and .kind == "verdict") | .payload' \
  "${BUS_HOME}/all.jsonl" 2>/dev/null | tail -1)
assert_eq "verdict envelope in all.jsonl" "$VERDICT_IN_ALL" "CONSENSUS"

# VP3d: initiator exit code was 0
assert_eq "initiator exit code" "$INITIATOR_EXIT" "0"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "=== ALL ASSERTIONS PASS ==="
  exit 0
else
  echo "=== SOME ASSERTIONS FAILED ==="
  exit 1
fi
