#!/bin/bash
# release.sh — atomic release of /radio file-path claims.
# Usage: bash release.sh <path>
#        bash release.sh --all              (release all own claims)
#        bash release.sh --all --force      (release ALL claims, including others — emergency)
# Env: BUS_FORCE_SID (test override), BUS_NAME (for broadcast)
# Output: JSON to stdout. Exit 0 always (no-op if claim not found).

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/_lock_lib.sh"

BUS_CLAIMS_DIR="${BUS_DIR}/claims"
BUS_CLAIMS_LOCK="${BUS_DIR}/claims.lock"

mkdir -p "$BUS_CLAIMS_DIR"

OWN_SID=$(_bus_resolve_sid) || {
  jq -cn '{ok:false, reason:"no_claude_ancestor"}'
  exit 1
}
NAME="${BUS_NAME:-unknown}"

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

ALL_FLAG=false
FORCE_FLAG=false
TARGET_PATH=""

for arg in "$@"; do
  case "$arg" in
    --all) ALL_FLAG=true ;;
    --force) FORCE_FLAG=true ;;
    *) TARGET_PATH="$arg" ;;
  esac
done

RELEASED=()
SEND="$SCRIPT_DIR/../plugin/src/cli/send.ts"

if $ALL_FLAG; then
  _bus_claims_lock_acquire || { jq -cn '{ok:false, reason:"lock_timeout"}'; exit 1; }
  trap _bus_claims_lock_release EXIT INT TERM

  for claim_file in "$BUS_CLAIMS_DIR"/*; do
    [ -f "$claim_file" ] || continue
    CLAIM_SID=$(jq -r '.session_id' "$claim_file" 2>/dev/null || echo "")
    CLAIM_PATH=$(jq -r '.path' "$claim_file" 2>/dev/null || echo "")
    if [ "$CLAIM_SID" = "$OWN_SID" ] || $FORCE_FLAG; then
      rm -f "$claim_file"
      RELEASED+=("$CLAIM_PATH")
    fi
  done

  _bus_claims_lock_release
  trap - EXIT INT TERM

  # Broadcast each release (best-effort).
  for p in "${RELEASED[@]:-}"; do
    [ -n "$p" ] || continue
    if [ -f "$SEND" ]; then
      BUS_NAME="$NAME" bun run "$SEND" all "unlock release $p" 2>/dev/null || true
    fi
  done

  jq -cn --argjson released "$(printf '%s\n' "${RELEASED[@]:-}" | jq -R . | jq -s .)" \
    '{ok:true, released:$released}'
  exit 0
fi

# Single path release.
if [ -z "$TARGET_PATH" ]; then
  jq -cn '{ok:false, reason:"missing_path_or_flag"}'
  exit 1
fi

case "$TARGET_PATH" in
  *[';''&''|''$''`']* | *$'\n'*)
    jq -cn '{ok:false, reason:"illegal_chars_in_path"}'; exit 1 ;;
esac

ABS_PATH=$(realpath "$TARGET_PATH" 2>/dev/null) || {
  jq -cn --arg p "$TARGET_PATH" '{ok:false, reason:"path_resolve_failed", path:$p}'
  exit 1
}
SHA=$(printf '%s' "$ABS_PATH" | shasum -a 256 | awk '{print $1}')
CLAIM_FILE="$BUS_CLAIMS_DIR/$SHA"

if [ ! -f "$CLAIM_FILE" ]; then
  # No-op.
  jq -cn --argjson released '[]' '{ok:true, released:$released, note:"no_claim_found"}'
  exit 0
fi

CLAIM_SID=$(jq -r '.session_id' "$CLAIM_FILE" 2>/dev/null || echo "")

if [ "$CLAIM_SID" != "$OWN_SID" ] && ! $FORCE_FLAG; then
  CLAIM_NAME=$(jq -r '.name' "$CLAIM_FILE" 2>/dev/null || echo "?")
  jq -cn --arg by "$CLAIM_NAME" '{ok:false, reason:"not_own_claim", by:$by}'
  exit 1
fi

_bus_claims_lock_acquire || { jq -cn '{ok:false, reason:"lock_timeout"}'; exit 1; }
trap _bus_claims_lock_release EXIT INT TERM
rm -f "$CLAIM_FILE"
_bus_claims_lock_release
trap - EXIT INT TERM

if [ -f "$SEND" ]; then
  BUS_NAME="$NAME" bun run "$SEND" all "unlock release $ABS_PATH" 2>/dev/null || true
fi

jq -cn --arg p "$ABS_PATH" '{ok:true, released:[$p]}'
exit 0
