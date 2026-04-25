# Phase 05 — Aggregate Report

Combine phase 01–04 buffers into one verdict block. Persist to disk + echo summary to user.

## Verdict math

| Condition | Verdict |
|-----------|---------|
| Any FAIL or INFRA-FAIL in phases 02–04 | RED |
| All run phases PASS, but Layers 4+5 DEFERRED | AMBER |
| All five layers PASS (only possible when 4+5 ship) | GREEN |

Until Layers 4+5 ship, the steady-state success signal is **AMBER**, not GREEN. This honesty matters — claiming GREEN while a11y is unverified would violate the Realization Check.

## Artifact

Write the full report to `<project-path>/.ship/frontendtest-<YYYYMMDD-HHMMSS>.md`. Create `.ship/` if absent. Filename uses local time.

Report format:
```
=== frontendtest report for <project> @ <timestamp> ===
Layer 1 (Snapshot): [PASS|FAIL|INFRA-FAIL] <details>
Layer 2 (Logic):    [PASS|FAIL|INFRA-FAIL] <details>
Layer 3 (Build):    [PASS|FAIL] <details>
Layer 4 (A11y):     [DEFERRED] manual via Xcode Accessibility Inspector
Layer 5 (XCUITest): [DEFERRED] needs Xcode project wrapper

Verdict: <RED|AMBER|GREEN>

<failed snapshots / tests / build errors blocks if applicable>

Recommended next:
  - <actionable list — refresh baseline if intentional drift, fix test, etc.>
```

## Echo to user

Echo the same report to stdout. User sees it inline; the artifact file gives a paper trail for /ship Phase 5 monitoring or future audit.

## Exit

Exit 0 even on RED — the skill itself succeeded by reporting accurately. Caller (e.g. /ship) decides whether RED blocks downstream actions.
