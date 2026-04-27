# Phase 4: READINESS `[SwiftUI/macOS only]` (dashboard-mac variant)

The pill-reveal gate. The dashboard's pill window MUST NOT show until every store feeding the visible UI has produced its first tick. A half-loaded dashboard expanding into the user's view is the canonical UX failure this phase prevents.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.4.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/04-readiness.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (store count + Combine wiring file:line + readiness-gate verification evidence).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/04-readiness.md` passes AND a manual relaunch test confirms the pill stays hidden until first-tick.

## Pre-slice

- Read `~/.claude/CLAUDE.md` §Epistemic discipline (causal-claim gate before "the pill is hidden because store X hung").
- Read `~/.claude/skills/ship/phases/common/observations.md` — every "I relaunched and saw pill in N seconds" claim routes here.
- Phase 01 lineage table is the input — the store list comes from there.

## §1. Iron law

> **Pill window MUST NOT show until ALL stores feeding visible UI have first-tick data. No safety timeout. A hung store keeps the pill hidden — that is correct behavior.**

The user notices a missing pill. They do NOT notice a half-loaded pill that "looks fine" but renders stale data. The first failure mode is loud, the second is silent. Loud > silent for a single-user dashboard.

## §2. Combine readiness-gate pattern

```swift
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var cancellables = Set<AnyCancellable>()
    let storeA = StoreA()
    let storeB = StoreB()
    let storeC = StoreC()

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Subscribe to first non-empty $state from each store
        storeA.$state.first(where: { !$0.isEmpty })
            .combineLatest(
                storeB.$state.first(where: { !$0.isEmpty }),
                storeC.$state.first(where: { !$0.isEmpty })
            )
            .first()
            .receive(on: DispatchQueue.main)
            .sink { [weak self] _ in
                self?.pillWindow?.orderFrontRegardless()
            }
            .store(in: &cancellables)
    }
}
```

Reference: `Sources/VibeIsland/App/AppDelegate.swift` post-rev2.

## §3. No safety timeout (HARD RULE — Bernard's rule)

Do not add a `.timeout(...)` operator to the readiness gate. Do not add a `DispatchQueue.main.asyncAfter(deadline: .now() + N)` fallback that reveals the pill anyway. A hung store is a real bug — the missing pill is the symptom that makes Bernard notice it. Mask the symptom and the bug rots silently.

## §4. ExpandedView fallback for first-tick race

Even after the readiness gate fires, individual sub-views may briefly render before their downstream stores publish (race between `combineLatest` first-tick and view body rendering). Defensive pattern in `ExpandedView`:

```swift
struct ExpandedView: View {
    @ObservedObject var storeD: StoreD  // downstream from initial gate

    var body: some View {
        if storeD.state.isEmpty {
            ProgressView("Loading…")
        } else {
            DashboardContent(state: storeD.state)
        }
    }
}
```

Reference: `Sources/VibeIsland/Views/ExpandedView.swift:7-16`.

This is *not* a substitute for the readiness gate — it's a defense for the small window between gate-fires and first user expand. If `ProgressView` shows for >1s on every launch, the readiness gate is misconfigured (a store is missing from the `combineLatest` group).

## §5. Store enumeration (required content)

The phase artifact MUST list every store feeding visible UI:

```
Store: <ClassName>
  source: <which Phase 01 widget(s) it backs>
  first-tick definition: <e.g. "state.signals.count > 0", "state.lastTickAt != nil">
  cadence: <how often it ticks after the first>
  failure mode: <what makes first-tick never arrive — file missing, daemon dead, network down>
  diagnostics path: <log path or command Bernard uses to diagnose a hung store>
```

A store missing from this list is a store missing from the readiness gate. Both are spec-rejection conditions.

## §6. Failure-mode user contract (required content)

For each store, declare what the user sees when first-tick never arrives:

| Failure | User sees | Diagnosis path |
|---|---|---|
| StoreA hangs (file missing) | Pill never appears | `tail /tmp/vibeisland-launch.log` → look for "StoreA: waiting" |
| StoreB hangs (daemon dead) | Pill never appears | `launchctl print gui/$(id -u)/<storeB-producer-label>` |
| StoreC hangs (network) | Pill never appears | `nc -zv <host> <port>` from terminal |

The "Pill never appears" column is intentionally repetitive. That is the contract.

## §7. Verification at phase close

Manual relaunch test, evidence in artifact:

1. `pkill -f '<App>.app'` (or fully quit)
2. `open /Applications/<App>.app`
3. **Stopwatch start** at app launch
4. **Stopwatch stop** when pill becomes visible
5. Record: launch-to-pill-visible time (target: <1s on warm cache, <3s cold)
6. Verify pill renders fully formed (no text-mid-load, no layout shift, no spinner inside the pill itself)

Failure mode test:
1. Kill one of the producers (e.g. `launchctl bootout gui/$(id -u)/<label>`)
2. Relaunch app
3. Confirm pill stays hidden indefinitely
4. Bring producer back, relaunch app, confirm pill appears

Document both test results in `.ship/<slug>/experiments/04-readiness-log.md` with timestamps.

## §8. Inherited claims gate

When prior phase artifacts say "readiness gate already wired" / "all stores already in combineLatest":

- Phase 04 MUST re-verify by counting stores in the actual `combineLatest(...)` call site versus the §5 store list in this phase.
- Mismatch = Phase 04 is not done. Add missing stores.
- Document inherited claims + re-verification evidence in `.ship/<slug>/experiments/04-readiness-log.md` under `## Inherited Claims Audit`.

## §9. Cross-references

- `~/.claude/skills/ship/phases/dashboard-mac/01-architecture.md` §2 — the lineage table whose Bernard-controlled rows feed §5
- `~/.claude/skills/ship/phases/dashboard-mac/02-implement.md` §6 — concurrency hygiene that supports the gate
- `~/.claude/skills/ship/phases/dashboard-mac/06-auto-resolution.md` — when a store's first-tick relies on registry data, the auto-resolution wiring must be done before this phase verifies
- `~/.claude/rules/ship.md` §Realization Check — manual relaunch test is the visible-verification step
