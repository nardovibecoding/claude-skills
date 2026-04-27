# Phase 3: EXECUTE (bot variant)

Build loop. Core execution — strengthened bookends stop shortcutting.

## Heuristic validation gate (HARD)

If EXECUTE ships a regex / classifier / scorer / router / pattern-matcher / threshold, the heuristic must have an `experiments/heuristic-validation.md` with held-out recall ≥80% and FP <10% per `~/.claude/skills/ship/phases/common/heuristic-validation.md`. If Phase 2 deferred this measurement, EXECUTE runs it before write. Do NOT ship a heuristic with held-out recall <60% or FP >30%.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Pre-slice

- **Context-fresh check** — if session >2h old, re-read relevant files before editing
- **Before each Edit** — Read full file first (rule already in system prompt, enforce here)
- **Touch-and-go pattern** — smallest compile-passing change first, expand incrementally

## Inherited claims gate (mandatory before skipping any "already done" item)

When a prior phase artifact (Phase 2 plan, prior /ship round, monitor report, agent self-report) marks an item as "already done" / "already shipped" / "no edit needed":

- Phase 3 MUST re-verify per `strict-execute §0.6 Premise Re-verification` BEFORE skipping that item.
- Failure to re-verify = item is treated as un-shipped, full execute applies.
- Document each inherited claim + its re-verification evidence in `.ship/<feature>/experiments/03-execution-log.md` under a new top section: `## Inherited Claims Audit`.

Persistence + run-the-thing per slice (mandatory, see `strict-execute §5.5` and `§5.6`):
- Every Write/Edit must be followed by an immediate Read on the same path to confirm diff persisted.
- Every producer/daemon/script edit must be followed by an actual invocation + mtime delta + output cat.

## Per slice

1. Code change (one logical concern)
2. Rule 50 checklist (internal)
3. **Slop-scan** — check output for: unused imports, boilerplate, over-comments, AI-filler. Strip before commit.
4. **Visible verify** — log output / curl endpoint / screenshot / data file. Rule 54: compiles ≠ works.
5. **Naming hygiene atomic** — rename + all call sites in same commit, or revert
6. Atomic commit, WHY message (not what)
7. **Rollback point tagged** — `git tag ship-<feature>-slice-N` (cheap insurance)
8. **Rule 8 audit trigger** — if 3rd+ change to same file, full audit of interacting parts before proceeding

## Error recovery — Debug Protocol

### Step 0 — Triage gate (classify before protocol fires)

Classify the bug in one line before entering full protocol:

- **TRIVIAL** — typo, obvious syntax error, missing import, stale cache, copy-paste miss. Fix + verify, skip steps 1-6. Max 2 attempts before promoting to non-trivial.
- **NON-TRIVIAL** — anything else: unexpected behavior, intermittent failure, cross-layer symptom, external service flake, state corruption, race. Full protocol below is MANDATORY.

Write the classification in chat before touching code. One word: `TRIVIAL` or `NON-TRIVIAL`. If unsure, default to NON-TRIVIAL.

### Step 0.5 — Reproduction test (hard gate on NON-TRIVIAL)

Before step 1 fires, a written repro MUST exist. Form:
- command/script that triggers the failure, OR
- exact user action + state preconditions + expected vs actual

Repro goes into the slice's debug log before any fix code is written. No repro = no fix. This blocks "I think I know what it is" speculative patches.

### Step 0.75 — Hypothesis template (hard gate on NON-TRIVIAL, before step 4)

Before editing code to fix, write this 4-field block in chat or in the debug log:

```
SYMPTOM:     <what the user/system observes>
EVIDENCE:    <logs, stack trace, repro output — cite line numbers>
ROOT CAUSE:  <why the bug exists, stated as a causal claim>
PROPOSED FIX: <what change, at which file:line, and why it addresses root cause>
```

If ROOT CAUSE reads like "X doesn't work" (restates symptom), the hypothesis is not ready. Iterate. Evidence must support the causal claim, not just the symptom.

### 6-step protocol (NON-TRIVIAL only)

1. **Reproduce reliably** — confirm repro from step 0.5 fires on demand. Capture timing/state/env if intermittent.
2. **Localize layer** — UI / API / data / build / external service / cron / env / network / wallet. Narrow to ONE layer before fixing.
3. **Reduce to minimal case** — strip unrelated code. Smallest script/input that still fails.
4. **Fix root cause per hypothesis** — apply PROPOSED FIX from step 0.75. If fix diverges from hypothesis mid-edit, STOP and rewrite hypothesis first.
5. **Guard against recurrence** — add a log line, assertion, or cron check that would have caught this earlier. For bots: often a health check or log pattern scanner.
6. **Verify end-to-end** — run full slice flow, not just the fixed function. Rule 54.

**Trip-wire:** 3 fails on same issue → STOP, spawn strict-plan subagent with the hypothesis block + repro + what-was-tried as the brief. Do not retry without new evidence.

## Rate-limit awareness

Dev loops hammering APIs = wasted quota. Use cached responses / mocks / paper mode for rapid iteration.

## [DANGER] annotation rule (mandatory for bot variant)

Any code path that touches wallet private keys, trade execution, or irreversible external calls (on-chain tx, API key rotation, destructive API endpoints) MUST have an inline `# [DANGER]` comment directly above the call site.

The comment must include all three fields:

```python
# [DANGER]
# caller-count: N          (grep result — how many callers reach this path)
# goroutine-risk: yes/no/n-a
# rollback-path: <explicit steps> OR 'not-possible'
result = execute_trade(order)
```

**Mandatory on commit.** strict-execute refuses to land Phase 4 if any new wallet/trade/irreversible-call path lacks this annotation. Run before closing Phase 3:

```bash
# verify all new dangerous paths are annotated
git diff HEAD~1 | grep -E "(private_key|execute_trade|sign_tx|rotate_key|destructive)" | grep -v "# \[DANGER\]"
# output must be empty
```

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
