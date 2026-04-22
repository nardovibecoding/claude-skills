# Phase 1: SPEC (app variant — validate-first)

slavingia principle: **Sell before build.** Validate idea manually before writing code.

## Auto-decision principles (app)

1. **Completeness** — no half-baked features
2. **Boil lakes** — don't scope-creep
3. **Pragmatic** — ship-first
4. **DRY** — no duplicates
5. **Explicit over clever**
6. **Bias to action** — reversible > analysis paralysis
7. **User trust** — public-facing = err toward user safety + transparency

## Steps

1. **Idea refine + validate-idea** —
   - Who specifically wants this? (named customer segment)
   - What problem does it solve for them?
   - Can you solve it MANUALLY first for 1-3 customers before coding?
   - Has anyone paid $1+ for the manual version?
2. **Four validation questions (slavingia):**
   - Who is the customer?
   - Why do they want it?
   - Will they pay?
   - Is the problem real (not hypothetical)?
3. **Discovery-first grep** — existing implementations in your codebase or NardoWorld
4. **GitHub recon** — `gh search repos` for reference implementations, competitor analysis
5. **Market landscape** — 3-5 existing products solving this. What's the differentiator?
6. **Strict-plan agent** — evidence + fabrication guard + prior-audit
7. **ADR** — WHY this approach + 2 alternatives + trade-offs
8. **User stories** — 3-5 short stories: "As <user>, I want <X>, so <outcome>"
9. **Success metrics** — user-visible KPIs (sign-ups, retention, revenue — not code metrics)
10. **Deps + risks** — upstream deps + user safety risks (auth, payments, PII)

## Artifact

`.ship/<feature>/01-spec.md`

## Gate

Human review. If validation is weak (no paying customer yet), push back — don't build until validated.

Auto-mode: MANDATORY GATE if no validated demand. "Sell before build" principle cannot auto-approve unvalidated ideas.

---

## Owning Agent

**strict-research + strict-plan** — use this agent's brief template for the phase artifact.

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
