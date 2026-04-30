#!/bin/bash
# test_claim_e2e.sh — end-to-end claim/release/collision + hook block test.
# Simulates two sessions (SID 11111 and 22222) and verifies:
#   1. Session A claims a path → ok
#   2. Session B tries same path → already_claimed
#   3. hook radio_claim_guard.py blocks Write for session B → exit 0 with block JSON
#   4. Session A releases → claim file gone
#   5. Session B now claims → succeeds
#
# Uses BUS_FORCE_SID + temp BUS_DIR for isolation.
# Exits 0 on all-pass, 1 on first failure.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$HOME/.claude/hooks/radio_claim_guard.py"
TMP_DIR=$(mktemp -d /tmp/bus-e2e-claim.XXXXXX)
CANARY="$TMP_DIR/canary.txt"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

touch "$CANARY"
mkdir -p "$TMP_DIR/claims"

echo "[e2e] Using TMP_DIR=$TMP_DIR"
echo "[e2e] CANARY=$CANARY"

pass() { printf '[PASS] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; exit 1; }

# ---------------------------------------------------------------------------
# Step 1: Session A (SID=11111) claims canary.
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 1: Session A claims $CANARY ==="
RESP_A=$(BUS_DIR="$TMP_DIR" BUS_FORCE_SID=11111 BUS_NAME=A \
  bash "$SCRIPT_DIR/claim.sh" "$CANARY" 2>/dev/null)
echo "$RESP_A"

OK_A=$(printf '%s' "$RESP_A" | jq -r '.ok')
[ "$OK_A" = "true" ] || fail "Step 1: claim should return ok:true (got: $RESP_A)"
pass "Session A claimed $CANARY"

SHA=$(printf '%s' "$RESP_A" | jq -r '.sha')
CLAIM_FILE="$TMP_DIR/claims/$SHA"
[ -f "$CLAIM_FILE" ] || fail "Step 1: claim file $CLAIM_FILE not created"
pass "Claim file exists at claims/$SHA"

# Patch session_id to a real alive PID so Session B sees it as live.
jq -c --argjson pid $$ '.session_id = $pid' "$CLAIM_FILE" > "${CLAIM_FILE}.tmp" \
  && mv "${CLAIM_FILE}.tmp" "$CLAIM_FILE"
echo "[e2e] Patched session_id to $$ (our PID, alive)"

# ---------------------------------------------------------------------------
# Step 2: Session B (SID=22222) tries to claim same path → must fail.
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 2: Session B tries to claim $CANARY ==="
RESP_B=$(BUS_DIR="$TMP_DIR" BUS_FORCE_SID=22222 BUS_NAME=B \
  bash "$SCRIPT_DIR/claim.sh" "$CANARY" 2>/dev/null) || RESP_B="$RESP_B"
echo "$RESP_B"

OK_B=$(printf '%s' "$RESP_B" | jq -r '.ok')
[ "$OK_B" = "false" ] || fail "Step 2: claim should return ok:false for collision (got: $RESP_B)"
REASON=$(printf '%s' "$RESP_B" | jq -r '.reason')
[ "$REASON" = "already_claimed" ] || fail "Step 2: reason should be already_claimed (got: $REASON)"
pass "Session B correctly blocked with already_claimed"

# ---------------------------------------------------------------------------
# Step 3: Simulate hook check for Session B trying to Write canary.
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 3: Hook radio_claim_guard.py blocks Write for session B ==="
HOOK_INPUT=$(jq -cn --arg p "$CANARY" '{"tool_name":"Write","tool_input":{"file_path":$p}}')
echo "Hook input: $HOOK_INPUT"

HOOK_OUT=$(printf '%s' "$HOOK_INPUT" | \
  BUS_DIR="$TMP_DIR" BUS_FORCE_SID=22222 \
  python3 "$HOOK" 2>/tmp/hook_e2e_stderr.txt)
HOOK_EXIT=$?

cat /tmp/hook_e2e_stderr.txt >&2 || true
echo "Hook stdout: $HOOK_OUT"
echo "Hook exit: $HOOK_EXIT"

# Hook should exit 0 AND emit a block decision JSON.
[ "$HOOK_EXIT" -eq 0 ] || fail "Step 3: hook must exit 0 (got $HOOK_EXIT)"
DECISION=$(printf '%s' "$HOOK_OUT" | jq -r '.decision' 2>/dev/null || echo "")
[ "$DECISION" = "block" ] || fail "Step 3: hook decision should be 'block' (got: $HOOK_OUT)"
pass "Hook emitted block decision for session B"

# ---------------------------------------------------------------------------
# Step 4: Session A releases.
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 4: Session A releases $CANARY ==="
# Restore correct session_id for release check.
jq -c '.session_id = 11111' "$CLAIM_FILE" > "${CLAIM_FILE}.tmp" \
  && mv "${CLAIM_FILE}.tmp" "$CLAIM_FILE"

RESP_R=$(BUS_DIR="$TMP_DIR" BUS_FORCE_SID=11111 BUS_NAME=A \
  bash "$SCRIPT_DIR/release.sh" "$CANARY" 2>/dev/null)
echo "$RESP_R"

OK_R=$(printf '%s' "$RESP_R" | jq -r '.ok')
[ "$OK_R" = "true" ] || fail "Step 4: release should return ok:true (got: $RESP_R)"
[ ! -f "$CLAIM_FILE" ] || fail "Step 4: claim file should be gone after release"
pass "Session A released; claim file removed"

# ---------------------------------------------------------------------------
# Step 5: Session B now claims → must succeed.
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 5: Session B claims (after release) ==="
RESP_B2=$(BUS_DIR="$TMP_DIR" BUS_FORCE_SID=22222 BUS_NAME=B \
  bash "$SCRIPT_DIR/claim.sh" "$CANARY" 2>/dev/null)
echo "$RESP_B2"

OK_B2=$(printf '%s' "$RESP_B2" | jq -r '.ok')
[ "$OK_B2" = "true" ] || fail "Step 5: Session B should claim after release (got: $RESP_B2)"
pass "Session B claimed after release"

echo ""
echo "=== ALL e2e steps PASSED ==="
exit 0
