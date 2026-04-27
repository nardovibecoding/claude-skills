#!/usr/bin/env bash
# /upskill entry point — v1 SKELETON
# SOP steps 1-6 are stubs. S2-S7 will wire real logic.
# See ~/.ship/upskill/goals/02-plan.md §S1.

set -euo pipefail

DATE=$(TZ=Asia/Hong_Kong date +%Y-%m-%d)

echo "=== /upskill | DATE=$DATE | mode=skeleton ==="

echo "[stub] step 1: external scout (gh search repos / Anthropic releases / awesome-lists)"
echo "[stub] step 2: internal gap scan (read consumed bundle / cold-fire bigd-gaps)"
echo "[stub] step 3: bottleneck telemetry (read perf bundle / cold-fire bigd-performance + dis_score_assess)"
echo "[stub] step 4: rank by ROI (impact / expected_token_spend, rule-based)"
echo "[stub] step 5: emit top-1 SPEC to .ship/upskill-<slug>/goals/01-spec.md"
echo "[stub] step 6: display top-5 + handoff line (/extractskill <url> or /ship continue upskill-<slug>)"

exit 0
