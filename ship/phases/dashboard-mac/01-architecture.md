# Phase 1: ARCHITECTURE (dashboard-mac variant)

Producer-consumer mapping. Every visible widget on a SwiftUI macOS dashboard MUST declare its data lineage before any code is written. This phase exists because dashboards silently rot when a producer dies, a path drifts, or a schema changes — and no one notices until the displayed number is wrong for hours.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.1.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/01-architecture.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (widget count + tier breakdown + top 3 lineage risks).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/01-architecture.md` passes AND every widget in §2 has all 6 fields filled (no `TODO`, no `???`).

## Pre-slice

- Read `~/.claude/CLAUDE.md` §Epistemic discipline (Evidence-tagging — every "this widget reads X" claim cites file:line of the read site).
- Read `~/.claude/skills/ship/phases/common/observations.md` — every "I confirmed producer X writes path Y" claim routes through observations log.
- Verify producer liveness via the protocols in `~/.claude/rules/pm-bot.md` §Liveness verdict protocol when applicable. File mtime alone is not evidence.

## §1. Iron law

> **Every visible widget on the dashboard MUST declare its data lineage in §2 below. No `TODO: figure out data source`. The phase artifact is rejected if any widget has gaps.**

A widget without declared lineage is a future stale-light bug. The lineage table is the contract that lets Phase 06 (auto-resolution) decide which mitigation tier applies.

## §2. Widget lineage table (required content)

For every visible widget, fill all 6 fields:

```
### Widget: <human-readable name>

- **producer**:        <who writes the data — cron / launchd / external SSH / live event source / user input>
- **source path**:     <real disk path OR registry component_id OR API endpoint>
- **schema**:          <fields the consumer reads, with types — e.g. `{status: "GREEN"|"AMBER"|"RED", last_msg: String, ts: ISO8601}`>
- **cadence**:         <expected refresh interval — e.g. "every 60s", "on-demand from user expand", "live stream">
- **failure modes**:   <what "no data" / "stale data" / "wrong data" looks like for this widget specifically>
- **mitigation tier**: <1 = consumer-side staleness check (latestSignalWins) | 2 = producer-side cleanup | 3 = registry-as-truth (_status_registry.json)>
```

Plus mandatory citation:

- **Producer cited**: `[cited file:line]` of the writer (script, daemon, API call site)
- **Consumer cited**: `[cited file:line]` of the SwiftUI view's read site

If the producer is external (third-party API, SSH state from another host), cite the call site that fetches it + an `[unverified-external]` tag.

## §3. Mitigation-tier decision rules

Cross-reference Phase 06 (auto-resolution) — but the decision lives here, since the architecture phase is when the choice is made.

### Tier 1 — consumer-side staleness check
- Use when: the producer is external/system state Bernard doesn't own (e.g. `launchctl list` output, SSH-fetched state from London, `journalctl` parsing, third-party service health).
- Pattern: `latestSignalWins(failGlob:, greenGlob:)` Swift helper, or equivalent `mtime`-newer-than-N comparison in the view's load path.

### Tier 2 — producer-side cleanup
- Use when: the producer is a Bernard-owned script that writes both FAIL and GREEN states and can self-clean.
- Pattern: producer deletes stale opposite-state files on each run (e.g. `e2e_smoketest.py` deletes prior `*_FAIL_*.json` on green run).

### Tier 3 — registry-as-truth (preferred default)
- Use when: the producer is a Bernard-controlled script (e2e_smoketest, bigd_pull, bigd-* daemons, any new dashboard widget where the data source is Bernard-authored).
- Pattern: producer writes `~/inbox/_status_registry.json` via `~/NardoWorld/scripts/bigd/_lib/status_registry.py` `set_status()`; Swift reads via `readStatusRegistry(component:, maxAgeSeconds:)`. Latest-write-wins by definition.

### Hybrid (per-widget declaration required)
A widget can read system state for ground-truth AND consult registry for Bernard-recorded supplemental status. When hybrid, the widget must declare BOTH lineages and the merge rule (e.g. "registry overrides if `ts` < 5min old, else fall back to system state").

## §4. Producer liveness verification (required at phase close)

For every widget with a Bernard-controlled producer, run before closing the phase:

| Producer type | Verification command |
|---|---|
| LaunchAgent | `launchctl print gui/$(id -u)/<label>` showing `state = running` + recent `last exit code = 0` |
| systemd unit (Hel/London) | `ssh <host> "systemctl is-active <unit> && journalctl -u <unit> --since '5 min ago' \| tail -5"` |
| cron job | recent log entry mtime within expected cadence + 2× margin |
| Live event source (websocket) | reconnect log line within last cadence window |
| Heartbeat file | `stat -f '%m' <path>` within expected cadence + 2× margin AND verify producer is the bot writing it (per `~/.claude/rules/pm-bot.md` §Liveness verdict protocol — mtime alone is not evidence) |

Document each verification result in `.ship/<slug>/experiments/01-architecture-log.md` with `[cited cmd]` evidence.

## §5. Schema evolution gate

When the spec adds a new field to an existing producer's output, the artifact MUST declare:

- Old schema (cited in current code)
- New schema (proposed)
- Migration plan: does the consumer need to handle both shapes during rollout? If yes, the consumer reads both keys with `??` fallback and Phase 04 (readiness) gates expand-on-ready until at least one shape parses.
- Rollback: how the consumer behaves if the new producer writes the new key but a stale consumer is still running.

## §6. Cross-host data flow declaration

When a widget displays state from another host (London/Hel SSH-fetched data, registry pulled via `bigd_pull`, etc.):

- Declare which host is **canonical** (truth source).
- Declare the **fetch mechanism** (SSH, rsync, HTTP API).
- Declare the **failure mode**: what the widget shows when the fetch is stale (cached value with stale-indicator? gray-out? hide?).
- Declare the **maxAgeSeconds** beyond which displayed data is treated as expired.

Cross-host widgets are stale-bug magnets. Phase 04 (readiness) and Phase 06 (auto-resolution) both depend on this declaration.

## §7. Test seam declaration

For every widget that renders any of: relative time, animation phase, randomized visual, or wall-clock-derived value — declare the test seam name and shape here, even before Phase 02 implements it.

```
Widget: <name>
  test seam: frozenNow: Date? = nil    // injected in tests, nil in production
  seam owner: <SwiftUI struct name>
```

This is what makes Phase 03 (snapshot-baseline) possible. A widget without a declared seam is rejected.

## §8. Phase-close checklist (gate before closing)

- [ ] Every visible widget has a §2 lineage block with all 6 fields filled
- [ ] Every widget cites producer + consumer file:line
- [ ] Every Bernard-controlled producer has a §4 liveness verification logged
- [ ] Every cross-host widget has a §6 declaration
- [ ] Every time/animation/random widget has a §7 test seam declared
- [ ] Tier choices match §3 rules (no Tier 3 declared on non-Bernard producers)
- [ ] Schema evolutions, if any, have §5 migration + rollback notes
- [ ] Inherited claims (from prior /ship rounds, prior architecture audits) are re-verified per CLAUDE.md §Independent re-derivation

## §9. Cross-references

- `~/.claude/skills/ship/phases/dashboard-mac/02-implement.md` §3 — off-main I/O patterns when consuming the lineage declared here
- `~/.claude/skills/ship/phases/dashboard-mac/04-readiness.md` — the Combine readiness gate consumes this lineage to decide which stores must first-tick before pill reveals
- `~/.claude/skills/ship/phases/dashboard-mac/06-auto-resolution.md` — the tier choices declared here drive the auto-resolution wiring in Phase 06
- `~/.claude/rules/pm-bot.md` §Liveness verdict protocol — applies to any producer claim
- `~/.claude/rules/ship.md` §Realization Check — declared lineage ≠ working lineage; live verification still required
