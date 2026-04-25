#!/usr/bin/env bash
# frontendtest skill — swift command runner with stdout+stderr capture.
# Usage: runner.sh <phase> <project-path>
#   phase = build | snapshot | logic
# Writes to /tmp/frontendtest-<phase>.log and echoes a single status line to stdout.

set -u

PHASE="${1:-}"
PROJECT="${2:-}"

if [ -z "$PHASE" ] || [ -z "$PROJECT" ]; then
    echo "frontendtest-runner: usage: runner.sh <build|snapshot|logic> <project-path>" >&2
    exit 2
fi

if [ ! -d "$PROJECT" ]; then
    echo "frontendtest-runner: project path not found: $PROJECT" >&2
    exit 2
fi

LOG="/tmp/frontendtest-${PHASE}.log"
cd "$PROJECT" || exit 2

case "$PHASE" in
    build)
        swift build -c release > "$LOG" 2>&1
        ;;
    snapshot)
        swift test --filter SnapshotTests > "$LOG" 2>&1
        ;;
    logic)
        swift test --filter LogicTests > "$LOG" 2>&1
        ;;
    *)
        echo "frontendtest-runner: unknown phase: $PHASE" >&2
        exit 2
        ;;
esac

EXIT=$?
echo "frontendtest-runner phase=$PHASE exit=$EXIT log=$LOG"
exit $EXIT
