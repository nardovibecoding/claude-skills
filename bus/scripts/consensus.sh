#!/usr/bin/env bash
# consensus.sh — initiator script for 3-round /radio consensus protocol.
#
# Usage: bash consensus.sh "<question>"
#
# Required env:
#   BUS_NAME       - sender bus letter, e.g. "A"
#   BUS_SID        - initiator session_id (numeric PID of claude ancestor)
#
# Optional env:
#   BUS_ROUND_TIMEOUT - seconds per round (default: 60)
#   BUS_HOME          - override bus root dir (default: ~/.claude/bus)
#
# Output:
#   Human-readable table on stdout.
#   Final JSON result on stdout: {"ok":true,"verdict":"CONSENSUS|NO-CONSENSUS","final_round":N,"agree":M,"total":T}
#
# Exit codes: 0 = ran to completion (check verdict in JSON); 1 = usage/env error.
#
# Consensus contract (v1 preserved):
#   - Hard cap: 3 rounds
#   - Per round: each peer responds at-most-once (jq dedup on round+from)
#   - Per-round timeout: BUS_ROUND_TIMEOUT (default 60s)
#   - Threshold: agree*100/total >= 75 (integer math; 3/4=75 PASSES, 2/3=66 FAILS)
#   - Early exit: if threshold met before round 3, emit verdict and stop
#   - Zero peers: no consensus, advance to next round
#
# Envelope types emitted:
#   kind=question : broadcast to all.jsonl each round
#   kind=vote     : received from peers in initiator's inbox
#   kind=verdict  : broadcast to all.jsonl after final decision

set -euo pipefail

QUESTION="${1:-}"
if [ -z "$QUESTION" ]; then
  echo "[consensus] usage: consensus.sh \"<question>\"" >&2
  exit 1
fi

BUS_NAME="${BUS_NAME:-}"
BUS_SID="${BUS_SID:-}"
if [ -z "$BUS_NAME" ] || [ -z "$BUS_SID" ]; then
  echo "[consensus] BUS_NAME and BUS_SID env required" >&2
  exit 1
fi

ROUND_TIMEOUT="${BUS_ROUND_TIMEOUT:-60}"
BUS_HOME="${BUS_HOME:-${HOME}/.claude/bus}"
INBOX="${BUS_HOME}/inbox/${BUS_SID}.jsonl"
SEND="bun run ${HOME}/.claude/skills/bus/plugin/src/cli/send.ts"

# consensus_id format: <sid>-c-<epoch>
CONSENSUS_ID="${BUS_SID}-c-$(date +%s)"

# Emit NO-CONSENSUS verdict on unexpected exit (trap).
_emit_no_consensus_on_exit() {
  local code=$?
  if [ "$code" -ne 0 ]; then
    BUS_NAME="$BUS_NAME" $SEND consensus "{}" 2>/dev/null || true
    BUS_NAME="$BUS_NAME" $SEND all \
      "{\"mode\":\"consensus\",\"kind\":\"verdict\",\"consensus_id\":\"${CONSENSUS_ID}\",\"payload\":\"NO-CONSENSUS (initiator crashed)\"}" \
      2>/dev/null || true
  fi
}
trap '_emit_no_consensus_on_exit' EXIT INT TERM

echo ""
echo "=== /radio consensus ==="
echo "Question : $QUESTION"
echo "ID       : $CONSENSUS_ID"
echo "Timeout  : ${ROUND_TIMEOUT}s per round"
echo "Threshold: 75%"
echo ""

FINAL_VERDICT="NO-CONSENSUS"
FINAL_ROUND=0
FINAL_AGREE=0
FINAL_TOTAL=0

# Helper: broadcast a question envelope for round R.
_broadcast_question() {
  local round="$1"
  # Build the JSON payload — question text carried in payload field.
  # consensus fields (round/kind/consensus_id) are passed via env so send.ts
  # can attach them. However send.ts consensus verb builds a plain envelope.
  # We use the raw write path: build a full JSON line and append directly
  # via send.ts to all.jsonl, with consensus fields.
  #
  # Since send.ts consensus verb does not yet accept --round/--kind/--consensus-id
  # flags, we construct a targeted bun call to writer.ts directly via a
  # small inline script. This keeps Sh1 (single writer path) intact.
  BUS_FORCE_FROM="$BUS_NAME" \
  BUS_NAME="$BUS_NAME" \
  BUN_ENV_CONSENSUS_ID="$CONSENSUS_ID" \
  BUN_ENV_ROUND="$round" \
  bun run - << 'BUNSCRIPT'
    import { appendBroadcast } from process.env.HOME + "/.claude/skills/bus/plugin/src/writer.js";
BUNSCRIPT
  # Simpler: use jq to build the line and append directly.
  # writer.ts appendBroadcast is the single writer; we call it via a tiny
  # inline bun script to avoid duplicating append logic.
  local ts msg_id payload_json
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  msg_id="${BUS_SID}-q${round}-$(date +%s%N | head -c 16)"
  payload_json=$(printf '%s' "$QUESTION" | jq -Rs .)

  # Inline bun: directly call appendBroadcast from writer.ts.
  BUS_NAME="$BUS_NAME" bun run --eval "
import { appendBroadcast } from '${HOME}/.claude/skills/bus/plugin/src/writer.js';
await appendBroadcast({
  msg_id: '${msg_id}',
  from: '${BUS_NAME}',
  from_session_id: '${BUS_SID}',
  to: 'all',
  mode: 'consensus',
  ts: '${ts}',
  payload: ${payload_json},
  round: ${round},
  kind: 'question',
  consensus_id: '${CONSENSUS_ID}',
});
" 2>&1
}

# Helper: collect votes from inbox for a given round within timeout.
# Writes deduplicated (round,from) votes to stdout as JSON lines.
_collect_votes() {
  local round="$1"
  local deadline
  deadline=$(( $(date +%s) + ROUND_TIMEOUT ))

  local seen_file
  seen_file=$(mktemp /tmp/bus-consensus-seen.XXXXXX)
  local votes_file
  votes_file=$(mktemp /tmp/bus-consensus-votes.XXXXXX)

  # Touch inbox in case it doesn't exist yet.
  mkdir -p "$(dirname "$INBOX")"
  touch "$INBOX"

  while [ "$(date +%s)" -lt "$deadline" ]; do
    # Read inbox: filter kind=vote + matching consensus_id + matching round.
    # Dedup by (round, from): keep first occurrence per from per round.
    if [ -s "$INBOX" ]; then
      jq -c --arg cid "$CONSENSUS_ID" --argjson r "$round" \
        'select(.consensus_id == $cid and .kind == "vote" and .round == $r)' \
        "$INBOX" 2>/dev/null | while IFS= read -r line; do
          from=$(printf '%s' "$line" | jq -r '.from')
          key="${round}:${from}"
          if ! grep -qxF "$key" "$seen_file" 2>/dev/null; then
            echo "$key" >> "$seen_file"
            echo "$line" >> "$votes_file"
          fi
      done
    fi
    sleep 2
  done

  cat "$votes_file"
  rm -f "$seen_file" "$votes_file"
}

# Helper: tally votes. Prints "agree=N total=M".
_tally() {
  local votes_json="$1"
  local agree=0 total=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    total=$(( total + 1 ))
    stance=$(printf '%s' "$line" | jq -r '.payload' | cut -d: -f1 | tr -d ' ')
    if [ "$stance" = "agree" ]; then
      agree=$(( agree + 1 ))
    fi
  done <<< "$votes_json"
  echo "agree=$agree total=$total"
}

# Helper: check 75% threshold. Returns 0 (true) if met.
_threshold_met() {
  local agree="$1" total="$2"
  if [ "$total" -eq 0 ]; then return 1; fi
  # Integer math: agree*100/total >= 75
  local pct=$(( agree * 100 / total ))
  [ "$pct" -ge 75 ]
}

# --- Main loop: 3 rounds ---
for ROUND in 1 2 3; do
  echo "--- Round ${ROUND} ---"

  # Broadcast question.
  echo "Broadcasting question to all peers..."
  _broadcast_question "$ROUND"
  echo "Waiting ${ROUND_TIMEOUT}s for votes..."

  # Collect votes (blocks for ROUND_TIMEOUT seconds).
  VOTES=$(_collect_votes "$ROUND")
  TALLY=$(_tally "$VOTES")

  AGREE=$(echo "$TALLY" | grep -o 'agree=[0-9]*' | cut -d= -f2)
  TOTAL=$(echo "$TALLY" | grep -o 'total=[0-9]*' | cut -d= -f2)

  echo "  Round ${ROUND} results: agree=${AGREE} / total=${TOTAL}"

  # Display per-vote breakdown.
  if [ -n "$VOTES" ]; then
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      from=$(printf '%s' "$line" | jq -r '.from')
      payload=$(printf '%s' "$line" | jq -r '.payload')
      echo "    ${from}: ${payload}"
    done <<< "$VOTES"
  else
    echo "    (no votes received)"
  fi

  FINAL_ROUND="$ROUND"
  FINAL_AGREE="$AGREE"
  FINAL_TOTAL="$TOTAL"

  # Check threshold.
  if _threshold_met "$AGREE" "$TOTAL"; then
    FINAL_VERDICT="CONSENSUS"
    echo ""
    echo ">>> CONSENSUS reached in round ${ROUND} (${AGREE}/${TOTAL} = $(( AGREE * 100 / TOTAL ))% >= 75%)"
    break
  else
    if [ "$ROUND" -lt 3 ]; then
      echo "  Threshold not met ($(( AGREE * 100 / ( TOTAL > 0 ? TOTAL : 1 ) ))% < 75%); advancing to round $(( ROUND + 1 ))."
    fi
  fi
done

if [ "$FINAL_VERDICT" = "NO-CONSENSUS" ]; then
  echo ""
  echo ">>> NO-CONSENSUS after ${FINAL_ROUND} round(s) (${FINAL_AGREE}/${FINAL_TOTAL})"
fi

# Broadcast verdict envelope.
echo ""
echo "Broadcasting verdict..."
VERDICT_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERDICT_MSG_ID="${BUS_SID}-v-$(date +%s)"

BUS_NAME="$BUS_NAME" bun run --eval "
import { appendBroadcast } from '${HOME}/.claude/skills/bus/plugin/src/writer.js';
await appendBroadcast({
  msg_id: '${VERDICT_MSG_ID}',
  from: '${BUS_NAME}',
  from_session_id: '${BUS_SID}',
  to: 'all',
  mode: 'consensus',
  ts: '${VERDICT_TS}',
  payload: '${FINAL_VERDICT}',
  round: 0,
  kind: 'verdict',
  consensus_id: '${CONSENSUS_ID}',
});
" 2>&1

echo ""
echo "=== Summary ==="
printf "%-15s %s\n" "Verdict:"     "$FINAL_VERDICT"
printf "%-15s %s\n" "Final round:" "$FINAL_ROUND"
printf "%-15s %s\n" "Agree:"       "${FINAL_AGREE}/${FINAL_TOTAL}"
echo ""

# Disarm exit trap (clean exit).
trap - EXIT INT TERM

# Emit machine-readable result.
printf '{"ok":true,"verdict":"%s","final_round":%d,"agree":%d,"total":%d}\n' \
  "$FINAL_VERDICT" "$FINAL_ROUND" "$FINAL_AGREE" "$FINAL_TOTAL"
