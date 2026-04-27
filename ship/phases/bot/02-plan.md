# Phase 2: PLAN (bot variant)

Eng-lens only. No CEO/Design/DX bloat.

## Heuristic validation gate (HARD)

If this PLAN produces a regex / classifier / scorer / router / pattern-matcher / threshold / promotion-criteria, follow `~/.claude/skills/ship/phases/common/heuristic-validation.md`. Author-generated retro-test does NOT close the phase. Held-out corpus (≥30 unseen TPs + ≥200 random for FP) required, written to `experiments/heuristic-validation.md`. Reject phase if recall <60% or FP >30%.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Steps

1. **Plan agent drafts** — spawn `Plan` subagent (Sonnet default) with spec + codebase context. Output: architecture sketch, components, files touched.
2. **Eng-lens review only** — skip CEO/Design/DX (not your stack). Strict-plan auditor re-reads the plan for:
   - Surface coverage (nothing hand-waved)
   - Dep-graph completeness
   - Edge cases
3. **Dep graph mapping** — explicit table: `X → Y` relations. What breaks if we touch X?
4. **Vertical slice decomposition** — break work into ≤5-file slices, each end-to-end working. NO horizontal (all-infra-then-features) — that's how Hel-London drifted.
5. **Migration checklist** (if rename/replace) — per CLAUDE.md naming-hygiene:
   - rename file X→Y in same commit as callers
   - update log/error strings (`"X down"` → `"Y down"`)
   - update config field names
   - grep-and-replace all references
6. **Checkpoint cadence** — every 2-3 slices = human review pause

## Artifact

`.ship/<feature>/02-plan.md` (with dep graph + vertical slice list)

## Gate

Human review. Minimal — most decisions auto-resolved via 7 principles.

Auto-mode: skip gate unless cross-system invariant break detected.

---

## Owning Agent

**strict-plan** — use this agent's brief template for the phase artifact.

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
