#!/bin/bash
# install_alias.sh — idempotent injector for `--channels plugin:bus@local`
#
# Re-verified 2026-04-30 against live ~/.zshrc:
#   Line 50-98: function claude() { ... } — the LIVE entrypoint
#   Line 73:    ~/.local/bin/claude --model sonnet --channels plugin:telegram@... --append-system-prompt ...
#   Line 77:    ~/.local/bin/claude --model sonnet --append-system-prompt ...
#   Line 154:   alias claude='~/projects/wet/bin/wet claude' — SHADOWED by function (dead path)
#
# Strategy:
#   - Patch the two `~/.local/bin/claude` invocations inside function claude()
#   - Line 73 already has `--channels plugin:telegram@claude-plugins-official`
#       → append `,plugin:bus@local` to that flag (comma-separated channel list)
#   - Line 77 has NO --channels flag
#       → insert `--channels plugin:bus@local` after `--model sonnet`
#   - Idempotent: if `plugin:bus@local` already present on a line, skip that line
#   - Backup: ~/.zshrc.bak.<unix-ts> before any edit
#   - Atomic: write to tmpfile, then mv (handles concurrent $EDITOR)
#   - macOS BSD sed/awk only (no GNU-isms)
#
# Usage:
#   install_alias.sh                       # patches ~/.zshrc
#   install_alias.sh /path/to/test_zshrc   # patches given file (for testing)

set -euo pipefail

TARGET="${1:-$HOME/.zshrc}"
FLAG="plugin:bus@local"
EXISTING_CHANNELS="plugin:telegram@claude-plugins-official"

# Pre-flight
if [ ! -e "$TARGET" ]; then
  touch "$TARGET"
  echo "[install_alias] created empty $TARGET"
fi

# Idempotency check FIRST (avoid creating noise backups on no-op runs)
if grep -q -- "--channels[^[:space:]]*${FLAG}" "$TARGET" 2>/dev/null; then
  echo "[install_alias] no-op: ${FLAG} already present in $TARGET"
  exit 0
fi

# Backup (only when an actual edit will happen)
TS=$(date +%s)
BACKUP="${TARGET}.bak.${TS}"
cp "$TARGET" "$BACKUP"

# Atomic edit via tmpfile
TMP=$(mktemp "${TARGET}.tmp.XXXXXX")

awk -v flag="$FLAG" -v existing="$EXISTING_CHANNELS" '
{
  line = $0
  # Only operate on lines invoking ~/.local/bin/claude (the live binary path)
  if (line ~ /~\/\.local\/bin\/claude/ && line !~ flag) {
    if (line ~ ("--channels +" existing)) {
      # Case A: existing --channels flag present → append ",FLAG" to its value
      # BSD awk: no gensub, use sub() with literal anchor
      sub(("--channels +" existing), ("--channels " existing "," flag), line)
    } else if (line ~ /--model sonnet/ && line !~ /--channels/) {
      # Case B: no --channels flag → insert one after --model sonnet
      sub(/--model sonnet/, ("--model sonnet --channels " flag), line)
    }
  }
  print line
}
' "$TARGET" > "$TMP"

# Verify the patch actually changed something we expected
if ! grep -q -- "$FLAG" "$TMP"; then
  echo "[install_alias] ERROR: patch produced no change; target lacks expected pattern" >&2
  rm "$TMP"
  exit 2
fi

mv "$TMP" "$TARGET"
echo "[install_alias] patched $TARGET (backup: $BACKUP)"
echo "[install_alias] new --channels lines:"
grep -n -- "--channels" "$TARGET" || true
