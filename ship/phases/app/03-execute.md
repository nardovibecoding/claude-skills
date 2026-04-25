# Phase 3: EXECUTE (app variant)

Same core loop as bot variant + app-specific additions.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Pre-slice

- Context-fresh check — if session >2h old, re-read relevant files before editing
- Before each Edit — Read full file first
- Touch-and-go pattern — smallest compile-passing change first, expand incrementally

## Inherited claims gate (mandatory before skipping any "already done" item)

When a prior phase artifact (Phase 2 plan, prior /ship round, monitor report, agent self-report) marks an item as "already done" / "already shipped" / "no edit needed":

- Phase 3 MUST re-verify per `strict-execute §0.6 Premise Re-verification` BEFORE skipping that item.
- Failure to re-verify = item is treated as un-shipped, full execute applies.
- Document each inherited claim + its re-verification evidence in `.ship/<feature>/experiments/03-execution-log.md` under a new top section: `## Inherited Claims Audit`.

Persistence + run-the-thing per slice (mandatory, see `strict-execute §5.5` and `§5.6`):
- Every Write/Edit must be followed by an immediate Read on the same path to confirm diff persisted.
- Every producer/script edit must be followed by an actual invocation + mtime delta + output cat.

## Per slice (shared with bot)

1. Code change (one logical concern)
2. Rule 50 checklist
3. **Slop-scan** — strip unused imports, boilerplate, over-comments, AI-filler
4. **Visible verify** — log / curl / screenshot / data. Rule 54.
5. **Naming hygiene atomic** — rename + all call sites in same commit
6. Atomic commit, WHY message
7. **Rollback point tagged** — `git tag ship-<feature>-slice-N`
8. **Rule 8 audit trigger** — if 3rd+ change to same file

## Error recovery — Debug Protocol

### Step 0 — Triage gate (classify before protocol fires)

- **TRIVIAL** — typo, obvious syntax error, missing import, stale cache, build glitch. Fix + verify, skip steps 1-6. Max 2 attempts before promoting to non-trivial.
- **NON-TRIVIAL** — unexpected behavior, intermittent, cross-layer symptom, state corruption, race, hydration/SSR flake, flaky test. Full protocol below is MANDATORY.

Write the classification in chat before touching code. One word. If unsure, default to NON-TRIVIAL.

### Step 0.5 — Reproduction gate (hard gate on NON-TRIVIAL)

Written repro MUST exist before step 1 fires:
- command/URL/click-path that triggers the failure, OR
- exact user action + state preconditions + expected vs actual + browser/viewport if UI

No repro = no fix.

### Step 0.75 — Hypothesis template (hard gate on NON-TRIVIAL, before step 4)

```
SYMPTOM:     <what the user/browser/console observes>
EVIDENCE:    <console log, network panel, stack trace — cite line numbers>
ROOT CAUSE:  <why the bug exists, stated as a causal claim>
PROPOSED FIX: <what change, at which file:line, and why it addresses root cause>
```

If ROOT CAUSE restates SYMPTOM, iterate. Evidence must support the causal claim.

### 6-step protocol (NON-TRIVIAL only)

1. **Reproduce reliably** — confirm repro from step 0.5 fires on demand
2. **Localize layer** — UI / API / data / build / external / network / auth / cache
3. **Reduce to minimal case**
4. **Fix root cause per hypothesis** — apply PROPOSED FIX. If fix diverges mid-edit, STOP and rewrite hypothesis.
5. **Guard against recurrence** — test / log / monitor
6. **Verify end-to-end** — full user flow, not just the fixed component

**Trip-wire:** 3 fails on same issue → STOP, spawn strict-plan subagent with hypothesis block + repro + what-was-tried as brief.

## Rate-limit awareness

Dev loops hammering APIs = wasted quota. Use cached / mocks.

## App-specific per slice

- **Accessibility check** — keyboard nav works? ARIA labels present? color contrast OK?
- **Mobile responsive** — test at 375px width minimum
- **Console error scan** — no new errors in dev tools
- **UI tests** if framework exists
- **i18n readiness** — no hardcoded English if multi-locale planned

## Parallel agents

Max 3 bg agents. Each commits own slice, none pushes. Main reviews + pushes at checkpoint.

## Checkpoint every 2-3 slices

Human pause — "does this still match intent?"

Auto-mode: skip unless 3-fail trigger fires or rule 8 audit triggers.

## Artifact

`.ship/<feature>/03-execution-log.md`

---

## Owning Agent

**strict-execute** — use this agent's brief template for the phase artifact.

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
