# Phase 2: PLAN (app variant — autoplan 4-lens + MVP 3-stage)

gstack's autoplan: parallel lens reviews, auto-decide 80%, surface only User-Challenges + Taste-Decisions.

## Heuristic validation gate (HARD)

If this PLAN produces a regex / classifier / scorer / router / pattern-matcher / threshold / promotion-criteria, follow `~/.claude/skills/ship/phases/common/heuristic-validation.md`. Author-generated retro-test does NOT close the phase. Held-out corpus (≥30 unseen TPs + ≥200 random for FP) required, written to `experiments/heuristic-validation.md`. Reject phase if recall <60% or FP >30%.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Discipline Impact gate (HARD)

This PLAN MUST include a §Discipline Impact section per `~/.claude/skills/ship/phases/common/discipline-impact.md`. Mandatory sub-fields:
- `lens:` — F-families from `~/.claude/rules/invariant-taxonomy.md` (F1.1, F4.5, F10.1, …) with 1-line rationale per code
- `applicable_DIs:` — project domain invariants from `<project>/.ship/_meta/domain-invariants.md` (per M1 meta-rule); empty allowed only with 1-line justification
- `disciplines:` — active D-codes from `~/.claude/rules/disciplines/_index.md` mapped to F-families above, each declaring its `detection:` mechanism (write-time grep / commit-time hook / runtime assertion)
- `gaps:` — F-families in `lens:` covered only by blank-titled disciplines, each with `gap_action: accept|build_detector|defer`

Phase rejected if G-D1..G-D5 fail. Each vertical slice (autoplan step 7) carries its own `lens:` so Phase 4 LAND receipts are slice-attributable.

## MVP 3-stage mindset (slavingia)

Before drafting architecture, ask: can we stay in stage 1 longer?

| Stage | What | When to graduate |
|---|---|---|
| Manual | Do it by hand per user | Process takes >50% of your time OR >10 users |
| Processized | Documented SOP, maybe Zapier/sheets/no-code | Can't scale manually; ready to automate |
| Productized | Code + automation | Proven demand + process stable |

**Build as little as possible.** Use no-code / spreadsheets / forms to ship within a weekend if possible.

## Autoplan flow

1. **Plan agent drafts** — architecture sketch, component list, data model
2. **4 lenses PARALLEL (spawn 4 bg agents):**
   - **CEO lens** — biz impact, user value, pricing, revenue path
   - **Design lens** — UX, visual hierarchy, accessibility, mobile
   - **Eng lens** — tech stack, performance, security, scalability
   - **DX lens** — developer experience if devs will use it (APIs, docs)
3. **minimalist-review lens** (slavingia) — community-aligned? reversibility? path-to-profit? time-vs-money?
4. **Auto-decide via 7 principles** — log rationale
5. **User Challenges** surfaced (models disagree with user direction)
6. **Taste Decisions** surfaced (close calls, borderline scope)
7. **Dep graph + vertical slicing** (≤5 files/slice, end-to-end working)
8. **Migration checklist** if renaming
9. **Strict-plan adversarial audit** of combined plan

## Artifact

`.ship/<feature>/02-plan.md` (with lens consensus table, User Challenges, Taste Decisions)

## Gate

Human reviews ONLY the User Challenges + Taste Decisions. Everything else auto-approved.

Auto-mode: skip gate unless User Challenges ≥ 2 (multi-lens disagreement).

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
