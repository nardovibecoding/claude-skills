# Phase 6: AUTO-RESOLUTION (dashboard-mac variant)

The 3-tier pattern that eliminates the stale-light bug class. Tier 3 (registry-as-truth) is the preferred default for Bernard-controlled producers. Tier 1 (consumer-side staleness) is the fallback for external state. Tier 2 (producer-side cleanup) is a partial mitigation when Tier 3 isn't yet available.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.6.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/06-auto-resolution.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (per-widget tier choice + registry component_ids + sweeper coverage).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/06-auto-resolution.md` passes AND every widget from Phase 01 has a tier choice declared + tested.

## Pre-slice

- Read Phase 01's lineage table — the tier-choice list comes from there.
- Read `~/.claude/CLAUDE.md` §Epistemic discipline — every "the registry resolved this stale light" claim cites the read site + a timestamp.

## §1. Iron law

> **Every widget on the dashboard MUST declare its tier choice (1 / 2 / 3 / hybrid) in the phase artifact, with rationale. No `TODO`, no `???`. Hybrid widgets MUST declare which tier covers which dimension.**

A widget without a tier choice is a future stale-light bug. The lineage table from Phase 01 declared the tiers; Phase 06 wires them up.

## §2. Tier 1 — consumer-side staleness check

**When**: external/system state Bernard doesn't own (`launchctl list`, SSH-fetched state from Hel/London, `journalctl` parsing, third-party service health, network reachability).

**Pattern**:
```swift
func latestSignalWins(failGlob: String, greenGlob: String) -> SignalState {
    let failMtime = newestMtime(matching: failGlob)
    let greenMtime = newestMtime(matching: greenGlob)
    return greenMtime > failMtime ? .green : .fail
}
```

**Limitation**: requires a parseable file/glob/state on disk. When the upstream is a live API, fall back to a TTL cache + force-refresh-on-expand pattern.

**Required spec content**: file globs / SSH commands / API endpoints + the staleness threshold (`maxAgeSeconds`) + what the widget renders past staleness (gray, dash, last-known-with-stale-indicator).

## §3. Tier 2 — producer-side cleanup

**When**: producer is a Bernard-owned script that writes both FAIL and GREEN states and can self-clean. Tier 2 alone is rarely sufficient — pair with Tier 1 or Tier 3 for safety.

**Pattern**: in the producer (e.g. `e2e_smoketest.py`):
```python
def run():
    if status == "GREEN":
        for f in glob.glob(str(INBOX / "critical" / "e2e_smoketest_FAIL_*.json")):
            Path(f).unlink(missing_ok=True)
    write_status_file(status)
```

**Sweeper safety net**: daily `~/NardoWorld/scripts/bigd/fail_sweeper.sh` (already shipped 2026-04-27 04:30 HKT) archives any `*FAIL*.json` >72h old in `critical/` to `archive/`. Covers any producer Bernard didn't yet wire to Tier 2.

**Required spec content**: which producer cleans which globs + cite the cleanup site `[file:line]`.

## §4. Tier 3 — registry-as-truth (preferred default)

**When**: producer is a Bernard-controlled script (e2e_smoketest, bigd_pull, bigd-* daemons, any new dashboard widget where Bernard owns the writer).

**Producer pattern** (Python):
```python
from bigd._lib.status_registry import set_status

set_status(
    component="e2e_smoketest",
    status="GREEN",
    last_msg=f"All {n} suites passed",
    extra={"suite_count": n, "duration_s": elapsed},
)
```

`set_status()` writes `~/inbox/_status_registry.json` atomically (lockfile + temp-file rename). Latest write wins by definition.

**Consumer pattern** (Swift):
```swift
func readStatusRegistry(component: String, maxAgeSeconds: TimeInterval) -> ComponentStatus? {
    guard let data = try? Data(contentsOf: registryURL),
          let registry = try? JSONDecoder().decode(StatusRegistry.self, from: data),
          let entry = registry.components[component],
          Date().timeIntervalSince(entry.ts) < maxAgeSeconds
    else { return nil }
    return entry
}
```

When the entry is older than `maxAgeSeconds`, return `nil` and the widget renders a "stale" indicator. When entry is missing entirely, also return `nil`.

**Required spec content**: per Tier-3 widget, declare `component_id` + status states (GREEN/AMBER/RED/UNKNOWN) + `last_msg` format + `maxAgeSeconds` + `extra` schema (if any).

## §5. Hybrid widgets (per-widget declaration required)

A widget can read system state for ground-truth AND consult registry for Bernard-recorded supplemental status. When hybrid:

```
Widget: <name>
  ground-truth source: <Tier-1 mechanism>
  supplemental source: <Tier-3 component_id>
  merge rule: <e.g. "registry overrides if ts < 5min old, else fall back to system state">
  example: "PM bot London status — primary read is `ssh london systemctl is-active pm-bot.service`; if registry has fresh entry from `bigd_pull` < 5min, use that for last_msg detail"
```

Without an explicit merge rule, hybrid is rejected — implicit precedence is a future debug nightmare.

## §6. Registry-MUST narrowing rule

> **MUST use Tier 3**: producer is Bernard-controlled (e2e_smoketest, bigd_pull, bigd-* daemons, any new dashboard widget where Bernard authors the writer).
>
> **NOT required, use Tier 1 + 2 fallback**: external/system state where Bernard doesn't own the writer (`launchctl list`, SSH-fetched state, `journalctl`, third-party service health).

This is the D6 audit-fix rule applied. Trying to wedge external state into the registry creates synthetic "Bernard-controlled" wrappers that just re-encode the freshness problem inside the registry.

## §7. Sweeper coverage declaration (required content)

For every Tier-2 producer, declare whether it's covered by `fail_sweeper.sh` or has its own cleanup logic. Sweeper covers `~/inbox/critical/*FAIL*.json` >72h old.

If a producer writes FAIL files outside `~/inbox/critical/`, document where + how cleanup happens (or state explicitly that no cleanup exists, accepting the manual-archive cost).

## §8. Verification at phase close

For each tier choice:

- **Tier 1**: simulate stale state (touch a FAIL file with old mtime) → confirm widget renders stale indicator within `maxAgeSeconds`. Replace with fresh GREEN → confirm widget recovers.
- **Tier 2**: run producer with FAIL state → verify FAIL file written. Run again with GREEN → verify FAIL file deleted by producer.
- **Tier 3**: write registry entry via `set_status` → verify Swift consumer renders new state within next view refresh. Delete entry → verify "stale"/"unknown" rendering.

Paste all verification outputs into `.ship/<slug>/experiments/06-auto-resolution-log.md` with timestamps.

## §9. Inherited claims gate

When prior phase artifacts say "registry already wired" / "Tier 3 already used":

- Phase 06 MUST re-verify by reading the registry write site `[cited file:line]` AND the Swift read site `[cited file:line]` THIS SESSION before skipping work.
- Document inherited claims + re-verification evidence under `## Inherited Claims Audit`.

## §10. Cross-references

- `~/.claude/skills/ship/phases/dashboard-mac/01-architecture.md` §3 — tier choice rules live there, this phase wires them
- `~/.claude/skills/ship/phases/dashboard-mac/04-readiness.md` — Tier-3 widgets must publish first-tick before pill reveals
- `~/NardoWorld/scripts/bigd/_lib/status_registry.py` — canonical `set_status()` writer
- `~/NardoWorld/scripts/bigd/fail_sweeper.sh` — Tier 2 safety net
- `~/.claude/rules/ship.md` §Realization Check — registry write ≠ widget renders correctly; both ends must verify
