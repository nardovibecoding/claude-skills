---
name: upskill
description: |
  On-demand upskill scout — single-entry sweep that scouts external candidates (GitHub primary), reads internal gap + bottleneck summaries, ranks by ROI, auto-emits top-1 SPEC, and hands off to /extractskill (ADOPT-EXT) or /ship continue (FIX-* / TRIM-SKILL / CLEAN-HOUSE).
  Triggers: "/upskill", "what should I improve", "find improvements", "upskill check", "scout new tools".
  Daemons (bigd-gaps, bigd-performance, bigd-upgrade) STAY RUNNING — /upskill is the on-demand twin per /lint pattern. Read-mostly: SOP steps 1-4 are read-only; step 5 writes `.ship/upskill-<slug>/goals/01-spec.md`. No auto-install — install path delegates to /extractskill (manual invoke after handoff) per Iron Law.
  NOT FOR: lessons promotion (use /lint), inbox panel (use /bigd), bug diagnosis (use /debug), skill install (use /extractskill).
  Produces: ranked top-5 candidate list (5-category IA: FIX-DRIFT / FIX-PERF / ADOPT-EXT / TRIM-SKILL / CLEAN-HOUSE) + auto-emitted top-1 SPEC + handoff line.
user-invocable: true
---

# /upskill — on-demand upskill sweep

Single entry, no flags, no verbs. One sweep runs SOP steps 1-6 in order:

1. **External scout** — `gh search repos` (4 topics), `gh api releases` (3 SDKs), awesome-list parse. Rule-based filters (active≥90d, stars≥50). Output: candidate JSON.
2. **Internal gap scan** — read latest `~/inbox/_summaries/consumed/<DATE>_bundle.json` gaps slice; cold-fire `bigd/gaps/daemon.py --once` if stale >6h.
3. **Bottleneck telemetry** — same fast/cold pattern for performance + `dis_score_assess` (upgrade slice).
4. **Rank by ROI** — `ROI = impact / expected_token_spend`. Rule-based, NO LLM. See `references/roi-formula.md`.
5. **Emit top-1 SPEC** — write `.ship/upskill-<slug>/goals/01-spec.md` matching /ship Phase 1 EARS template.
6. **Display top-5 + handoff** — print ranked table; ADOPT-EXT → `/extractskill <url>`; others → `/ship continue upskill-<slug>`.

## v1 status

**v1 = SKELETON ONLY.** SOP steps 1-6 are stubs that echo `[stub] step N: <name>` and exit 0. Subsequent slices (S2-S7) wire actual scout / gaps / perf / rank / spec-emit / handoff logic. See `~/.ship/upskill/goals/02-plan.md` §S1-S7.

## Self-skeleton-detect (added 2026-04-27 — meta-protection)

Before /upskill claims to have "run" a sweep, the entry script MUST self-test that its own SOP steps are NOT stubs:

```bash
# scripts/upskill.sh — pre-flight self-check
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STUB_HITS=$(grep -rE '\[stub\] step|return 0  # stub|stub_step|TODO[: ]' \
    "$SCRIPT_DIR" "$SCRIPT_DIR/../references/" 2>/dev/null | wc -l)
if [ "$STUB_HITS" -gt 0 ]; then
    echo "==> /upskill self-check: $STUB_HITS stub markers found in own implementation"
    echo "==> SOP steps not yet wired. Cannot claim sweep results — output is meta-stub."
    echo "==> See: ~/.ship/upskill/goals/02-plan.md §S2-S7 for unbuilt slices."
    exit 0  # Exit gracefully WITHOUT producing fake results
fi
# Real SOP runs only if self-check passes
```

This means /upskill v1 (current) refuses to fake "I ran a scan" — it announces its own skeleton state honestly. Only after slices S2-S7 ship does /upskill produce real output.

Same /ship Phase 4 SKILL route's RC-1 (stub markers) is the build-time gate that prevents shipping the next /upskill slice as another skeleton.

## Realization Checks per emit (mirror /ship)

When SOP step 5 writes `.ship/upskill-<slug>/goals/01-spec.md`, the SPEC itself MUST run RC-1 against its own claims before being emitted:

- If the SPEC contains `TODO`, `[stub]`, `placeholder` in load-bearing sections (acceptance criteria, plan steps, verification) → BLOCK emit. Forces the planner to fill those in before handoff to /ship continue.
- Cross-ref: `~/.claude/skills/ship/phases/common/realization-checks.md` RC-1 (universal stub-marker scan).

## /extractskill subroutine boundary

For `[ADOPT-EXT]` candidates, /upskill does NOT reimplement install. It prints `Hand off: /extractskill <url>`. Bernard invokes manually — Iron Law: no auto-install. /extractskill carries its own security-auditor gate. Dedup: install logic lives in /extractskill alone.

## Pilot gate

/upskill is read-mostly. SOP step 5 writes `.ship/upskill-<slug>/goals/01-spec.md` — local file, NOT infra. No pilot gate needed for /upskill v1. Cold-fire fallback at SOP 2/3 invokes daemons, which honor their own `pilot_until=2026-05-07` gate (inherited transparently).

## Iron Laws

- NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
- NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE

## References (lazy-loaded)

- `references/roi-formula.md` — ROI formula spec (impact tiers + base_costs + cache discount)
- `references/topic-list.md` — GitHub topic list + Anthropic releases + awesome-list sources
- `references/ia-categories.md` — 5 stranger-test categories

## Spec / plan

- `~/.ship/upskill/goals/01-spec.md`
- `~/.ship/upskill/goals/02-plan.md`

## Entry

```bash
bash ~/.claude/skills/upskill/scripts/upskill.sh
```
