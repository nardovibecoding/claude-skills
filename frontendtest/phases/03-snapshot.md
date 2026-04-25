# Phase 03 — Snapshot Diff (Layer 1)

Pixel-diff current SwiftUI views against PNG baselines stored in `Tests/__Snapshots__/`.

## Command

```bash
bash ~/.claude/skills/frontendtest/lib/runner.sh snapshot "<project-path>"
```

Runs `swift test --filter SnapshotTests` with output captured to `/tmp/frontendtest-snapshot.log`.

## Pass criteria

Exit code 0 — every snapshot matched baseline within tolerance.

## On fail

Parse `/tmp/frontendtest-snapshot.log` for `failed - ` and `XCTAssertEqual failed` lines. Find paths to before/after PNGs (snapshot-testing writes `<TestName>.<n>.png` + `<TestName>.<n>.failure.png` next to baselines).

Report block:
```
[03-snapshot] FAIL — <N> snapshot(s) drifted
Failed snapshots:
  - Tests/VibeIslandTests/__Snapshots__/SnapshotTests/<test>.png
    failure: <same-dir>/<test>.failure.png  (review visually)
Full log: /tmp/frontendtest-snapshot.log
```

## On pass

```
[03-snapshot] PASS — all snapshot baselines matched
```

## On infra fail (e.g. test bundle didn't compile)

```
[03-snapshot] INFRA-FAIL — could not run (build broken upstream?)
Full log: /tmp/frontendtest-snapshot.log
```

Distinguish INFRA-FAIL from FAIL so verdict logic in Phase 05 doesn't double-count a build break.
