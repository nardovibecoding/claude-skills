#!/bin/bash
# probe_session_id.sh — confirms whether ${CLAUDE_SESSION_ID} substitution fires in skill context
#
# Open issues #13733 / #25642 (per r1a research) flag CLAUDE_SESSION_ID as unreliable
# in some hook/skill contexts. We need a ground-truth probe before S2 plugin assumes it.
#
# Bernard runs this manually from a fresh `claude` session via:
#     bash ~/.claude/skills/bus/scripts/probe_session_id.sh
# OR slash-invoke if wired (S4):
#     /bus probe
#
# Output goes to /tmp/bus_session_probe_<pid>.log AND stdout.

set -u
PROBE_LOG="/tmp/bus_session_probe_$$.log"

{
  echo "=== bus session_id probe — $(date -Iseconds) ==="
  echo "PID: $$"
  echo "PPID: $PPID"
  echo "TTY: $(tty 2>/dev/null || echo 'no tty')"
  echo "---"
  echo "CLAUDE_SESSION_ID: ${CLAUDE_SESSION_ID:-NOT_SET}"
  echo "CLAUDE_PROJECT_DIR: ${CLAUDE_PROJECT_DIR:-NOT_SET}"
  echo "CLAUDE_TTY_ID: ${CLAUDE_TTY_ID:-NOT_SET}"
  echo "CLAUDE_CONVERSATION_ID: ${CLAUDE_CONVERSATION_ID:-NOT_SET}"
  echo "---"
  echo "All CLAUDE_* env vars:"
  env | grep -E '^CLAUDE_' | sort || echo "(none)"
  echo "---"
  echo "Fallback IDs available:"
  echo "  pid=$$"
  echo "  hostname=$(hostname -s)"
  echo "  shell_pid=$$"
  echo "=== end probe ==="
} | tee "$PROBE_LOG"

echo ""
echo "[probe] log saved: $PROBE_LOG"
