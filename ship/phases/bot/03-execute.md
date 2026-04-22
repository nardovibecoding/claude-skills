# Phase 3: EXECUTE (bot variant)

Build loop. Core execution — strengthened bookends stop shortcutting.

## Pre-slice

- **Context-fresh check** — if session >2h old, re-read relevant files before editing
- **Before each Edit** — Read full file first (rule already in system prompt, enforce here)
- **Touch-and-go pattern** — smallest compile-passing change first, expand incrementally

## Per slice

1. Code change (one logical concern)
2. Rule 50 checklist (internal)
3. **Slop-scan** — check output for: unused imports, boilerplate, over-comments, AI-filler. Strip before commit.
4. **Visible verify** — log output / curl endpoint / screenshot / data file. Rule 54: compiles ≠ works.
5. **Naming hygiene atomic** — rename + all call sites in same commit, or revert
6. Atomic commit, WHY message (not what)
7. **Rollback point tagged** — `git tag ship-<feature>-slice-N` (cheap insurance)
8. **Rule 8 audit trigger** — if 3rd+ change to same file, full audit of interacting parts before proceeding

## Error recovery — 6-step Debug Protocol

When bug/failure encountered mid-slice, run this sequence (not just "retry with flag tweaks"):

1. **Reproduce reliably** — make failure happen on demand. If intermittent, capture timing/state/env. Preserve evidence: logs, error output, stack trace.
2. **Localize layer** — UI / API / data / build / external service / cron / env / network / wallet. Narrow to ONE layer before fixing.
3. **Reduce to minimal case** — strip unrelated code. Smallest script/input that still fails.
4. **Fix root cause, not symptom** — rule 55 internalized. If fix doesn't explain WHY the bug existed, it's a patch. Spawn strict-plan subagent for deep audit if stuck.
5. **Guard against recurrence** — add a log line, assertion, or cron check that would have caught this earlier. For bots: often a health check or log pattern scanner.
6. **Verify end-to-end** — run full slice flow, not just the fixed function. Rule 54.

**Trip-wire:** 3 fails on same issue → STOP, spawn strict-plan subagent for root-cause audit before retrying.

## Rate-limit awareness

Dev loops hammering APIs = wasted quota. Use cached responses / mocks / paper mode for rapid iteration.

## Bot-specific

- **Live tail during edits** — if editing trading code: `tail -f` the bot log in parallel pane
- **Paper/dry-run per slice** — trading logic changed → run paper mode 5 min, verify balances unchanged, before next slice
- **Wallet watch** — alarm on unexpected tx during dev. Check `POLY_PRIVATE_KEY` handling hasn't shifted.
- **No hot-loop** — don't leave scripts running between slices (rule from zombie-leak-audit lesson)

## Parallel agents

- Rule 7: max 3 bg agents. Each commits own slice, none pushes. Main session reviews + pushes at checkpoint.
- Rule 11: multi-agent edits to same repo = each commits, review, then push once.

## Checkpoint every 2-3 slices

Human pause — "does this still match intent?"

Auto-mode: skip unless 3-fail trigger fires or rule 8 audit triggers.

## Artifact

`.ship/<feature>/03-execution-log.md` (append per slice: commit hash, verify result, rollback tag)

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
