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

## Per slice (shared with bot)

1. Code change (one logical concern)
2. Rule 50 checklist
3. **Slop-scan** — strip unused imports, boilerplate, over-comments, AI-filler
4. **Visible verify** — log / curl / screenshot / data. Rule 54.
5. **Naming hygiene atomic** — rename + all call sites in same commit
6. Atomic commit, WHY message
7. **Rollback point tagged** — `git tag ship-<feature>-slice-N`
8. **Rule 8 audit trigger** — if 3rd+ change to same file

## Error recovery — 6-step Debug Protocol

1. **Reproduce reliably** — preserve evidence
2. **Localize layer** — UI / API / data / build / external / network
3. **Reduce to minimal case**
4. **Fix root cause, not symptom** (rule 55)
5. **Guard against recurrence** — test / log / monitor
6. **Verify end-to-end**

**Trip-wire:** 3 fails on same issue → STOP, spawn strict-plan subagent.

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
