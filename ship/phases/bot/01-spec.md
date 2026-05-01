# Phase 1: SPEC (bot variant)

Pre-plan bookend. Build the question before the answer.

## Auto-decision principles (bot)

Apply these when making judgment calls during any phase. Surface only User-Challenges and Taste-Decisions at gates.

1. **Completeness** — no half-baked features, no TODOs-in-main
2. **Boil lakes** — don't scope-creep; solve stated problem only
3. **Pragmatic** — ship-first, refine later; compiles-that-works > elegant-that-compiles
4. **DRY** — no duplicate config, no mirrored logic
5. **Explicit over clever** — readable beats smart
6. **Bias to action** — when 2 options are close, pick the reversible one and move
7. **WALLET SAFETY** — touching keys/trades/wallet code → err toward safety, extra verification, dry-run first

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/0N-<phase>.md` via the Write tool.
- RETURN only: (a) the artifact file path, (b) a ≤15-line summary (verdict + key counts + top 3 risks).
- NEVER include the full §0-§N body in the return message. The file on disk is the source of truth.
- Phase is not closed until `test -s .ship/<feature>/0N-<phase>.md` passes.

## Discipline Impact gate (HARD)

This brief MUST include a §Discipline Impact section per `~/.claude/skills/ship/phases/common/discipline-impact.md`. Mandatory sub-fields:
- `lens:` — F-families from `~/.claude/rules/invariant-taxonomy.md` (F1.1, F4.5, F10.1, …)
- `applicable_DIs:` — project domain invariants from `<project>/.ship/_meta/domain-invariants.md` (per M1 meta-rule); empty allowed only with 1-line justification
- `applicable_concerns:` — project quality-axis concerns from `<project>/.ship/_meta/concerns.md` (per M2 meta-rule); C1-C7 from `~/.claude/rules/concerns-taxonomy.md`; empty allowed only with 1-line justification
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

1. **Idea refine** — restate objective in one sentence. Is it concrete + measurable? If vague ("improve the bot"), push back and ask what specifically + how success is measured.
2. **Discovery-first grep** — search codebase for existing implementations of this feature. Rule 28: never propose building what exists. Also check `~/NardoWorld/` for prior lessons/atoms on same topic.
3. **File-map consult** — if touching bot data, read:
   - PM bots → `~/NardoWorld/projects/prediction-markets/file-map.md`
   - Dagou → `~/NardoWorld/projects/dagou/file-map.md`
4. **GitHub recon** — `gh search repos <keyword>` for reference implementations. Rank by stars, recency, license. Report: top 3-5 repos + evaluate (fork / adapt / ignore).
5. **Protocol research** — for platform integrations (Hyperliquid, new RPC, new CLOB): fetch official docs, note WS/REST split, rate limits, auth flow, fee model.
6. **Strict-plan agent** — spawn `strict-plan` subagent for:
   - Evidence-backed objectives (file-path citations required)
   - Fabrication guard (no made-up dependencies)
   - Prior-audit check (have we tried this before and failed?)
7. **ADR** — write 3-5 line Architecture Decision Record:
   - WHY this approach
   - vs. 2 alternatives explicitly
   - trade-offs accepted
8. **Deps + risks** — list:
   - Upstream deps (code, APIs, wallets, cookies)
   - Downstream deps (what breaks if this changes)
   - Wallet exposure flag (Y/N — if Y, Principle 7 gates extra safety)
   - Failure modes + rollback path

## §2.6 CAUSAL CHAIN (required when mode = audit OR feature slug contains "debug"/"wedge"/"crash"/"hang"/"leak")

Numbered chain from trigger → observed effect. Every step must have either:
- `[cited]` — concrete evidence (file:line, log line, strace output, config snapshot), OR
- `[GAP — unverified]` — explicit unknown, must be resolved before Phase 2 closes

Zero `???` gaps. Zero "assumed" without label. A chain with any unlabeled leap = phase does not close.

**Reachability gate:** every code path cited in a step must be proven REACHABLE under the test configuration that produced the evidence. If the citation is `foo.ts:123` but an upstream filter/gate/short-circuit prevents execution from reaching line 123 under the relevant config, the citation is invalid and the step reverts to `[GAP — unverified]`. Example failure: claiming `basketAtomicity` code caused a wedge when `disabledSources` strips all signals before they reach the basketAtomicity check.

Format:
```
Step 0 (trigger):  <user/config/event action> [cited §0.x]
Step 1:            <first downstream effect> [cited §0.x]
Step 2:            <next effect> [GAP — unverified, experiment E1 in §X.9 would close]
...
Step N (observed): <wedge/crash/leak fingerprint> [cited §0.x]
```

## §2.7 PREMISE AUDIT (required when audit inherits claims from prior debug rounds OR prior shipped features)

List every premise this phase builds on from earlier work. For each:
- Source (convo ID, commit SHA, prior ship slug, or lesson file)
- Original evidence cited in source
- Verification status: `[verified]` / `[unverified — blocks next phase]` / `[partial]`

Inherited premises are NOT evidence. A premise with `[unverified — blocks next phase]` forces Phase 2 to either close the gap first or abandon the dependent path.

Example:
```
- "round 5 isolation showed flag X causes wedge" (source: convo_2026-04-24)
  Original evidence: log fingerprint, no config snapshot captured.
  Status: [unverified — blocks next phase]. Confounders possible: different commit, different disabledSources.
  Closure: re-run 3×20-min cycle with git-snapshotted config.
```

## §X.9 OPEN GAPS (required at every phase close, all phases)

Every phase ends with an explicit gap list, tagged:
- `[resolved]` — closed within this phase
- `[carry]` — carries forward but does not block next phase
- `[blocks-next]` — must resolve before next phase starts

Phase close FAILS if any `[blocks-next]` is unresolved. Auto-mode halts at a `[blocks-next]` regardless of approval settings.

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

Human review. User responds with "yes"/"go"/"approved" or edits. Per rule 56: plan-ack = full green light, no mid-chain re-confirms.

Auto-mode: skip gate UNLESS wallet exposure = Y (mandatory gate).

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
