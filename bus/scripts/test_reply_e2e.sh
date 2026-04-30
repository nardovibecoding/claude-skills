#!/usr/bin/env bash
# test_reply_e2e.sh — end-to-end reply-path driver for S6.
#
# Simulates two sessions:
#   A (BUS_FORCE_SID=11111) sends tell B "ping" → mode=notify
#   B (BUS_FORCE_SID=22222) sends reply A <msg_id> "pong" → mode=reply into A's inbox
#
# Verifies:
#   1. A's inbox has the reply envelope with mode=reply, reply_from=B
#   2. envelope.in_reply_to matches A's original msg_id
#
# On success: exits 0 and prints "E2E PASS"
# On failure: exits 1 and prints the failing check

set -euo pipefail

SEND="bun run /Users/bernard/.claude/skills/bus/plugin/src/cli/send.ts"
RESOLVE="bash /Users/bernard/.claude/skills/bus/scripts/resolve_name.sh"
JOIN="bash /Users/bernard/.claude/skills/bus/scripts/join.sh"

# ── Temp state ────────────────────────────────────────────────────────────────
BUS_DIR=$(mktemp -d)/bus
mkdir -p "$BUS_DIR/inbox" "$BUS_DIR/opted-in"
export BUS_DIR HOME="$(mktemp -d)"
mkdir -p "$HOME/.claude"
ln -sf "$BUS_DIR" "$HOME/.claude/bus"

cleanup() {
  rm -rf "${BUS_DIR%/bus}" "$HOME"
}
trap cleanup EXIT INT TERM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Step 1: A joins as "A", B joins as "B" ───────────────────────────────────
RESP_A=$(BUS_FORCE_SID=11111 bash "$SCRIPT_DIR/join.sh" 2>/dev/null)
NAME_A=$(echo "$RESP_A" | jq -r '.name')
SID_A=$(echo "$RESP_A" | jq -r '.session_id')
if [ "$NAME_A" = "null" ] || [ -z "$NAME_A" ]; then
  echo "FAIL: A join failed: $RESP_A"
  exit 1
fi

RESP_B=$(BUS_FORCE_SID=22222 bash "$SCRIPT_DIR/join.sh" 2>/dev/null)
NAME_B=$(echo "$RESP_B" | jq -r '.name')
SID_B=$(echo "$RESP_B" | jq -r '.session_id')
if [ "$NAME_B" = "null" ] || [ -z "$NAME_B" ]; then
  echo "FAIL: B join failed: $RESP_B"
  exit 1
fi

echo "Joined: $NAME_A=$SID_A  $NAME_B=$SID_B"

# ── Step 2: A sends tell B "ping" → mode=notify into B's inbox ───────────────
TARGET_B_SID=$(BUS_DIR="$BUS_DIR" $RESOLVE "$NAME_B" 2>/dev/null) || {
  echo "FAIL: resolve $NAME_B failed"
  exit 1
}

TELL_OUT=$(HOME="$HOME" BUS_NAME="$NAME_A" BUS_TARGET_SID="$TARGET_B_SID" \
  $SEND tell "$NAME_B" "ping" 2>/dev/null)
ORIG_MSG_ID=$(echo "$TELL_OUT" | jq -r '.msg_id')
if [ -z "$ORIG_MSG_ID" ] || [ "$ORIG_MSG_ID" = "null" ]; then
  echo "FAIL: tell did not return msg_id: $TELL_OUT"
  exit 1
fi
echo "A sent tell to B: msg_id=$ORIG_MSG_ID"

# ── Step 3: B sends reply A <msg_id> "pong" ──────────────────────────────────
REPLY_OUT=$(HOME="$HOME" BUS_NAME="$NAME_B" BUS_DIR="$BUS_DIR" \
  $SEND reply "$NAME_A" "$ORIG_MSG_ID" "pong" 2>/dev/null)
REPLY_MSG_ID=$(echo "$REPLY_OUT" | jq -r '.msg_id')
if [ -z "$REPLY_MSG_ID" ] || [ "$REPLY_MSG_ID" = "null" ]; then
  echo "FAIL: reply did not return msg_id: $REPLY_OUT"
  exit 1
fi
echo "B sent reply to A: reply_msg_id=$REPLY_MSG_ID in_reply_to=$ORIG_MSG_ID"

# ── Step 4: Verify A's inbox ─────────────────────────────────────────────────
A_INBOX="$BUS_DIR/inbox/${SID_A}.jsonl"
if [ ! -f "$A_INBOX" ]; then
  echo "FAIL: A's inbox does not exist: $A_INBOX"
  exit 1
fi

ENVELOPE=$(tail -1 "$A_INBOX")
echo "A inbox last envelope: $ENVELOPE"

check() {
  local FIELD="$1" EXPECTED="$2"
  local GOT
  GOT=$(echo "$ENVELOPE" | jq -r ".$FIELD")
  if [ "$GOT" != "$EXPECTED" ]; then
    echo "FAIL: envelope.$FIELD expected='$EXPECTED' got='$GOT'"
    exit 1
  fi
}

check "mode"        "reply"
check "reply_from"  "$NAME_B"
check "in_reply_to" "$ORIG_MSG_ID"
check "from"        "$NAME_B"
check "payload"     "pong"

echo ""
echo "E2E PASS: reply envelope in A's inbox verified"
echo "  mode=reply, reply_from=$NAME_B, in_reply_to=$ORIG_MSG_ID"
exit 0
