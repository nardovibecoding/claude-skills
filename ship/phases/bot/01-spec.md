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

## §6.5 Adversarial SPEC Audit (required before gate)

After all steps above, spawn a second `strict-plan` invocation with default stance: **"this SPEC has defects — find them."**

The adversarial auditor MUST:
- Cite specific REQ-IDs for each defect found
- Flag: EARS violation, missing counterpart action, unmeasurable AC, undefined terms, contradictions
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
