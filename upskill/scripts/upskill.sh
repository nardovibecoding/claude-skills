#!/usr/bin/env bash
# /upskill v2 — 7-step lens-driven orchestrator.
# See ~/.ship/upskill/goals/01-spec.md (v2) and 02-plan.md §S6.

set -euo pipefail

# Cleanup tmp artifacts on any exit (closes audit L5).
trap 'rm -f /tmp/upskill_*$$*.json' EXIT

LENS="${1:-skills}"
DATE=$(TZ=Asia/Hong_Kong date +%Y-%m-%d)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Self-skeleton-detect — refuse to fake "I ran a sweep" if SOP scripts are stubs.
STUB_HITS=$( { grep -rE --exclude=upskill.sh '\[stub\] step|return 0  # stub|stub_step|TODO[: ]' \
    "$SCRIPT_DIR" "$SCRIPT_DIR/../references/" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [ "$STUB_HITS" -gt 0 ]; then
    echo "==> /upskill self-check: $STUB_HITS stub marker(s) found in own implementation"
    echo "==> SOP steps not yet wired. Cannot claim sweep results — output is meta-stub."
    echo "==> See: ~/.ship/upskill/goals/02-plan.md §S2-S7 for unbuilt slices."
    exit 0
fi

echo "=== /upskill v2 | LENS=$LENS | DATE=$DATE | self-check=PASS ==="

LENS_OUT="/tmp/upskill_lens_$$.json"
SCOUT_OUT="/tmp/upskill_scout_$$.json"
SCORE_OUT="/tmp/upskill_score_$$.json"
OVERLAY_OUT="/tmp/upskill_overlay_$$.json"
EMIT_OUT="/tmp/upskill_emit_$$.json"
DECISION_OUT="/tmp/upskill_decision_$$.json"
EXTRACT_OUT="/tmp/upskill_extract_$$.json"

# Step 1 — Lens resolve (S1).
python3 "$SCRIPT_DIR/lens_resolve.py" --lens "$LENS" --out "$LENS_OUT" >/dev/null
jq -r '"step 1 (lens): name=\(.name)  keywords=\(.keywords | length)  topics=\(.gh_topics | length)  cost_model=\(.integration_cost_model)"' "$LENS_OUT"

# Step 2 — Scout (S2).
python3 "$SCRIPT_DIR/scout.py" --lens "$LENS_OUT" --out "$SCOUT_OUT" >/dev/null || true
jq -r '"step 2 (scout): candidates=\(.candidates | length)  degraded=\(.scout_degraded)  rate_limit=\(.rate_limit_remaining)  skipped=\(.scout_skipped // "no")"' "$SCOUT_OUT"

# Step 3 — Score (S3).
python3 "$SCRIPT_DIR/score.py" --scout "$SCOUT_OUT" --lens "$LENS_OUT" --out "$SCORE_OUT" --top 5 >/dev/null
jq -r '"step 3 (score): ranked=\(.ranked | length)  total=\(.total_candidates)  co_tied=\(.co_tied_top)"' "$SCORE_OUT"

# Step 4 — Overlay (S4).
python3 "$SCRIPT_DIR/overlay.py" --scored "$SCORE_OUT" --lens "$LENS_OUT" --out "$OVERLAY_OUT" >/dev/null
jq -r '"step 4 (overlay): applied=\(.overlay_applied)  sources_used=\(.overlay_sources_used | length)  missing=\(.overlay_sources_missing | length)"' "$OVERLAY_OUT"

# Top-5 human-readable table.
echo "--- top-5 candidates ---"
jq -r '.ranked[] | "[\(.ia_category // "?")] \(.id // .name // "?") — ROI=\(.roi // 0) stars=\(.raw.stars // 0)"' "$OVERLAY_OUT" || echo "(no candidates)"

# Step 5 — Emit auto-spec for top-1 (carry-over from v1 emit_spec.py).
python3 "$SCRIPT_DIR/emit_spec.py" --ranked "$OVERLAY_OUT" > "$EMIT_OUT"
EMIT_SPEC=$(jq -r '.spec // "(none)"' "$EMIT_OUT")
EMIT_SLUG=$(jq -r '.slug // ""' "$EMIT_OUT")
echo "step 5 (emit): spec=$EMIT_SPEC"

# Step 6 — Adopt gate (S5). Iron Law: explicit Y required, no auto-adopt.
python3 "$SCRIPT_DIR/adopt_gate.py" --overlay "$OVERLAY_OUT" --out "$DECISION_OUT"
DECISION=$(jq -r '.decision' "$DECISION_OUT")
REASON=$(jq -r '.reason // ""' "$DECISION_OUT")
echo "step 6 (gate): decision=$DECISION reason=$REASON"

# Step 7 — Extract subroutine OR fallback handoff.
if [ "$DECISION" = "adopt" ]; then
    python3 "$SCRIPT_DIR/extract.py" --decision "$DECISION_OUT" --out "$EXTRACT_OUT"
    INSTALL_STATUS=$(jq -r '.install_status' "$EXTRACT_OUT")
    SECURITY=$(jq -r '.security_verdict // "n/a"' "$EXTRACT_OUT")
    echo "step 7 (extract): install_status=$INSTALL_STATUS security=$SECURITY"
elif [ "$DECISION" = "n/a" ] && [ -n "$EMIT_SLUG" ]; then
    echo "step 7 (handoff): /ship continue upskill-$EMIT_SLUG"
    echo "                   spec at $EMIT_SPEC"
else
    echo "step 7 (no install): decision=$DECISION (no extract path)"
fi

exit 0
