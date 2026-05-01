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

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Discipline Impact gate (HARD)

This brief MUST include a §Discipline Impact section per `~/.claude/skills/ship/phases/common/discipline-impact.md`. Mandatory sub-fields:
- `lens:` — F-families from `~/.claude/rules/invariant-taxonomy.md` (F1.1, F4.5, F10.1, …)
- `applicable_DIs:` — project domain invariants from `<project>/.ship/_meta/domain-invariants.md` (per M1 meta-rule); empty allowed only with 1-line justification
- `disciplines:` — active D-codes from `~/.claude/rules/disciplines/_index.md` mapped to F-families above
- `gaps:` — F-families touched but covered only by blank-titled disciplines, each with `gap_action: accept|build_detector|defer`

Phase rejected if any of G-D1..G-D5 fail (see template). Phase 4 LAND must append receipts to `~/.claude/scripts/state/discipline-receipts.jsonl` per discipline this slice violated and closed.

## Acceptance Criteria format (EARS — mandatory)

Every AC in this spec MUST match one of these five EARS patterns. Prose ACs are REJECTED by strict-plan auditor — failing EARS parse = phase does not close.

| Pattern | Template |
|---|---|
| Event-driven | `WHEN <event> THE <system> SHALL <behavior>` |
| Conditional | `IF <precondition> THEN THE <system> SHALL <behavior>` |
| Continuous | `WHILE <state> THE <system> SHALL <behavior>` |
| Contextual | `WHERE <location/context> THE <system> SHALL <behavior>` |
| Ubiquitous | `THE <system> SHALL <behavior>` |

Each AC must also carry a REQ-ID (e.g. `REQ-01`) for adversarial audit citation.

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

## §4.5 Information Architecture (mandatory when target renders user-visible output)

Triggers: dashboard, app, CLI output, Telegram reply, report, markdown, HTML, any user-facing text or visual.

### IA-1 Taxonomy schema
- Define named categories (3-6 top-level) before writing any label.
- Every user-visible item must belong to exactly one category.
- Siblings within a category must use parallel structure (all verb-phrases, or all noun-phrases, never mixed).

### IA-2 Stranger test per label
Every user-facing label must pass: "Would someone who's never used this app understand what this means?"
- Reject: bare shorthand (`heartb`, `upgr`, `digest`)
- Reject: under-scoped labels ("End-to-end test" without saying which system)
- Reject: orphaned internal slugs (`bigd-pull@mac` shown raw in UI)
- Accept: action + scope qualifier ("Heartbeat files fresh", "Daily bundle generated")

### IA-3 Sort order
Specify sort discipline:
- Flow direction (input → processing → output)
- Priority (urgent → waiting → done)
- Alphabetical (only when no meaningful order exists)
- Never: insertion order / implementation-detail order

### IA-4 Category prefix consistency
Use same emoji/prefix for same category across all views. Define once at spec level.

Phase 1 cannot close if UI-producing target has any §4.5 item unanswered.

## §6.5 Adversarial SPEC Audit (required before gate)

After all steps above, spawn a second `strict-plan` invocation with default stance: **"this SPEC has defects — find them."**

The adversarial auditor MUST:
- Cite specific REQ-IDs for each defect found
- Flag: EARS violation, missing counterpart action, unmeasurable AC, undefined terms, contradictions, bare-label (shorthand without expansion), under-scoped-label (label lacks scope qualifier), mixed-taxonomy (siblings use different category schemas), orphaned-slug (internal identifier leaked to UI)
- IA defect types (bare-label, under-scoped-label, mixed-taxonomy, orphaned-slug) = CRITICAL in MVP user-visible output, MINOR only in debug/dev paths
- Return PASS only if zero CRITICAL defects found
- Any CRITICAL defect = Phase 1 CANNOT close

Write audit output to `.ship/<slug>/goals/01-spec-audit.md`.

If complexity tier = `small`, the adversarial audit is skipped (compressed Phase 1 per complexity router).

## Artifact

`.ship/<slug>/goals/01-spec.md` (legacy: `.ship/<feature>/01-spec.md` also written for backwards compat)

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
