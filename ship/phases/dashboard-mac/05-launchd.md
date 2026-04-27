# Phase 5: LAUNCHD `[macOS only]` (dashboard-mac variant)

LaunchAgent canon for any Bernard-controlled producer that feeds the dashboard. Captures the DASH-only naming rule (infra.md), the RunAtLoad review gate, and the nested-repo guard that the 2026-04-27 `.claude` near-miss made canonical.

Source spec: `~/.ship/dashboard-ship-route/goals/00-spec.md` §3.5.

## OUTPUT CONTRACT (enforced for owning strict-* agents)

- WRITE the full brief to `.ship/<feature>/05-launchd.md` via the Write tool.
- RETURN only: (a) artifact file path, (b) ≤15-line summary (plist label + RunAtLoad decision + heartbeat verification + allowlist entries).
- NEVER paste full §0-§N body in return message. The file on disk is source of truth.
- Phase not closed until `test -s .ship/<feature>/05-launchd.md` passes AND `launchctl print gui/$(id -u)/<label>` shows the loaded plist with `state = running` (or `state = waiting` if scheduled-only).

## Pre-slice

- Read `~/.claude/rules/infra.md` §LaunchAgent naming canon — DASH separator only, dot-separator forbidden.
- Read `~/.claude/CLAUDE.md` §Epistemic discipline — every "the plist is firing" claim cites `launchctl print` output, not file mtime.
- Confirm via `launchctl print gui/$(id -u)/<label>` for liveness, not by reading `~/Library/LaunchAgents/<file>.plist` mtime.

## §1. Plist + script + heartbeat = one atomic deploy unit (HARD RULE)

> **Don't ship plist alone (script missing → silent ENOENT loop). Don't ship script alone (no schedule). Phase 07 deploys all three together or none.**

Every dashboard-mac LaunchAgent ships with three artifacts:
1. `~/Library/LaunchAgents/com.bernard.<dash-name>.plist`
2. The script the plist calls (must exist + be executable)
3. The heartbeat path the script writes (must be writable + dashboard reads it per Phase 01 lineage)

The phase artifact lists all three paths and verifies all three exist.

## §2. DASH separator only (HARD RULE — infra.md canon)

```
✅ com.bernard.bigd-lint.plist
❌ com.bernard.bigd.lint.plist        ← FORBIDDEN, will silent-double-schedule
```

macOS launchd treats `com.bernard.bigd.lint` and `com.bernard.bigd-lint` as two separate units. Both run independent schedules. Neither knows about the other. The 2026-04-25 round-5 ship subagent's DOT-separator slip caused 48× firehose, 1200+ duplicate inbox briefs in 24h.

Enforcement: `~/.claude/hooks/launchagent_dup_guard.py` (PreToolUse on Write) blocks dot-separator plist names.

## §3. RunAtLoad rule (with explicit review gate)

> **Default**: `RunAtLoad=true` for *idempotent and cheap* daemons (data collectors, heartbeat writers, rsync pulls of small dirs).
>
> **Explicit review gate** for daemons with side effects: large file syncs (>100MB or >30s wall time), git pushes to remote, network-intensive ops, anything that changes external state.

Required spec field:

```
runs_at_load_safe: yes | no
runs_at_load_reason: <1-sentence justification>
```

Counter-example: a 3am-only large-sync plist with `RunAtLoad=true` would burn bandwidth on every login. Use `RunAtLoad=false` + accept that overnight-asleep misses a fire (acceptable for low-cadence daemons).

When `runs_at_load_safe: no`, the plist MUST omit `RunAtLoad` (or set it `false`) and the spec MUST declare what catches missed fires (sleep-recovery via `StartCalendarInterval` only schedules the next fire; it does not catch up).

## §4. Sleep-recovery + StartInterval gotchas

`StartInterval=300` (every 5 min) does NOT fire when Mac is asleep. On wake, only the next scheduled fire occurs — not a backfill. For dashboard-feeding producers, this means:

- After overnight sleep, the dashboard reads stale data until next fire.
- Phase 04 readiness gate may keep pill hidden if first-tick depends on a producer that hasn't fired post-wake yet.
- Mitigation: `RunAtLoad=true` (per §3) so wake reload triggers a fire — provided the daemon is `runs_at_load_safe: yes`.

For long-cadence daemons (`StartCalendarInterval` daily/hourly) that are NOT `runs_at_load_safe`:
- Accept that the dashboard will show stale data after wake until next scheduled fire.
- Document this in the §6 failure-mode contract.
- Optionally: separate `bigd-poke-on-wake.plist` that runs on `WakeFromSleep` event (rare, document if added).

## §5. Nested-repo guard (HARD RULE)

Before any auto-commit allowlist entry on a directory, verify the directory does NOT contain another `.git` inside. The 2026-04-27 `.claude` near-miss (23k-file root commit, reverted before push) is the canonical failure case.

Required check before adding `<dir>` to gitwatch / auto-commit allowlist:

```bash
find <dir> -maxdepth 4 -name ".git" -type d | head
```

Any match other than `<dir>/.git` itself = nested repo present. Refuse the allowlist entry. Add narrower allowlist paths instead.

The phase artifact MUST cite the output of this check for every allowlisted path.

## §6. Failure-mode contract (required content)

For the LaunchAgent shipped in this phase, declare:

| Failure | User-visible effect | Diagnosis |
|---|---|---|
| Plist not loaded | Heartbeat never updates → dashboard shows stale | `launchctl print gui/$(id -u)/<label>` (returns "Could not find service") |
| Script ENOENT | `launchctl print` shows recent `last exit code = 127` | `launchctl print` + check `<script-path>` |
| Script crashes | Heartbeat updates intermittently or stops | `tail /tmp/<label>.stderr` (set `StandardErrorPath` in plist) |
| Disk full | Heartbeat write fails silently | `df -h ~` |
| Slow disk wake | First post-wake fire takes >30s | Watch `launchctl print` `last exit timestamp` post-wake |

## §7. Plist canonical fields (required content)

Every plist shipped in Phase 05 MUST declare these fields in the artifact:

```
Label:                  com.bernard.<dash-name>
ProgramArguments:       [<absolute path to script>, <args...>]
StartInterval | StartCalendarInterval: <one of>
RunAtLoad:              <true|false> (per §3 review gate)
StandardOutPath:        /tmp/<label>.stdout
StandardErrorPath:      /tmp/<label>.stderr
WorkingDirectory:       <if needed; absent = $HOME>
ProcessType:            Background
KeepAlive:              <only if daemon must restart on crash; default absent>
```

Any non-canonical field (e.g. `EnvironmentVariables`, `LowPriorityIO`) requires a 1-sentence justification in the artifact.

## §8. Verification at phase close

```bash
# 1. Plist syntax valid
plutil -lint ~/Library/LaunchAgents/com.bernard.<name>.plist

# 2. Loaded into launchd
launchctl print gui/$(id -u)/com.bernard.<name>

# 3. Script executes manually (smoke test, do NOT run if §3 says runs_at_load_safe: no)
<script-path> <args...>

# 4. First fire happens
launchctl kickstart -k gui/$(id -u)/com.bernard.<name>

# 5. Heartbeat updated
stat -f '%m' <heartbeat-path>   # mtime within last cadence window
```

Paste all 5 outputs into `.ship/<slug>/experiments/05-launchd-log.md` with timestamps.

## §9. Inherited claims gate

When prior phase artifacts say "plist already loaded" / "daemon already running":

- Phase 05 MUST re-verify with `launchctl print gui/$(id -u)/<label>` THIS SESSION before skipping work. File mtime alone does NOT count.
- Document inherited claims + re-verification evidence under `## Inherited Claims Audit`.

## §10. Cross-references

- `~/.claude/rules/infra.md` §LaunchAgent naming canon
- `~/.claude/rules/pm-bot.md` §Liveness verdict protocol — same protocol applies for verifying any Mac LaunchAgent producer
- `~/.claude/skills/ship/phases/dashboard-mac/01-architecture.md` §4 — producer liveness verification feeds this phase
- `~/.claude/skills/ship/phases/dashboard-mac/07-deploy.md` — the final deploy step that loads the plist into the live launchd
- `~/.claude/hooks/launchagent_dup_guard.py` — write-time enforcement of §2
