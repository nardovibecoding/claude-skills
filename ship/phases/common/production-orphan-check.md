# Production Orphan / Zombie Check — Phase 4 LAND

Loaded for any route that deploys to a running host (bot, mcp, dashboard-mac, sometimes hook). Runs AFTER unit restart, BEFORE phase close.

Iron Law: a "deploy succeeded" verdict that leaves orphan workers behind is a silent regression. CPU goes red on the dashboard hours later, root cause invisible without `ps -ef`.

Source: 2026-04-29 London CPU 96% incident — 32 orphaned `git index-pack receive-pack` processes (PPID=1, etime > 47min) accumulated from interrupted ssh-pushes during prior deploys. Symptom showed up as VibeIsland Sync tab "CPU (London) maxed out" hours after the actual deploys completed. See `~/.claude/rules/infra.md` § Push-receiving host defense.

---

## OC-1 — Orphan inventory on deploy target

Run after the unit's restart settles (typically 10-15s post-`systemctl restart` or `launchctl kickstart`):

```bash
ssh "$DEPLOY_HOST" "ps -eo pid,ppid,etime,pcpu,stat,comm,args --sort=-etime | \
  awk 'NR==1 || (\$2==1 && \$3 ~ /[0-9]+:[0-9]+:[0-9]+/) || \$5 ~ /Z/'"
```

Read the output. Apply suspect-list:

| pattern | classification |
|---|---|
| `git index-pack`, `git receive-pack` | orphan from interrupted push — **BLOCK** |
| `<defunct>` (zombie, STAT=Z) | parent failed to reap — **BLOCK** |
| `node` / `python` / `bun` with PPID=1, etime>10min, NOT the unit MainPID | **BLOCK** |
| `sshd: <user> [priv]`, etime>1h, no client connection | **WARN**, not block |
| systemd children, etime same as host uptime | expected, ignore |

Block path → write `experiments/orphan-check-blocked.md` with the offending PIDs + suggest cleanup commands. Phase 4 cannot close.

Warn path → log `experiments/orphan-check.md`, allow phase close, surface the warning in the verdict block.

Clean path → log `experiments/orphan-check.md` with `OK: 0 orphans, 0 zombies` and proceed.

---

## OC-2 — Load-divergence sanity check

After orphan inventory, sanity-check the host's reported load:

```bash
ssh "$DEPLOY_HOST" "uptime; nproc; ps -eo pcpu --no-headers | awk '{s+=\$1} END{print s}'"
```

If `load_avg_1min > nproc * 1.5` AND `sum(pcpu) < load_avg_1min * 50`, the host has hidden background work (likely D-state / iowait / orphan accumulation NOT yet caught by OC-1's etime threshold). Mirror the verdict to the dashboard owner with diagnostics.

This is the SAME divergence pattern as `/debug performance` detector P3. The two should produce equivalent verdicts on the same host snapshot. If they diverge, escalate.

---

## OC-3 — Cleanup pre-flight (when route deploys via ssh-push)

For routes that use `git push` to a bare repo on the deploy host (bot route on London, etc):

Before pushing, the deploy script SHOULD set:

```bash
# Client-side (run in deploy script)
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 "$HOST" \
  "cd '$BARE_REPO_PATH' && git config receive.transferIdleTimeout 300"
```

The `transferIdleTimeout` makes the server-side `git index-pack` self-terminate after 5min of no progress, preventing the 47-minute orphan accumulation Bernard observed. The ssh keepalive options ensure dead-peer detection in 90s (3 × 30s) so TCP teardown propagates.

If the deploy script does NOT set these, log a warning into `experiments/orphan-check.md` recommending the upgrade.

---

## Wiring

Each route's `phases/<route>/04-land.md` that deploys to a remote host MUST include:

```markdown
## Production Orphan Check (universal)

Run `~/.claude/skills/ship/phases/common/production-orphan-check.md` OC-1 + OC-2 against the deploy target. Apply BLOCK / WARN / CLEAN logic as documented. Phase 4 cannot close on BLOCK.
```

Routes covered today: `bot/04-land.md`, `dashboard-mac/04-land.md` (when DMG is auto-installed), `mcp/04-land.md`. Skill / hook / doc routes are local-only and do NOT need this check.
