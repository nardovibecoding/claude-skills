---
name: ship
description: |
  Full 5-phase build+ship ritual. Auto-routes bot vs app based on target. Each phase maps to a strict-* agent. Embeds SPREAD/SHRINK at every phase close.

  BOT keywords (route to phases/bot/): dagou, kalshi, polymarket, pm-bot, london, hel, admin-bot, telegram-bot, xhs-mcp, douyin-mcp, legends, hooks, MCP servers, any internal tool.

  APP keywords (route to phases/app/): user-facing, public, launch, landing, UI, B2C, customers, tokengotchi, external-facing.

  Triggers: "ship X", "build X", "create X", "implement X", "integrate X", "audit X", "continue X". Ambiguous → ask "bot/internal or user-facing app?"

  MODES: new (default) / audit / continue / big-systemd.

  Phase files loaded lazily — only current phase in context.
verified_at: 2026-04-23
documents:
  - /Users/bernard/.claude/skills/ship/phases/bot/01-spec.md
  - /Users/bernard/NardoWorld/meta/phase4_scope.md
  - /Users/bernard/NardoWorld/meta/phase5_scope.md
  - /Users/bernard/NardoWorld/meta/phase6_scope.md
  - /Users/bernard/NardoWorld/meta/phase7_scope.md
---

# /ship — Build+Ship Ritual

5-phase bookended discipline. Per-mode phase files loaded on demand.

## Dispatch

On invoke, identify:

1. **Mode** — new (default) / audit / continue / big-systemd
2. **Variant** — bot (internal) or app (public) based on target keywords. Ambiguous → ask.
3. **Feature slug** — sanitize user's name for `.ship/<slug>/` artifact dir
4. **Big-SystemD auto-load** — if user invokes `/ship <big-systemd-phase>` (e.g. `/ship phase4`, `/ship 4.4`, `/ship inbox`), auto-load the matching `~/NardoWorld/meta/phaseN_scope.md` (4, 5, 6, 7 exist) + `~/NardoWorld/meta/big_systemd_master_plan.md` as additional context before Phase 1.

## Phase flow (lazy-load)

For each phase N:
1. Read `~/.claude/skills/ship/phases/<bot|app>/0N-<phase>.md`
2. **Identify owning strict-* agent** per Phase Agent Map below
3. Execute phase per loaded instructions — use owning agent's brief template
4. **SPREAD/SHRINK pass** before closing phase (L1-L5 + Sh1-Sh5 checklist)
5. Write `.ship/<slug>/0N-<phase>.md` artifact with full brief
6. Approval gate (skip if `--auto` mode AND no safety override triggered; Phase 5 is ALWAYS human-gated)
7. Proceed to next phase

## Phase Agent Map

| # | Phase | Owning Agent | Brief Format |
|---|---|---|---|
| 1 | SPEC | strict-research + strict-plan | §0 sources w/ fetch-ts, §1 facts w/ confidence, §2 diagnosis, §3 verdict |
| 2 | PLAN | strict-plan | §0 evidence, §1 facts, §2 diagnosis, §2.5 SPREAD/SHRINK, §3 verdict |
| 3 | EXECUTE | strict-execute | §0 snapshot, §1 goal, §2 changes, §3 wiring, §4 execution, §5 visible proof, §6 rollback, §6.5 SPREAD/SHRINK, §7 adversarial |
| 4 | LAND | strict-execute (deploy) + strict-plan (security scan) | execute brief + audit findings |
| 5 | MONITOR | strict-review (at T+24h / T+7d) | §0 original ref, §1 re-verify, §2 drift, §3 git log, §4 downstream, §5 new errors, §6 classify, §6.5 SPREAD/SHRINK, §7 lessons, §8 recommend |

Audit mode (`ship audit <project>`):
- Phase 1: strict-explore (survey codebase) → strict-plan (audit)
- Phase 2: strict-plan (reconstruct)
- Phase 4: strict-plan (security + regression)
- Phase 5: strict-review (post-audit recommendations)

## SPREAD/SHRINK checklist (required per phase)

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

## Phases

| # | Name | Purpose | Owning Agent |
|---|---|---|---|
| 1 | SPEC | idea refine, GitHub recon, strict-plan audit, ADR, deps+risks | strict-research + strict-plan |
| 2 | PLAN | architecture, dep graph, vertical slicing, migration checklist | strict-plan |
| 3 | EXECUTE | per-slice code + verify + commit, debug protocol, rate-limit awareness | strict-execute |
| 4 | LAND | smoke test, security scan, perf check, CHANGELOG, deploy | strict-execute + strict-plan |
| 5 | MONITOR | post-deploy watch loop, canary, rollback-ready | strict-review |

## Auto-approve mode

Trigger: user says "auto", "--auto", "yolo", "full auto", or "ship X and keep going".

**Auto still pauses on (safety overrides):**
- Wallet-touching code flagged in Phase 1 risk list
- 3-fail error recovery trigger in Phase 3
- Red alarm in Phase 5 monitor
- Cross-system invariant break detected
- Production data schema change

All other gates auto-approve with logged rationale.

**Phase 5 is ALWAYS human-gated** regardless of --auto. Monitor verdict requires Bernard's ack before marking feature closed.

## Modes

### `ship <feature>` — new feature (default)
Full 5 phases. Existing code = context loaded Phase 1.

### `ship audit <project>` — retroactive spec
- No Phase 3 (nothing to build)
- Phase 1: reverse-engineer SPEC from code
- Phase 2: reconstruct dep graph
- Phase 4: security scan + regression readiness
- Artifact: `.ship/<project>/audit.md`

### `ship continue <feature>` — resume
Reads `.ship/<feature>/*.md`, detects last completed phase, resumes next.

### `ship <big-systemd-phase>` — Big SystemD queue dispatch
Triggers: `/ship phase4`, `/ship 4.4`, `/ship inbox`, `/ship daemons`, `/ship state-registry`, etc.
- Auto-loads `~/NardoWorld/meta/phaseN_scope.md` (N = 4, 5, 6, 7)
- Auto-loads `~/NardoWorld/meta/big_systemd_master_plan.md`
- Maps user's phrasing to the scope doc's per-step spec
- Phase flow runs with owning strict-* agent per spec

## Artifact layout

```
.ship/<feature-slug>/
├── 01-spec.md         # strict-research/strict-plan brief
├── 02-plan.md         # strict-plan brief
├── 03-execution-log.md # strict-execute brief (one per slice)
├── 04-land.md         # strict-execute + strict-plan briefs
└── 05-monitor.md      # strict-review brief (T+24h, T+7d entries)
```

## When NOT to use /ship

| Skip for | Use instead |
|---|---|
| 1-line bug fix | direct edit + commit |
| Typo / rename single file | direct edit |
| Exploratory spike | prototype freely |
| Tiny config change | direct edit |

Rule of thumb: use when ≥3 files touched OR multi-day OR touches production data / wallet / trading logic.

## Routing disambiguation

If unclear whether bot or app, ask once:
> "Routing to /ship — is this internal/bot tooling or user-facing product?"

If user specifies mixed (e.g. "bot dashboard for users"), default to **bot** variant and flag the UI portion for app-variant Phase 3 accessibility/mobile checks.
