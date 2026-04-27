# Phase 0: SPEC (dashboard-mac variant)

Pre-plan bookend. Build the question before the answer. Mostly inherits the bot/app SPEC structure; adds dashboard-mac-specific gates (audience-of-one, visual-verify default, lineage iron law).

Source spec for the route: `~/.ship/dashboard-ship-route/goals/00-spec.md`.

## Auto-decision principles (dashboard-mac)

Apply these when making judgment calls during any phase. Surface only User-Challenges and Taste-Decisions at gates.

1. **Completeness** — no half-baked widgets, no TODO panels, no "we'll wire data later"
2. **Boil lakes** — don't scope-creep; solve stated dashboard problem only
3. **Pragmatic** — ship-first, refine later; compiles-that-works > elegant-that-compiles
4. **DRY** — no duplicate widget logic, no mirrored data parsing
5. **Explicit over clever** — readable beats smart, especially in SwiftUI view bodies
6. **Bias to action** — when 2 options are close, pick the reversible one and move
7. **VISIBLE-VERIFY** — every shipped change must be observable by Bernard (screenshot, interaction, structured artifact). Compiles ≠ works
8. **AUDIENCE-OF-ONE** — Bernard alone uses this dashboard. No accessibility-for-others, no localization, no multi-user state. The constraint is the feature

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/00-spec.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (objective + REQ-ID count + top 3 risks).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/00-spec.md` passes.

## Acceptance Criteria format (EARS — mandatory)

Every AC in this spec MUST match one of these five EARS patterns. Prose ACs are REJECTED by strict-plan auditor — failing EARS parse = phase does not close.

| Pattern | Template |
|---|---|
| Event-driven | `WHEN <event> THE <system> SHALL <behavior>` |
| Conditional | `IF <precondition> THEN THE <system> SHALL <behavior>` |
| Continuous | `WHILE <state> THE <system> SHALL <behavior>` |
| Contextual | `WHERE <location/context> THE <system> SHALL <behavior>` |
| Ubiquitous | `THE <system> SHALL <behavior>` |

Each AC carries a REQ-ID (e.g. `REQ-01`) for adversarial audit citation.

Dashboard-mac-flavored examples:
- `REQ-01: WHEN <store-A> publishes its first non-empty state THE <pill-window> SHALL call orderFrontRegardless()`
- `REQ-02: IF <registry-entry> is older than 60s THEN THE <kalshi-tab> SHALL render the stale-indicator`
- `REQ-03: WHILE <snapshot tests are running> THE <LivenessLabel> SHALL read frozenNow instead of Date()`

## Steps

1. **Idea refine** — restate objective in one sentence. Is it concrete + measurable? If vague ("improve the dashboard"), push back and ask what specifically + how Bernard tells the change worked.
2. **Discovery-first grep** — search codebase for existing widgets/views that solve this. Rule 28: never propose building what exists.
3. **Audience-of-one check** — confirm the change is for Bernard's dashboard only. If it implies multi-user, accessibility-for-others, or localization, it does NOT belong on this route — re-route per `~/.ship/dashboard-ship-route/goals/00-spec.md` §2 three-test ladder.
4. **Lineage iron law (Phase 01 preview)** — for every new visible widget, sketch its Phase 01 lineage block (producer / source / schema / cadence / failure / tier). The spec is rejected if any new widget can't fill all 6 fields. This is the #1 dashboard-mac-specific gate.
5. **Test-seam preview (Phase 03 preview)** — if any new widget renders relative time, animation phase, or wall-clock-derived value, declare the test seam name now. Phase 02 will implement it; Phase 03 will baseline it.
6. **Strict-plan agent** — spawn `strict-plan` subagent for:
   - Evidence-backed objectives (file:line citations required)
   - Fabrication guard (no made-up SwiftUI APIs, no nonexistent data paths)
   - Prior-audit check (has this widget been tried before? Why didn't it ship?)
7. **ADR** — write 3-5 line Architecture Decision Record:
   - WHY this approach (e.g. Tier 3 registry vs Tier 1 file glob)
   - vs. 2 alternatives explicitly
   - trade-offs accepted
8. **Deps + risks** — list:
   - Upstream deps: producers, registries, SSH targets, cookies
   - Downstream deps: which other widgets break if this widget's data path changes
   - Visible-verify plan: what screenshot / interaction proves the change worked
   - Failure modes + rollback path

## §1. Spec content (required sections)

The phase artifact MUST contain:

```
## 1. Objective (1 sentence, measurable)
## 2. Background (why now)
## 3. Acceptance Criteria (REQ-IDs in EARS format)
## 4. Lineage preview (every new widget — see Phase 01 §2 template)
## 5. Test-seam preview (every time/animation/random widget — see Phase 03 §1)
## 6. Tier choice preview (per widget — see Phase 06 §1)
## 7. ADR (3-5 lines)
## 8. Deps + risks
## 9. Visible-verify plan (what Bernard sees post-deploy)
## 10. Out of scope (explicit)
```

## §2. Inherited claims gate

When prior /ship rounds, atoms, or lessons claim this widget / pattern / lineage already exists:

- Phase 00 MUST cite the file:line of the existing implementation OR the atom/lesson — and verify it via Read THIS SESSION before treating the claim as evidence.
- Document inherited claims + re-verification evidence in `.ship/<slug>/experiments/00-spec-log.md` under `## Inherited Claims Audit`.

## §3. Cross-references

- `~/.ship/dashboard-ship-route/goals/00-spec.md` — the route-spec; defines the 3-case classifier and audit decisions
- `~/.claude/skills/ship/phases/dashboard-mac/01-architecture.md` — lineage iron law (the §4 step here previews it)
- `~/.claude/skills/ship/phases/dashboard-mac/03-snapshot-baseline.md` — test-seam canon (the §5 step here previews it)
- `~/.claude/skills/ship/phases/dashboard-mac/06-auto-resolution.md` — tier choices (the §6 step here previews it)
- `~/.claude/rules/ship.md` §Realization Check — the visible-verify rule §7 step encodes
