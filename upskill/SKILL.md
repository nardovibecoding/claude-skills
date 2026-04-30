---
name: upskill
description: |
  On-demand upskill scout — lens-driven 7-step sweep that resolves a lens (default `skills`), scouts external candidates via `gh search`, scores by intrinsic ROI, overlays bigd-context (perf / gaps / skills audit), prompts adopt gate for ADOPT-EXT top-1, and either (a) invokes the extract subroutine after explicit `Y` confirm or (b) prints a `/ship continue upskill-<slug>` handoff for FIX-* / TRIM-SKILL / CLEAN-HOUSE categories.
  Triggers: "/upskill", "/upskill <lens>", "/upskill menu:<file>", "/upskill health", "/upskill audit <path-or-url>", "what should I improve", "find improvements", "scout new tools", "skill health", "check skills", "audit skill safety", "scan skill before install".
  Iron Law: NO auto-adopt — Phase 6 adopt gate requires explicit `Y`. CONFIRM_BYPASS env / `--auto` flag FORBIDDEN.
  NOT FOR: external web research without gap-context (use /r1a). NOT FOR: installing the candidate without /upskill context (use /extractskill standalone with `--standalone-url`). NOT FOR: lessons promotion (use /lint). NOT FOR: inbox panel (use /daemons). NOT FOR: bug diagnosis (use /debug).
  Produces: top-5 ranked candidate list (5-category IA: FIX-DRIFT / FIX-PERF / ADOPT-EXT / TRIM-SKILL / CLEAN-HOUSE) + auto-emitted top-1 SPEC + adopt-gate decision + extract result OR fallback handoff line.
user-invocable: true
---

# /upskill v2 — lens-driven on-demand upskill sweep

Single entry: `bash ~/.claude/skills/upskill/scripts/upskill.sh [lens]`. Default lens = `skills`.

## v2 status

**v2 = ROLLED OUT (shipped 2026-04-30).** S1-S6 wired end-to-end: lens system (5 default lenses + custom menu), lens-aware scout, intrinsic ROI score, bigd-context overlay, adopt gate (Iron Law confirm), extract subroutine (security gate + ledger). v1 retired (rank.py deleted; orchestrator rewritten).

## 7-step pipeline

1. **Lens resolve** (`scripts/lens_resolve.py`) — load lens YAML, validate `scoring_weights` sum=1.0±0.01, return keyword set + gh_topics + integration_cost_model + overlay_sources. Lens = `skills` | `general` | `perf` | `gaps` | `menu:<file>`.
2. **Scout** (`scripts/scout.py`) — pre-flight `gh api rate_limit`, fan-out gh-search per lens topic+keyword combo (max 5 per call). Output: `candidates[]` + `scout_degraded` + `rate_limit_remaining`.
3. **Score** (`scripts/score.py`) — intrinsic ROI per lens weights: `impact = stars_tier×w_stars + recency×w_recency + keyword_fit×w_kw_fit + language_match×w_lang`; `cost = base_costs[integration_cost_model]`. Top-5 returned.
4. **Overlay** (`scripts/overlay.py`) — read lens `overlay_sources` (e.g. `bigd-perf`) from today's `~/inbox/_summaries/consumed/<DATE>_bundle.json`; boost candidates whose keywords match active gaps/perf hotspots. Skipped if no bundle (no-bigd path).
5. **Emit auto-spec** (`scripts/emit_spec.py`) — write top-1 SPEC to `~/.ship/upskill-<slug>/goals/01-spec.md` matching /ship Phase 1 EARS template. Append ledger row to `~/.claude/scripts/state/upskill-installs.jsonl`.
6. **Adopt gate** (`scripts/adopt_gate.py`) — for ADOPT-EXT top-1, prompt `Adopt this skill? [Y/n/skip]`. Iron Law: only literal `Y`/`y` proceeds; everything else falls through to handoff. No-TTY = `aborted_no_tty`. No bypass.
7. **Extract subroutine** (`scripts/extract.py`) — only fires on `decision=adopt`. Clones repo to `/tmp/upskill_extract_*`, runs `~/.claude/skills/upskill/scripts/skill_security_auditor.py` (folded in 2026-04-30 from the retired `skill-security-auditor` skill). Verdict gate: PASS → install to `~/.claude/skills/<slug>/`, EXTRACT-only → write to `~/NardoWorld/atoms/extracted-patterns/<slug>-<date>.md`, WARN → re-prompt, FAIL → abort. Append final ledger row.

For `FIX-DRIFT` / `FIX-PERF` / `TRIM-SKILL` / `CLEAN-HOUSE` top-1: steps 6-7 do NOT fire. Step 5 emits the spec and step 7 prints `/ship continue upskill-<slug>` instead.

## Default lenses

| lens | focus | overlay_sources |
|---|---|---|
| `skills` (default) | claude-code skill ecosystem | bigd-skills-audit |
| `general` | broad capability scout | (none) |
| `perf` | perf/cache/optimization | bigd-perf |
| `gaps` | capability-gap candidates from CLAUDE.md + realize-debt | bigd-gaps |
| `menu:<file>` | user-supplied menu list | (per-menu) |

Custom menu schema + lens authoring: `references/lens-design.md`.

## Iron Law

NO AUTO-ADOPT. Phase 6 requires explicit `Y` keystroke. The adopt_gate enforces — env var `CONFIRM_BYPASS=1` is rejected at startup, `--auto` flag does not exist, no-TTY runs (cron/CI) abort with `aborted_no_tty`. /upskill cannot be wired into a recurring daemon.

## Self-skeleton-detect (carry from v1)

Pre-flight grep refuses to fake "I ran a sweep" if SOP scripts contain stub markers. See `scripts/upskill.sh:13-20`. Sole exit path is graceful no-op with stub count.

## /extractskill subroutine boundary

Install logic ships ONCE in `scripts/extract.py`. /extractskill standalone (`--standalone-url <url>`) wraps the same code path for manual entry without /upskill context. Dedup: no parallel install path.

## Realization Checks per emit

When step 5 writes a SPEC, RC-1 (universal stub-marker scan) runs against the emitted body. SPECs with `TODO`/`[stub]`/`placeholder` in load-bearing sections BLOCK emit, forcing the planner to fill in before /ship continue handoff.

## References (lazy-loaded)

- `references/lens-design.md` — lens YAML schema + custom menu authoring
- `references/roi-formula.md` — intrinsic ROI weights + base_costs + cache discount
- `references/topic-list.md` — GitHub topic list + Anthropic releases + awesome-list sources
- `references/ia-categories.md` — 5 stranger-test categories

## Spec / plan

- `~/.ship/upskill/goals/01-spec.md` (v2)
- `~/.ship/upskill/goals/02-plan.md` (v2)
- `~/.ship/upskill/experiments/route-trace.md` (v2 SKILL-mode gate)
- `~/.ship/upskill/experiments/heuristic-validation.md` (held-out corpus per A11)

## Entry

```bash
bash ~/.claude/skills/upskill/scripts/upskill.sh           # default lens=skills
bash ~/.claude/skills/upskill/scripts/upskill.sh perf      # perf lens
bash ~/.claude/skills/upskill/scripts/upskill.sh menu:tools.json  # custom menu
```

## Verb dispatcher (added 2026-04-30, skill-consolidation step 19)

| verb | action | underlying file |
|---|---|---|
| `/upskill` (bare) | external scout sweep + ROI rank + auto-emit top-1 SPEC | `scripts/upskill.sh` (default lens=skills) |
| `/upskill scout` / `/upskill <lens>` | alias for bare with lens override | `scripts/upskill.sh <lens>` |
| `/upskill health` | broken symlinks / stale disabled / stub-only / orphan refs / inline-bloat | `references/health-check.md` (folded from `skill-health-check`, 2026-04-30) |
| `/upskill audit <path-or-url>` | pre-install security scan, 11+ threat categories | `scripts/skill_security_auditor.py` + `references/security-threat-model.md` (folded from `skill-security-auditor`, 2026-04-30) |

`/upskill audit` invocation:
```bash
python3 ~/.claude/skills/upskill/scripts/skill_security_auditor.py <fetched-skill-dir>
```
Output: PASS/WARN/FAIL JSON. /extractskill calls this same script path directly (no slash dependency).
