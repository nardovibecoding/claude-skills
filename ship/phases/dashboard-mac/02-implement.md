# Phase 2: IMPLEMENT (dashboard-mac variant)

Build loop for SwiftUI macOS dashboards. Inherits the universal /ship Phase 2 disciplines (LSP-first navigation, atomic commits, slop-scan, visible-verify, naming hygiene) and adds dashboard-specific gates.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.2.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/02-implement.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (slices done + tests added + frontendtest verdict + top 3 risks).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/02-implement.md` passes AND `swift build -c release` exits 0 AND `/frontendtest <project-path>` returns green.

## Pre-slice

- Read `~/.claude/CLAUDE.md` §Epistemic discipline (applies per phase).
- Read `~/.claude/skills/ship/phases/common/observations.md` — every "I tested X, it worked/failed" claim routes through observations log first.
- **Context-fresh check** — if session >2h old, re-read changed files before editing.
- **Before each Edit** — Read the full file first.
- **Touch-and-go pattern** — smallest compile-passing change first, expand incrementally.

## §1. LSP-first (HARD RULE — applies to all Swift code reads)

When locating Swift symbols, definitions, references, or call hierarchies, use the `LSP` tool BEFORE Grep:

| Task | LSP operation |
|---|---|
| Find a type/function definition | `goToDefinition` |
| Find all call sites | `findReferences` |
| Search workspace for a symbol | `workspaceSymbol` |
| List symbols in current file | `documentSymbol` |
| Find protocol implementations | `goToImplementation` |
| Trace caller chain | `incomingCalls` |
| Trace callee chain | `outgoingCalls` |
| Read inferred type / docs | `hover` |

Grep is fallback ONLY for non-symbol content (string literals, log messages, comment text).

The `lsp-first-guard` hook will reject symbol-shaped Grep calls. Use LSP first.

## §2. SwiftUI test seam invariant (HARD RULE)

> **No SwiftUI body work without a test seam.**

Any time-relative or animation-driven view MUST accept a test seam BEFORE it ships:

```swift
struct LivenessLabel: View {
    let lastTickAt: Date
    var frozenNow: Date? = nil   // <- seam, nil in production
    var body: some View { … }
}
```

The seam is added in the same commit as the view's `body`. Adding the view first and the seam later means the snapshot baseline is captured against a non-deterministic view → Phase 03 fails or, worse, ships with a hidden flake.

Applies to:
- `Date()` reads
- `Timer.publish` subscriptions
- `.animation(.linear(duration:))` modifiers driven by elapsed time
- Any `@StateObject` whose initial state is time-derived
- Random color/blur/jitter modifiers

## §3. All file I/O off the main actor (HARD RULE)

Reading status registries, log tails, snapshot files, or any disk content from a SwiftUI view body or `@MainActor` callback freezes the UI. Stale-light bug class.

**Pattern**:
```swift
Task.detached(priority: .userInitiated) {
    let data = try Data(contentsOf: registryURL)
    let parsed = try JSONDecoder().decode(StatusRegistry.self, from: data)
    await MainActor.run {
        self.registry = parsed
    }
}
```

`Task.detached` for the I/O. `await MainActor.run { … }` for state mutation that drives view updates. Never `Task { … }` from a view body if the body itself was synthesized on `@MainActor` — that inherits main and re-enters the bug.

## §4. /frontendtest auto-fire at Phase 2 close (HARD RULE)

Before declaring Phase 2 closed, invoke `/frontendtest <project-path>`. Required green:

- `swift build -c release` exits 0
- `swift test` exits 0 (logic + snapshot)
- (Future) a11y / XCUITest layers — when shipped, also required green

If `/frontendtest` flags a snapshot failure, do NOT re-baseline here. Snapshot re-baseline is **Phase 03's job**. Phase 02 closes either green or with an explicit handoff note: "Phase 03 must re-baseline X views, reason: <class>".

## §5. Per-slice loop

1. Code change (one logical concern)
2. Rule 50 internal checklist
3. **Slop-scan** — strip unused imports, boilerplate, over-comments, AI-filler
4. **Visible verify** — log line, screenshot, or interactive demo. Compiles ≠ works (CLAUDE.md / `~/.claude/rules/ship.md` §Realization Check)
5. **Naming hygiene atomic** — rename + all call sites in same commit, or revert
6. Atomic commit, WHY message (not what)
7. **Rollback point tagged** — `git tag ship-<feature>-slice-N`
8. **Rule 8 audit trigger** — if 3rd+ change to same file, full audit of interacting parts before proceeding

## §6. Concurrency hygiene

- `@MainActor` on view-mutating types (`@StateObject` classes that publish to views).
- `nonisolated` on pure-data helpers (parsers, formatters) — avoids accidental main pinning.
- `actor` for shared state read by multiple stores (status registry cache).
- No `DispatchQueue.main.async` in new code — use `await MainActor.run` or `@MainActor` annotation. Mixed paradigms = race surface.

## §7. Inherited claims gate

When prior phase artifacts (Phase 1 architecture, prior /ship round, monitor report, agent self-report) mark an item as "already done":

- Phase 02 MUST re-verify per `strict-execute §0.6 Premise Re-verification` BEFORE skipping.
- Failure to re-verify = item is treated as un-shipped, full implement applies.
- Document inherited claims + re-verification evidence in `.ship/<feature>/experiments/02-implement-log.md` under `## Inherited Claims Audit`.

## §8. Error recovery — Debug Protocol (inherited from bot/03-execute.md)

Same triage gate: TRIVIAL → fix + verify, max 2 attempts. NON-TRIVIAL → full 6-step protocol with reproduction test (Step 0.5) + hypothesis template (Step 0.75) before edits.

When the bug is dashboard-specific (stale light, snapshot drift, pill-not-revealing), pre-classify the layer:
- **Render layer** (text wrong, layout off) → Phase 03 patterns (test seam, timer guard)
- **Readiness layer** (pill hidden, ExpandedView spinning) → Phase 04 patterns
- **Data layer** (numbers wrong, lights stale) → Phase 06 auto-resolution patterns
- **Launch layer** (.app missing on reboot, plist not firing) → Phase 05 launchd patterns

Mis-classifying the layer wastes a debug round. The 4-layer split exists because dashboard bugs cluster sharply by layer.

## §9. Phase-close checklist (gate before closing)

- [ ] `swift build -c release` exits 0
- [ ] `swift test` exits 0
- [ ] `/frontendtest <project-path>` returns green (or handoff note to Phase 03 with explicit reason class)
- [ ] All views with time/animation/random have a `frozenNow` (or equivalent) test seam
- [ ] All file I/O routes through `Task.detached` + `await MainActor.run`
- [ ] No `DispatchQueue.main.async` introduced in new code
- [ ] Slop-scan clean — no AI-filler, no orphan imports, no over-commenting
- [ ] Naming hygiene: every replaced symbol fully renamed (no stale refs, no TODO suffixes)
- [ ] Atomic commits, WHY messages
- [ ] Inherited claims audit logged

## §10. Cross-references

- `~/.claude/rules/lsp-first.md` — LSP-first canon
- `~/.claude/rules/ship.md` §Realization Check — compiles ≠ works
- `~/.claude/skills/ship/phases/common/observations.md` — evidence routing
- `~/.claude/skills/ship/phases/dashboard-mac/03-snapshot-baseline.md` — handoff target when test seams need baseline updates
- `~/.claude/skills/ship/phases/dashboard-mac/04-readiness.md` — readiness gate patterns
- `~/.claude/skills/ship/phases/dashboard-mac/06-auto-resolution.md` — registry/lineage patterns for data layer
