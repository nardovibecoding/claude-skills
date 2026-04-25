# Phase 02 — Build (Layer 3)

Verify the project compiles in release configuration before any test layer runs. Catches missing types, broken refs, syntax errors. Build failure short-circuits the value of every later layer (a snapshot test on broken code = noise).

## Command

```bash
bash ~/.claude/skills/frontendtest/lib/runner.sh build "<project-path>"
```

`runner.sh build` runs `swift build -c release` with stdout+stderr captured to `/tmp/frontendtest-build.log`.

## Pass criteria

Exit code 0.

## On fail

Capture top 20 lines of `/tmp/frontendtest-build.log` (where the actual error lines usually land before noise). Append to report buffer as:

```
[02-build] FAIL — exit <code>
<top 20 lines of log>
Full log: /tmp/frontendtest-build.log
```

## On pass

```
[02-build] PASS — swift build -c release exit 0
```

Do NOT abort skill on fail — Layers 1+2 still tried. They will likely also fail (since they share a build), but recording the failures forms the actionable diff.
