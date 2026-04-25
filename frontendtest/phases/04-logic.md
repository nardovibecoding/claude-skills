# Phase 04 — Logic Unit Tests (Layer 2)

Pure-function XCTest cases. Catches threshold misconfigs, sort instability, enum-mapping drift — the class of bugs Bernard previously caught manually.

## Command

```bash
bash ~/.claude/skills/frontendtest/lib/runner.sh logic "<project-path>"
```

Runs `swift test --filter LogicTests` with output captured to `/tmp/frontendtest-logic.log`.

## Pass criteria

Exit code 0.

## On fail

Parse `/tmp/frontendtest-logic.log` for lines matching `Test Case .* failed` and `XCTAssert.* failed`. Pair each failing test name with its assertion message (next 1–3 lines).

Report block:
```
[04-logic] FAIL — <N> test(s) failed
Failed tests:
  - <ClassName.testName>: <assertion message>
  - ...
Full log: /tmp/frontendtest-logic.log
```

## On pass

```
[04-logic] PASS — <N> tests green
```

## On infra fail

```
[04-logic] INFRA-FAIL — could not run (build broken upstream?)
Full log: /tmp/frontendtest-logic.log
```
