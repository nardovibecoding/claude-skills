#!/usr/bin/env bash
# /upskill entry point — v1 SKELETON
# SOP steps 1-6 are stubs. S2-S7 will wire real logic.
# See ~/.ship/upskill/goals/02-plan.md §S1.

set -euo pipefail

DATE=$(TZ=Asia/Hong_Kong date +%Y-%m-%d)

# --- Self-skeleton-detect (per SKILL.md §Self-skeleton-detect, 2026-04-27) ---
# /upskill must refuse to fake "I ran a scan" if its own SOP steps are unwired stubs.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STUB_HITS=$(grep -rE --exclude=upskill.sh '\[stub\] step|return 0  # stub|stub_step|TODO[: ]' \
    "$SCRIPT_DIR" "$SCRIPT_DIR/../references/" 2>/dev/null | wc -l | tr -d ' ')
if [ "$STUB_HITS" -gt 0 ]; then
    echo "==> /upskill self-check: $STUB_HITS stub marker(s) found in own implementation"
    echo "==> SOP steps not yet wired. Cannot claim sweep results — output is meta-stub."
    echo "==> See: ~/.ship/upskill/goals/02-plan.md §S2-S7 for unbuilt slices."
    exit 0  # graceful exit — refuse to produce fake results
fi

echo "=== /upskill | DATE=$DATE | self-check=PASS ==="

# Step 1 (S4): external scout via gh CLI. Writes JSON to /tmp; jq prints summary line.
SCOUT_OUT="/tmp/upskill_scout_$$.json"
python3 ~/.claude/skills/upskill/scripts/scout.py --out "$SCOUT_OUT" >/dev/null
jq -r '"step 1: candidates=\(.candidates | length)  degraded=\(.scout_degraded)  rate_limit=\(.rate_limit_remaining)  skipped=\(.scout_skipped // "no")"' "$SCOUT_OUT"
# Step 2 (S2): real internal gap reader. Writes JSON to /tmp; jq prints summary line.
GAPS_OUT="/tmp/upskill_gaps_$$.json"
python3 ~/.claude/skills/upskill/scripts/gaps_read.py --out "$GAPS_OUT"
jq -r '"step 2: \(.findings_by_severity | to_entries | map("\(.key)=\(.value)") | join(" "))  cold_fired=\(.cold_fired)"' "$GAPS_OUT"
# Step 3 (S3): bottleneck telemetry reader. token_spend / cache_hit / dis_score / host_metrics.
PERF_OUT="/tmp/upskill_bottleneck_$$.json"
python3 ~/.claude/skills/upskill/scripts/bottleneck_read.py --out "$PERF_OUT"
jq -r '"step 3: tokens_7d=\(.token_spend_recent_7d.total_tokens)  cache_hit=\(.cache_hit_rate_recent_7d)  dis_score_count=\(.dis_score | length)  cold_fired=\(.cold_fired)"' "$PERF_OUT"
# Step 4 (S5): rank by ROI. Aggregates S2/S3/S4 → unified candidate list.
RANK_OUT="/tmp/upskill_ranked_$$.json"
python3 ~/.claude/skills/upskill/scripts/rank.py \
  --gaps "$GAPS_OUT" --bottleneck "$PERF_OUT" --scout "$SCOUT_OUT" \
  --out "$RANK_OUT"
jq -r '"step 4: ranked_top=\(.ranked | length)  total=\(.total_candidates)  co_tied=\(.co_tied_top)  by_cat=\(.by_category | to_entries | map("\(.key)=\(.value)") | join(","))"' "$RANK_OUT"

# Step 5 (S6): emit top-1 SPEC + ledger row.
EMIT_OUT="/tmp/upskill_emit_$$.json"
python3 ~/.claude/skills/upskill/scripts/emit_spec.py --ranked "$RANK_OUT" > "$EMIT_OUT"
jq -r '"step 5: spec=\(.spec // "<none>")  ledger=\(.ledger // "<none>")  ia=\(.ia_category // "?")  roi=\(.roi // 0)"' "$EMIT_OUT"

# Top-3 human-readable
echo "--- top-3 candidates ---"
jq -r '.ranked[:3] | to_entries | map("[\(.key+1)] [\(.value.ia_category)] \(.value.id) — ROI=\(.value.roi) (impact=\(.value.impact), cost=\(.value.expected_token_spend))") | .[]' "$RANK_OUT"

# Step 6 (S7): handoff routing based on top-1 candidate's IA category.
# Reads ranked + emit JSON; prints suggested next command. Does NOT auto-invoke (deferred to v1.1 per spec).
TOP1_CAT=$(jq -r '.ranked[0].ia_category // "UNKNOWN"' "$RANK_OUT")
TOP1_ID=$(jq -r '.ranked[0].id // "unknown"' "$RANK_OUT")
TOP1_URL=$(jq -r '.ranked[0].raw.url // ""' "$RANK_OUT")
EMIT_SLUG=$(jq -r '.slug // ""' "$EMIT_OUT")
case "$TOP1_CAT" in
  ADOPT-EXT)
    if [ -n "$TOP1_URL" ]; then
      echo "step 6: handoff -> /extractskill $TOP1_URL  (top-1: $TOP1_ID)"
      echo "        run \`/extractskill $TOP1_URL\` to install"
    else
      echo "step 6: handoff -> /extractskill <url>  (top-1: $TOP1_ID; url missing in scout payload)"
    fi
    ;;
  FIX-DRIFT|FIX-PERF|TRIM-SKILL|CLEAN-HOUSE)
    SLUG="upskill-${EMIT_SLUG:-$(echo "$TOP1_ID" | tr '[:upper:]_' '[:lower:]-')}"
    echo "step 6: handoff -> /ship continue $SLUG  (top-1: $TOP1_ID, cat: $TOP1_CAT)"
    echo "        spec at ~/.ship/$SLUG/goals/01-spec.md"
    ;;
  UNKNOWN|*)
    echo "step 6: no top-1 candidate (empty rank or co-tied with no clear winner)"
    ;;
esac

exit 0
