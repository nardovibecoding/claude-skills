# Phase 01 — Precheck

Verify the target project is shaped for this skill before burning swift-build cycles.

## Steps

1. `cd <project-path>` (parameter from dispatch).
2. Assert `Package.swift` exists. On miss → halt with `[BLOCKED — no Package.swift at <path>; frontendtest only handles SwiftPM macOS apps]`.
3. Assert `Tests/` directory exists with at least one `*.swift` file. On miss → halt with `[BLOCKED — no Tests/ dir or test files found]`.
4. Grep `Package.swift` for `swift-snapshot-testing`. On miss → warn `[WARN — SnapshotTesting dep missing; Layer 1 will fail to compile]` but continue (Layers 2+3 still useful).
5. Note presence of `Tests/__Snapshots__/` baseline dir. If absent → flag `[INFO — no baselines yet; first Layer 1 run will write them]`.

## Output

Three-line block appended to report buffer:
```
[01-precheck] Package.swift: OK | Tests/: <N files> | SnapshotTesting dep: <yes/no> | baselines: <count or "none">
```

Pass criteria - both Package.swift + Tests/ exist. SnapshotTesting dep + baselines presence are info-only.
