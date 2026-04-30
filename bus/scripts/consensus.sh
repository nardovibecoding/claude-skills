#!/usr/bin/env bash
# consensus.sh -- initiator script for 3-round /radio consensus protocol.
#
# Usage: bash consensus.sh "<question>"
#
# Required env:
#   BUS_NAME   - sender bus letter, e.g. "A"
#   BUS_SID    - initiator session_id (numeric PID of claude ancestor)
#
# Optional env:
#   BUS_ROUND_TIMEOUT - seconds per round (default: 60)
#   BUS_HOME          - override bus root dir (default: ~/.claude/bus)
#
# Stdout:
#   Human-readable table, then final JSON:
#   {"ok":true,"verdict":"CONSENSUS|NO-CONSENSUS","final_round":N,"agree":M,"total":T}
#
# Exit codes: 0 = ran to completion (check verdict in JSON); 1 = usage/env error.
#
# Consensus contract (ported from v1 SKILL.md.v1-backup:155-178):
#   - Hard cap: 3 rounds
#   - Per round: each peer responds at-most-once (jq dedup on round+from)
#   - Per-round timeout: BUS_ROUND_TIMEOUT (default 60s)
#   - Threshold: agree*100/total >= 75  (3/4=75 PASSES, 2/3=66 FAILS, 0/N=NO)
#   - Early exit: threshold met before round 3 -> emit verdict, stop
#   - Zero peers: no consensus, advance to next round
#
# Envelope types emitted:
#   kind=question : broadcast to all.jsonl each round
#   kind=vote     : received from peers in initiator's inbox (not emitted here)
#   kind=verdict  : broadcast to all.jsonl after final decision
#   round=0 on verdict (not part of 1-3 consensus rounds)

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
WRITER="${HOME}/.claude/skills/bus/plugin/src/writer.js"

# consensus_id format: <sid>-c-<epoch>
CONSENSUS_ID="${BUS_SID}-c-$(date +%s)"

# Verdict state (written by main loop, read by exit trap).
TRAP_FIRED=0

# Emit NO-CONSENSUS verdict on unexpected exit or signal.
_on_trap() {
  if [ "$TRAP_FIRED" -eq 0 ]; then
    TRAP_FIRED=1
    local vts msg_id
    vts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    msg_id="${BUS_SID}-trap-$(date +%s)"
    BUS_NAME="$BUS_NAME" bun --eval "
import { appendBroadcast } from '$WRITER';
await appendBroadcast({
  msg_id: '$msg_id',
  from: '$BUS_NAME',
  from_session_id: '$BUS_SID',
  to: 'all',
  mode: 'consensus',
  ts: '$vts',
  payload: 'NO-CONSENSUS',
  round: 0,
  kind: 'verdict',
  consensus_id: '$CONSENSUS_ID',
});
" 2>/dev/null || true
  fi
}
trap '_on_trap' EXIT INT TERM

echo ""
echo "=== /radio consensus ==="
echo "Question : $QUESTION"
echo "ID       : $CONSENSUS_ID"
echo "Timeout  : ${ROUND_TIMEOUT}s per round"
echo "Threshold: 75%"
echo ""

# Helper: broadcast a question envelope for round R via writer.ts.
# Uses bun --eval to call appendBroadcast directly (Sh1: single writer path).
_broadcast_question() {
  local round="$1"
  local ts msg_id payload_escaped
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  msg_id="${BUS_SID}-q${round}-$(date +%s)"
  # Escape double-quotes in question for embedding in JS string.
  payload_escaped="${QUESTION//\"/\\\"}"

  BUS_NAME="$BUS_NAME" bun --eval "
import { appendBroadcast } from '$WRITER';
await appendBroadcast({
  msg_id: '${msg_id}',
  from: '${BUS_NAME}',
  from_session_id: '${BUS_SID}',
  to: 'all',
  mode: 'consensus',
  ts: '${ts}',
  payload: \"${payload_escaped}\",
  round: ${round},
  kind: 'question',
  consensus_id: '${CONSENSUS_ID}',
});
process.stdout.write(JSON.stringify({ok:true,msg_id:'${msg_id}'})+'\n');
" 2>&1
}

# Helper: collect votes from inbox for round R within timeout.
# Returns newline-separated JSON lines (deduplicated by from).
_collect_votes() {
  local round="$1"
  local deadline seen_file votes_file
  deadline=$(( $(date +%s) + ROUND_TIMEOUT ))
  seen_file=$(mktemp /tmp/bus-consensus-seen.XXXXXX)
  votes_file=$(mktemp /tmp/bus-consensus-votes.XXXXXX)

  mkdir -p "$(dirname "$INBOX")"
  touch "$INBOX"

  # Poll inbox every 2s until deadline.
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if [ -s "$INBOX" ]; then
      # Filter: consensus_id match + kind=vote + round match.
      jq -c --arg cid "$CONSENSUS_ID" --argjson r "$round" \
        'select(.consensus_id == $cid and .kind == "vote" and .round == $r)' \
        "$INBOX" 2>/dev/null | while IFS= read -r line; do
          from=$(printf '%s' "$line" | jq -r '.from // empty' 2>/dev/null)
          [ -z "$from" ] && continue
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

# Helper: tally a block of vote JSON lines.
# Prints "agree=N total=M" to stdout.
_tally() {
  local votes_text="$1"
  local agree=0 total=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    total=$(( total + 1 ))
    # payload format: "agree: reason" or "disagree: reason"
    stance=$(printf '%s' "$line" | jq -r '.payload // ""' | cut -d: -f1 | tr -d ' ')
    if [ "$stance" = "agree" ]; then
      agree=$(( agree + 1 ))
    fi
  done <<< "$votes_text"
  echo "agree=$agree total=$total"
}

# Helper: check 75% threshold (integer math).
# Returns 0 (true) if met, 1 (false) otherwise.
_threshold_met() {
  local agree="$1" total="$2"
  if [ "$total" -eq 0 ]; then return 1; fi
  local pct=$(( agree * 100 / total ))
  [ "$pct" -ge 75 ]
}

# --- Main 3-round loop ---
FINAL_VERDICT="NO-CONSENSUS"
FINAL_ROUND=0
FINAL_AGREE=0
FINAL_TOTAL=0

for ROUND in 1 2 3; do
  echo "--- Round ${ROUND} ---"
  echo "Broadcasting question..."
  _broadcast_question "$ROUND"
  echo "Waiting ${ROUND_TIMEOUT}s for peer votes..."

  VOTES=$(_collect_votes "$ROUND")
  TALLY=$(_tally "$VOTES")

  AGREE=$(echo "$TALLY" | grep -o 'agree=[0-9]*' | cut -d= -f2)
  TOTAL=$(echo "$TALLY" | grep -o 'total=[0-9]*' | cut -d= -f2)

  FINAL_ROUND="$ROUND"
  FINAL_AGREE="$AGREE"
  FINAL_TOTAL="$TOTAL"

  echo "  Results: agree=${AGREE} / total=${TOTAL}"

  if [ -n "$VOTES" ]; then
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      from=$(printf '%s' "$line" | jq -r '.from // "?"')
      payload=$(printf '%s' "$line" | jq -r '.payload // "?"')
      echo "    ${from}: ${payload}"
    done <<< "$VOTES"
  else
    echo "    (no votes received)"
  fi

  if _threshold_met "$AGREE" "$TOTAL"; then
    FINAL_VERDICT="CONSENSUS"
    echo ""
    echo ">>> CONSENSUS in round ${ROUND}: ${AGREE}/${TOTAL} = $(( AGREE * 100 / TOTAL ))% >= 75%"
    break
  else
    local_pct=0
    if [ "$TOTAL" -gt 0 ]; then
      local_pct=$(( AGREE * 100 / TOTAL ))
    fi
    echo "  Threshold not met (${local_pct}% < 75%)"
    if [ "$ROUND" -lt 3 ]; then
      echo "  Advancing to round $(( ROUND + 1 ))..."
    fi
  fi
done

if [ "$FINAL_VERDICT" = "NO-CONSENSUS" ]; then
  echo ""
  echo ">>> NO-CONSENSUS after ${FINAL_ROUND} round(s): ${FINAL_AGREE}/${FINAL_TOTAL}"
fi

# Broadcast verdict envelope.
echo ""
echo "Broadcasting verdict..."
VERDICT_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VERDICT_MSG_ID="${BUS_SID}-v-$(date +%s)"

BUS_NAME="$BUS_NAME" bun --eval "
import { appendBroadcast } from '$WRITER';
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
process.stdout.write(JSON.stringify({ok:true,msg_id:'${VERDICT_MSG_ID}'})+'\n');
" 2>&1

echo ""
echo "=== Consensus Summary ==="
printf "%-15s %s\n" "Verdict:"     "$FINAL_VERDICT"
printf "%-15s %s\n" "Final round:" "$FINAL_ROUND"
printf "%-15s %s\n" "Agree:"       "${FINAL_AGREE}/${FINAL_TOTAL}"
echo ""

# Disarm trap (clean exit).
TRAP_FIRED=1
trap - EXIT INT TERM

# Machine-readable result (last line of stdout).
printf '{"ok":true,"verdict":"%s","final_round":%d,"agree":%d,"total":%d}\n' \
  "$FINAL_VERDICT" "$FINAL_ROUND" "$FINAL_AGREE" "$FINAL_TOTAL"
