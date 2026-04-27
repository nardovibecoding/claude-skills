# Phase 7: DEPLOY `[macOS only]` (dashboard-mac variant)

The `.app` bundle replace flow + visible-verification gate. Visual verification is the default — for a single-user dashboard, "Bernard sees the change live" is the canonical proof. The escape hatch (structured verification) covers headless changes only.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.7.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/07-deploy.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (verification mode + 5 deploy-step status + visible-verify evidence path).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/07-deploy.md` passes AND all 5 deploy steps logged AND verification evidence (screenshot or structured artifact) attached.

## Pre-slice

- Read `~/.claude/CLAUDE.md` §Epistemic discipline — visible-verify section enforces "compiles ≠ works".
- Read `~/.claude/rules/ship.md` §Realization Check (compiles ≠ works) — same canon, slightly different framing.

## §1. The 5 deploy steps (mandatory, ordered)

```
1. swift build -c release        → exit 0
2. swift test                    → exit 0 (snapshots + logic)
3. cp .build/release/<App> "/Applications/<App>.app/Contents/MacOS/<App>"
4. pkill -f '<App>.app' && open /Applications/<App>.app
5. Visible verification (or structured escape hatch — see §3)
```

Step 3 replaces only the bundle's binary. The rest of the bundle (Info.plist, resources, code signature for self-signed builds) stays put. This survives reboot via the existing LoginItem / LaunchAgent that points to `/Applications/<App>.app`.

Step 4 is hard-restart, not graceful. SwiftUI macOS apps with persistent windows need a kill-and-relaunch to pick up new binary code paths reliably.

## §2. Visible verification (default mode)

Bernard must see all four of these post-deploy:

1. **Pill is visible** after launch (within readiness gate window from Phase 04, target <3s cold)
2. **Expand renders without spinner** (or with spinner only briefly per Phase 04 §4 fallback)
3. **Numbers / lights match upstream** data sources (cross-check against Phase 01 source paths)
4. **The specific feature being shipped is observable** — screenshot, log line, interaction trace, or panel-state-change confirms the change is live

Step 4 is the non-negotiable one. "I shipped a new lineage tab" requires Bernard clicking that tab and seeing the right nodes. Compiles + boots + previous features still work is necessary but not sufficient.

## §3. Structured-verification escape hatch (explicit)

Visual verification is the default. For non-UI changes, structured verification substitutes:

| Change class | Structured verification |
|---|---|
| Schema migration (`_status_registry.json` adds new key) | JSON diff before/after + read-roundtrip test passes |
| Plist `StartInterval` change (30min → 60min) | `launchctl print` shows new interval |
| Pure-logic refactor (extract method, no behavior change) | Test pass + log output identical to baseline (paste both) |
| CI-only changes (lint rule, no runtime impact) | CI green |

The phase artifact MUST declare `verification_mode: visual | structured` + (if structured) evidence path.

If a change touches BOTH UI and headless (e.g. registry schema migration + new tab consuming new key), verification is `visual` for the UI part — the headless part is verified inside the visual flow.

## §4. Pre-deploy checklist (gate before step 1)

- [ ] All prior phase artifacts (00-06) closed and on disk
- [ ] Phase 03 snapshot tests passed 5× consecutively (cite log)
- [ ] Phase 04 readiness gate manually verified (cite log)
- [ ] Phase 05 plist + script + heartbeat verified (cite log)
- [ ] Phase 06 tier choices verified (cite log)
- [ ] Working tree clean for the project (no uncommitted changes that would ship in the binary)
- [ ] No nested `.git` warnings from auto-commit hooks (Phase 05 §5 guard)

## §5. Post-deploy verification log (required content)

```
deploy_at: <ISO8601>
verification_mode: visual | structured
swift_build_exit: 0
swift_test_exit: 0
binary_replaced: yes (cp output: <stat-mtime-after>)
relaunch_pid: <new pid from `pgrep -f <App>.app`>
pill_visible_at: <stopwatch from launch, in seconds>
visible_verify_evidence: <screenshot path | log line | structured artifact path>
post_deploy_persistence_check: <reboot test result OR "deferred to next reboot, expected to persist via LoginItem">
```

## §6. Persistence verification

A successful step 4 launch is necessary but doesn't prove the bundle persists across reboot. For first-time deploys of a new app or first-time deploy after a LoginItem / LaunchAgent change:

1. Force reboot (`sudo shutdown -r now`)
2. Login
3. Confirm app auto-launches (within 30s of login)
4. Confirm pill visible per §2

For subsequent deploys (binary-replace only, LoginItem unchanged), persistence is presumed. Note in artifact: `post_deploy_persistence_check: deferred-presumed-good`.

## §7. Failure handling — when visible-verify fails

Step 5 fails (pill stays hidden, numbers wrong, feature not observable):

1. **Do NOT auto-rollback** the binary. Visual changes are sometimes intentional UX shifts that look "wrong" until Bernard adjusts.
2. **Capture evidence**: screenshot of failure state + tail of `/tmp/<App>.stderr` + `tail /tmp/vibeisland-launch.log`.
3. **Check Phase 04 readiness gate**: did all stores first-tick? `tail /tmp/<App>-readiness.log` (if logging enabled) or check store state via debugger.
4. **Triage**:
   - If readiness gate hung → Phase 04 issue, fix at Phase 04 layer
   - If render layer wrong → Phase 03 (snapshot) likely missed it, re-baseline OR fix view
   - If data layer wrong → Phase 06 tier choice issue, fix tier wiring
   - If launch layer wrong → Phase 05 plist issue
5. **Bernard decides**: rollback or fix-forward. Do not auto-decide.

## §8. Inherited claims gate

When prior phase artifacts say "deploy already done" / "binary already replaced":

- Phase 07 MUST re-verify with `pgrep -f <App>.app` showing a fresh PID + `stat -f '%m' /Applications/<App>.app/Contents/MacOS/<App>` showing recent mtime.
- File mtime alone proves binary replaced; PID change proves relaunch happened.
- Document inherited claims + re-verification evidence under `## Inherited Claims Audit`.

## §9. Cross-references

- `~/.claude/skills/ship/phases/dashboard-mac/03-snapshot-baseline.md` — `swift test` step 2 input
- `~/.claude/skills/ship/phases/dashboard-mac/04-readiness.md` — pill-visible verification step
- `~/.claude/skills/ship/phases/dashboard-mac/05-launchd.md` — persistence depends on the LaunchAgent shipped there
- `~/.claude/skills/ship/phases/dashboard-mac/06-auto-resolution.md` — numbers-match-upstream depends on tier wiring
- `~/.claude/rules/ship.md` §Realization Check — the canon visible-verify rule
- `~/.claude/CLAUDE.md` §Epistemic discipline — verification evidence format
