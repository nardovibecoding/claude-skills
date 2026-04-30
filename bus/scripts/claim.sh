#!/bin/bash
# claim.sh — atomic file-path claim for /radio coordination.
# Usage: bash claim.sh <path>
# Env: BUS_FORCE_SID (test override), BUS_NAME (session name for broadcast)
# Output: JSON to stdout. Exit 0 = ok/idempotent. Exit 1 = already_claimed by other.
#
# Claim file: ~/.claude/bus/claims/<sha256> containing JSON record.
# Lock: mkdir-as-lock on ~/.claude/bus/claims.lock (same primitive as registry.lock).

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/_lock_lib.sh"

BUS_CLAIMS_DIR="${BUS_DIR}/claims"
BUS_CLAIMS_LOCK="${BUS_DIR}/claims.lock"

mkdir -p "$BUS_CLAIMS_DIR"

# --- Argument validation ---
if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  jq -cn '{ok:false, reason:"missing_path"}'
  exit 1
fi

RAW_PATH="$1"

# LEGAL path check: reject shell metacharacters (;  &  |  $  ` and newline).
case "$RAW_PATH" in
  *[';''&''|''$''`']* | *$'\n'*)
    jq -cn '{ok:false, reason:"illegal_chars_in_path"}'
    exit 1 ;;
esac

# Resolve to absolute path.
ABS_PATH=$(realpath "$RAW_PATH" 2>/dev/null) || {
  jq -cn --arg p "$RAW_PATH" '{ok:false, reason:"path_resolve_failed", path:$p}'
  exit 1
}

# Compute sha256 of absolute path bytes.
SHA=$(printf '%s' "$ABS_PATH" | shasum -a 256 | awk '{print $1}')
CLAIM_FILE="$BUS_CLAIMS_DIR/$SHA"

# Resolve own session id.
OWN_SID=$(_bus_resolve_sid) || {
  jq -cn '{ok:false, reason:"no_claude_ancestor"}'
  exit 1
}

NAME="${BUS_NAME:-unknown}"
HOST=$(hostname -s 2>/dev/null || echo "unknown")
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# --- Critical section ---
_bus_claims_lock_acquire() {
  local waited=0
  while ! mkdir "$BUS_CLAIMS_LOCK" 2>/dev/null; do
    if [ -d "$BUS_CLAIMS_LOCK" ]; then
      local age now
      age=$(stat -f "%m" "$BUS_CLAIMS_LOCK" 2>/dev/null || stat -c "%Y" "$BUS_CLAIMS_LOCK" 2>/dev/null || echo 0)
      now=$(date +%s)
      if [ $((now - age)) -gt 30 ]; then
        rmdir "$BUS_CLAIMS_LOCK" 2>/dev/null || rm -rf "$BUS_CLAIMS_LOCK" 2>/dev/null
        continue
      fi
    fi
    sleep 0.05
    waited=$((waited + 1))
    [ "$waited" -gt 100 ] && return 1
  done
  return 0
}

_bus_claims_lock_release() {
  rmdir "$BUS_CLAIMS_LOCK" 2>/dev/null || rm -rf "$BUS_CLAIMS_LOCK" 2>/dev/null
}

_bus_claims_lock_acquire || {
  jq -cn '{ok:false, reason:"lock_timeout"}'
  exit 1
}
trap _bus_claims_lock_release EXIT INT TERM

RESULT=""
if [ -f "$CLAIM_FILE" ]; then
  # Parse existing claim.
  EXISTING_SID=$(jq -r '.session_id' "$CLAIM_FILE" 2>/dev/null || echo "")
  EXISTING_NAME=$(jq -r '.name' "$CLAIM_FILE" 2>/dev/null || echo "?")
  EXISTING_TS=$(jq -r '.ts' "$CLAIM_FILE" 2>/dev/null || echo "?")

  if [ -z "$EXISTING_SID" ]; then
    # Corrupted claim file — treat as no claim; overwrite.
    printf '%s' "$(jq -cn \
      --arg p "$ABS_PATH" --arg s "$SHA" --argjson sid "$OWN_SID" \
      --arg n "$NAME" --arg ts "$NOW" --arg h "$HOST" \
      '{path:$p, sha:$s, session_id:$sid, name:$n, ts:$ts, host:$h}')" > "$CLAIM_FILE"
    RESULT="$(jq -cn --arg s "$SHA" --arg p "$ABS_PATH" '{ok:true, sha:$s, path:$p}')"
  elif [ "$EXISTING_SID" = "$OWN_SID" ]; then
    # Idempotent: own claim — refresh ts only.
    jq -c --arg ts "$NOW" '.ts = $ts' "$CLAIM_FILE" > "${CLAIM_FILE}.tmp" && mv "${CLAIM_FILE}.tmp" "$CLAIM_FILE"
    RESULT="$(jq -cn --arg s "$SHA" --arg p "$ABS_PATH" '{ok:true, sha:$s, path:$p, refreshed:true}')"
  else
    # Claimed by another session — check if that session is still alive.
    DEAD=false
    case "$EXISTING_SID" in
      ''|*[!0-9]*) DEAD=true ;;
      *) kill -0 "$EXISTING_SID" 2>/dev/null || DEAD=true ;;
    esac
    if $DEAD; then
      # Auto-expire stale claim; take ownership.
      printf '%s' "$(jq -cn \
        --arg p "$ABS_PATH" --arg s "$SHA" --argjson sid "$OWN_SID" \
        --arg n "$NAME" --arg ts "$NOW" --arg h "$HOST" \
        '{path:$p, sha:$s, session_id:$sid, name:$n, ts:$ts, host:$h}')" > "$CLAIM_FILE"
      RESULT="$(jq -cn --arg s "$SHA" --arg p "$ABS_PATH" '{ok:true, sha:$s, path:$p, note:"expired_prior_claim"}')"
    else
      RESULT="$(jq -cn \
        --arg r "already_claimed" --arg by "$EXISTING_NAME" \
        --arg at "$EXISTING_TS" --argjson sid "$EXISTING_SID" \
        '{ok:false, reason:$r, by:$by, at:$at, sid:$sid}')"
      _bus_claims_lock_release
      trap - EXIT INT TERM
      printf '%s\n' "$RESULT"
      exit 1
    fi
  fi
else
  # New claim.
  printf '%s' "$(jq -cn \
    --arg p "$ABS_PATH" --arg s "$SHA" --argjson sid "$OWN_SID" \
    --arg n "$NAME" --arg ts "$NOW" --arg h "$HOST" \
    '{path:$p, sha:$s, session_id:$sid, name:$n, ts:$ts, host:$h}')" > "$CLAIM_FILE"
  RESULT="$(jq -cn --arg s "$SHA" --arg p "$ABS_PATH" '{ok:true, sha:$s, path:$p}')"
fi

_bus_claims_lock_release
trap - EXIT INT TERM

# Broadcast outside critical section (best-effort). Redirect all output to stderr.
SEND="$SCRIPT_DIR/../plugin/src/cli/send.ts"
if [ -f "$SEND" ]; then
  BUS_NAME="$NAME" bun run "$SEND" all "lock claim $ABS_PATH" >/dev/null 2>&1 || true
fi

printf '%s\n' "$RESULT"
exit 0
