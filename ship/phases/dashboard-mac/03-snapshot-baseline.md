# Phase 3: SNAPSHOT BASELINE (dashboard-mac variant) `[SwiftUI/macOS only]`

Determinism gate for SwiftSnapshotTesting. Captures the patterns rediscovered 4× during the 2026-04-26/27 vibe-island session. Without this phase, snapshot tests flake on AA drift, drag review attention from real bugs, and erode trust in the test suite.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.3.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/03-snapshot-baseline.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (verdict + which baselines re-recorded + reason class + 5× consecutive pass evidence).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/03-snapshot-baseline.md` passes AND `swift test --filter SnapshotTests` exits 0 five consecutive runs.

## Pre-slice

- Read `~/.claude/CLAUDE.md` §Epistemic discipline (Evidence-tagging, Causal-claim gate, Multi-round confound check, Diagnostic-method audit) — these apply per phase, CLAUDE.md is not auto-loaded for subagents.
- Read `~/.claude/skills/ship/phases/common/observations.md` — every "snapshot fails / passes / drifts" claim routes through observations log first.
- LSP-first when locating Swift symbols (`goToDefinition`, `findReferences`). Grep is fallback for non-symbol content only.

## §1. Time-relative views need a `frozenNow` seam

Reading wall-clock `Date()` at render time leaks into pixel output. The "5s ago" pill text changes every render → snapshot baseline drifts continuously.

**Pattern**:
```swift
struct LivenessLabel: View {
    let lastTickAt: Date
    var frozenNow: Date? = nil  // test seam, nil in production

    var body: some View {
        let now = frozenNow ?? Date()
        let secondsAgo = now.timeIntervalSince(lastTickAt)
        Text(formatAge(secondsAgo))
    }
}
```

Production call sites pass nothing (default `nil` → live `Date()`). Test call sites pass a pinned `Date(timeIntervalSince1970: 1_700_000_000)` so output is deterministic.

Reference: `Sources/VibeIsland/Helpers/LivenessLabel.swift:24-26, 31, 67`.

**Iron law**: any view that renders a relative time, animation phase, or wall-clock-derived value MUST accept a test seam before it ships. No exceptions.

## §2. Guard timer subscriptions in test mode

`.onReceive(Timer.publish(every: 1, on: .main, in: .common).autoconnect())` re-renders mid-snapshot capture even when state didn't change. Result: 1-pixel AA drift, baseline fails on next run despite no code change.

**Pattern**:
```swift
.onReceive(Timer.publish(every: 1, on: .main, in: .common).autoconnect()) { _ in
    guard frozenNow == nil else { return }  // test mode: skip timer
    refresh()
}
```

When `frozenNow` is set (test environment), the timer no-ops. Snapshot capture sees a frozen view tree.

## §3. `precision: 0.995` is for AA-drift, NOT for text drift

```swift
assertSnapshot(of: view, as: .image(precision: 0.995))
```

This tolerates ~0.5% sub-pixel anti-aliasing variance (font rasterization, color profile, retina density). It does NOT tolerate:
- Different digits (`5s` vs `6s`) — that's a clock leak, fix with `frozenNow`
- Different word (`Live` vs `Stale`) — that's a real state change, NOT a flake
- Layout shift > a few pixels — that's a SwiftUI environment change, investigate

**Rule**: if a baseline fails and the diff shows text characters changing or layout shifting, do NOT bump `precision`. Find the determinism leak.

## §4. System-render flake protocol

When baselines fail across **2 consecutive runs without code change**, system rendering shifted (font cache, color profile, OS minor update, display attached/detached). Protocol:

1. **Confirm no code change**: `git status` clean + `git log -1 -- <baseline-path>` shows the prior re-baseline commit.
2. **Wait 60s, re-run snapshot tests** — transient cache effects often clear.
3. **If still fails**: re-record baseline, commit with reason class `system-drift`, verify 5× consecutive pass.
4. **If 5× pass fails**: escalate to `/debug flaky` — there's a real non-determinism source still hiding.

**Diagnostic-method audit (CLAUDE.md §Epistemic discipline)**: if `/ship` Phase 03 has re-baselined the same view 3× in 7 days for "system drift", the mechanism is suspect. Stop re-baselining. Switch to local repro: identical snapshot in CI vs Mac → same hash? If different, the test environment is the variable, not the system.

## §5. One PR per re-baseline (commit hygiene)

Every re-baseline commit MUST:
- Touch ONLY the affected `__Snapshots__/*.png` files + (optionally) the test seam wiring
- Carry a commit subject classifying the reason: `aa-drift` / `system-drift` / `intentional-ux` / `pinned-time-refactor`
- Body: 1 sentence why the re-baseline was needed + the verification (`swift test --filter SnapshotTests` 5× pass)

Reviewer can `git log --grep='re-baseline'` to audit history. Bulk re-baselines that mix reason classes are rejected — split into one commit per class.

## §6. Acceptance gate for the phase

Before declaring Phase 03 closed, the artifact `.ship/<slug>/03-snapshot-baseline.md` MUST contain:

1. **Which baselines were re-recorded** (file paths, `__Snapshots__/*.png`)
2. **Reason class for each** (`aa-drift` / `system-drift` / `intentional-ux` / `pinned-time-refactor` / `none — no re-baseline needed`)
3. **5× consecutive pass evidence** — paste output of `for i in 1 2 3 4 5; do swift test --filter SnapshotTests || break; done` showing 5 green runs
4. **Test seam coverage**: list every time-relative or animation-driven view; for each, file:line of its `frozenNow` parameter (or equivalent)
5. **Determinism leaks found + closed** during this phase (Date() call sites, timer subscriptions, image-asset randomness, etc.) with `[cited file:line]` per leak
6. **Open `[GAP — unverified]` items** — if any view renders non-deterministically and Phase 03 ships without a fix, declare it a known flake risk explicitly

## §7. Inherited claims gate

When prior phase artifacts say "snapshots already passing" / "baseline already up to date":

- Phase 03 MUST re-run `swift test --filter SnapshotTests` from clean working tree before skipping work.
- A passing 1-time run is NOT sufficient — re-verify with 5× consecutive pass per §6.3.
- Document inherited claims + their re-verification evidence under `## Inherited Claims Audit` in `.ship/<slug>/experiments/03-snapshot-log.md`.

## §8. Failure recovery — when 5× consecutive pass fails

1. **Bisect by view**: comment out tests one at a time, find the unstable one.
2. **Inspect its render path**: any `Date()`, `Timer.publish`, `Image(systemName:)` (icon font drift), `.animation(...)` modifier, randomized color/blur?
3. **Add or fix `frozenNow` seam** per §1.
4. **Guard timers** per §2.
5. **If still flaky after seam + guard**: the view is rendering off-main or depends on async state not gated by the test fixture. Promote to `/debug flaky` with `--runs=20`.

## §9. Cross-references

- `~/.claude/rules/ship.md` §Realization Check — compiles ≠ works; snapshot pass ≠ feature works
- `~/.claude/skills/ship/phases/common/observations.md` — evidence routing
- `~/.claude/skills/ship/phases/common/rounds.md` — when N>1 re-baseline rounds happen on same view
- vibe-island canonical examples: `Sources/VibeIsland/Helpers/LivenessLabel.swift`, `Tests/VibeIslandTests/SnapshotTests/`
