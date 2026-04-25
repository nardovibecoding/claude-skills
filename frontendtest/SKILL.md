---
name: frontendtest
description: |
  Full UI/UX testing pipeline for SwiftUI macOS projects. Runs SwiftSnapshotTesting + XCTest logic + build check + (future a11y/XCUITest). Outputs per-layer pass/fail report with actionable failures.

  Triggers - "test ui", "snapshot diff", "ui regression", "uxui test", "/frontendtest <project-path>", auto-fires after /ship Phase 4 for UI features.

  NOT FOR - backend tests (use plain `swift test` or pytest), web apps (use Playwright/axe-core), iOS apps (current scope = macOS SwiftUI only).
verified_at: 2026-04-25
---

# /frontendtest — UI/UX Testing Pipeline

One invocation runs every UI testing layer + reports per-layer pass/fail. Auto-fires after `/ship` Phase 4 for any feature with a UI surface, or manually via `/frontendtest <project-path>`.

## Dispatch

1. Parse user invocation. Extract `<project-path>` arg. Default = current working directory (`$PWD`).
2. Verify project shape via Phase 01-precheck (Package.swift + Tests/ dir + SnapshotTesting dependency). On fail → halt with clear actionable message.
3. Run phases 02→05 sequentially. **Fail-fast OFF** — every layer runs even when an earlier one fails. Each phase appends its block to the in-memory report.
4. Final aggregation written to `<project-path>/.ship/frontendtest-<YYYYMMDD-HHMMSS>.md` AND echoed to user.

## Phase flow (lazy load)

| Phase | File | Layer |
|-------|------|-------|
| 01 | `phases/01-precheck.md` | Project shape verification |
| 02 | `phases/02-build.md` | Layer 3 — `swift build -c release` |
| 03 | `phases/03-snapshot.md` | Layer 1 — `swift test --filter SnapshotTests` |
| 04 | `phases/04-logic.md` | Layer 2 — `swift test --filter LogicTests` |
| 05 | `phases/05-report.md` | Aggregate verdict + write artifact |

Layer 4 (Accessibility) and Layer 5 (XCUITest) are DEFERRED in v1 — surfaced as `[DEFERRED]` lines in the final report so verdict math stays honest.

## Helper

`lib/runner.sh` wraps `swift` invocations with stdout/stderr capture into `/tmp/frontendtest-<phase>.log`. Each phase calls `runner.sh <phase> <swift-args...>` and reads exit code + log tail.

## Output report

```
=== frontendtest report for <project> @ <timestamp> ===
Layer 1 (Snapshot): [PASS|FAIL] <details>
Layer 2 (Logic):    [PASS|FAIL] <details>
Layer 3 (Build):    [PASS|FAIL] <details>
Layer 4 (A11y):     [DEFERRED] manual via Xcode Accessibility Inspector
Layer 5 (XCUITest): [DEFERRED] needs Xcode project wrapper

Verdict: GREEN if all PASS, AMBER if any DEFERRED + no FAIL, RED if any FAIL.

Failed snapshots: <list of file paths under Tests/__Snapshots__/>
Failed tests:     <list of test names + assertion messages>
Build errors:     <captured stderr top 20 lines>

Recommended next: <actionable items>
```

Note - because Layer 4 + 5 are DEFERRED in v1, verdict can never be pure GREEN until they ship. Use `AMBER` as the steady-state success signal.

## Auto-fire integration

When /ship Phase 4 closes for a feature touching `*.swift` UI files (View/Panel/Label/Button), `/ship` should invoke `/frontendtest <project-path>` as part of Phase 5 monitoring close-out. Wiring lives in /ship phase files; this skill just needs to be callable.
