# Phase 5: MONITOR (bot variant)

CLI-native canary. 30 min default (60 min if wallet-touching code).

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Pre-deploy baseline capture

- Log tail snapshot (last 100 lines, error counts)
- Heartbeat freshness
- Wallet balance (USDC, USD positions)
- Fill rate / scan rate (last hour)
- Cookie age (Poly, Kalshi)
- Process list (pgrep)

## 60s watch loop (30 min or 60 min)

```
Tick actions:
- tail logs → any NEW error pattern vs baseline?
- heartbeat < 60s old?
- bot process alive? (pgrep match expected count)
- wallet delta vs baseline — big drop = RED ALARM
- fill/scan rate vs baseline — zero activity = YELLOW ALARM
- cookie health — all still valid?
- MCP/VPS health — all services reachable?
```

## Alert rules

- Alert on CHANGES not absolutes (3 errors before + 3 errors after = ok; 0 before + 1 after = ALERT)
- Red alarm = auto-revert ready (rollback tag from Phase 3) → MANDATORY GATE even in auto-mode
- Yellow alarm = human notify, continue watch

## Rollback command ready

30-min window after deploy. If red alarm:
```bash
git reset --hard ship-<feature>-slice-<last-green>
git push --force-with-lease  # CAREFUL — confirm first
# Then singlesourceoftruth sync to VPS
```

## Post-window cleanup

- If clean: declare DONE
- Update `~/NardoWorld/CHANGELOG.md` with outcome
- Write structured lesson entry (see YAML two-track format below)

## Lesson capture — YAML two-track (required)

Every Phase 5 artifact MUST include at least one lesson entry using this structured format. Replaces freeform "lessons learned" prose.

```yaml
---
track: bug | knowledge        # bug = postmortem; knowledge = architectural decision
problem_type: <enum>          # bug-track only: timing-race | config-drift | supersede-missing | type-error | data-loss | perf-regress | security | other
decision_type: <enum>         # knowledge-track only: pattern | convention | tradeoff | non-goal | other
symptoms:                     # bug-track only (list)
  - <symptom 1>
  - <symptom 2>
root_cause: <one-line>        # bug-track only
fix_commit: <sha>             # bug-track only
architecture_pattern: <slug>  # knowledge-track only
convention: <slug>            # knowledge-track only
feature_slug: <slug>
created: <YYYY-MM-DD>
---
```

Body: 2-5 paragraphs describing the lesson. Indexed by Phase 0 recall grep (PLUG 1). Each monitor artifact may contain multiple `---`-delimited lesson blocks.

## Artifact

`.ship/<slug>/reports/05-monitor.md` (baseline snapshot, tick log, final verdict, YAML lesson blocks)

---

## Owning Agent

**strict-review** — use this agent's brief template for the phase artifact.

## SPREAD/SHRINK pass (required before closing phase)

**SPREAD (L1-L5):**
- L1 Lifecycle — create + update + retire covered?
- L2 Symmetry — every action has counterpart (write+delete, enable+disable)?
- L3 Time-lens — 1d / 30d / 365d behavior considered?
- L4 Scale — works at 10x inputs?
- L5 Resources — CPU/disk/network/tokens accounted for?

**SHRINK (Sh1-Sh5):**
- Sh1 Duplication — same logic repeated elsewhere?
- Sh2 Abstraction — premature or correct?
- Sh3 Retirement — what's now orphaned by this change?
- Sh4 Merge — can this fold into existing?
- Sh5 Simplification — can this be fewer lines?

Phase is NOT closed until all 10 items answered.
