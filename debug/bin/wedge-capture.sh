#!/bin/bash
# wedge-capture.sh — kernel-state trace for /debug wedge mode.
#
# Captures /proc/PID/{status,wchan,syscall,task/<tid>/{wchan,syscall}} every 30s
# for 25 min. On first state=D or state=S+low-log entry, emits DEEP CAPTURE
# block with per-thread wchan histogram, open fd count, cumulative I/O.
#
# Usage: bash wedge-capture.sh <systemd-unit>
#        bash wedge-capture.sh pm-bot.service
#        bash wedge-capture.sh kalshi-bot.service
#
# Output: /tmp/wedge-trace-<PID>.log
# Runs as the invoking user (no sudo needed). /proc/PID/stack is NOT captured
# (requires CAP_SYS_PTRACE); wchan suffices for kernel-function identification.
#
# Source: /debug Wedge mode Step 0.5. Lesson: pm-london wedge 2026-04-27.

set -uo pipefail
UNIT="${1:-}"
if [ -z "$UNIT" ]; then
  echo "usage: $0 <systemd-unit>" >&2
  exit 2
fi

PID=$(systemctl show "$UNIT" -p MainPID --value 2>/dev/null)
if [ -z "$PID" ] || [ "$PID" = "0" ]; then
  echo "no PID for unit=$UNIT" >&2
  exit 1
fi

OUT=/tmp/wedge-trace-${PID}.log
echo "=== armed for unit=$UNIT PID=$PID, log=$OUT, started $(date -u +%H:%M:%S) ===" | tee "$OUT"

CAPTURED_DEEP=0
for i in $(seq 1 50); do
  TS=$(date -u +%H:%M:%S)
  if [ ! -d /proc/$PID ]; then
    echo "$TS DEAD" >> "$OUT"
    exit 0
  fi
  STATE=$(awk '/^State:/{print $2}' /proc/$PID/status 2>/dev/null)
  RSS=$(awk '/^VmRSS:/{print $2}' /proc/$PID/status 2>/dev/null)
  LINES=$(journalctl _PID=$PID --since '30 sec ago' --no-pager -q 2>/dev/null | wc -l)
  WCHAN=$(cat /proc/$PID/wchan 2>/dev/null || echo '?')
  echo "$TS state=$STATE rss=${RSS}KB lines30s=$LINES wchan=$WCHAN" >> "$OUT"

  if [ "$CAPTURED_DEEP" = "0" ] && { [ "$STATE" = "D" ] || { [ "$STATE" = "S" ] && [ "$LINES" -lt 200 ]; }; }; then
    CAPTURED_DEEP=1
    {
      echo
      echo "=== DEEP CAPTURE @ $TS state=$STATE ==="
      echo '--- /proc/PID/status (excerpt) ---'
      grep -E '^(State|Threads|VmRSS|VmSize|voluntary|nonvoluntary|SigQ|SigPnd|SigBlk|SigIgn|SigCgt):' /proc/$PID/status
      echo '--- main wchan ---'
      cat /proc/$PID/wchan 2>&1; echo
      echo '--- per-thread (state, wchan, syscall_nr) ALL threads ---'
      for tid in $(ls /proc/$PID/task 2>/dev/null); do
        tstate=$(awk '/^State:/{print $2}' /proc/$PID/task/$tid/status 2>/dev/null)
        twchan=$(cat /proc/$PID/task/$tid/wchan 2>/dev/null || echo '?')
        tsyscall=$(cat /proc/$PID/task/$tid/syscall 2>/dev/null | awk '{print $1}' || echo '?')
        echo "tid=$tid state=$tstate syscall_nr=$tsyscall wchan=$twchan"
      done
      echo '--- wchan histogram (most common kernel functions across threads) ---'
      for tid in $(ls /proc/$PID/task 2>/dev/null); do
        cat /proc/$PID/task/$tid/wchan 2>/dev/null
        echo
      done | sort | uniq -c | sort -rn | head -10
      echo '--- syscall_nr histogram ---'
      for tid in $(ls /proc/$PID/task 2>/dev/null); do
        cat /proc/$PID/task/$tid/syscall 2>/dev/null | awk '{print $1}'
      done | sort | uniq -c | sort -rn | head -10
      echo '--- open file count ---'
      ls /proc/$PID/fd 2>/dev/null | wc -l
      echo '--- /proc/PID/io (cumulative I/O) ---'
      cat /proc/$PID/io 2>&1
      echo '--- last 50 journal lines from this PID ---'
      journalctl _PID=$PID --no-pager -q 2>/dev/null | tail -50
      echo "=== END DEEP CAPTURE ==="
      echo
    } >> "$OUT"
  fi

  sleep 30
done

echo "=== trace ended @ $(date -u +%H:%M:%S) ===" >> "$OUT"
