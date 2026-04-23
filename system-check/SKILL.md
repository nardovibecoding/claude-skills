---
name: system-check
description: Mac + Hel + London health snapshot. Uses systemctl cat (systemd-as-truth), checks CPU/disk/mem, flags stale-code drift. Triggers "system check", "health check", "status all".
---

Run a comprehensive health check across Mac, Hel (Kalshi), and London (Poly/Manifold). Parallel where possible.

## Hel VPS (ssh bernard@hel) — Kalshi stack

1. **Systemd truth**: `systemctl cat telegram-bots | grep -E 'User|WorkingDirectory|ExecStart'` — verify live path matches deploy target per HARD RULE
2. **Git drift**: `cd ~/telegram-claude-bot && git rev-list --count HEAD..origin/main` — 0 = in sync; N>0 = stale code, service will run old version
3. **Bot processes**: `pgrep -fa "run_bot|admin_bot"` — daliu/sbf/admin alive?
4. **Services**: `systemctl is-active telegram-bots xhs-mcp douyin-mcp` — all active?
5. **MCP health**: `curl -s localhost:18060/health && curl -s localhost:18070/health`
6. **Heartbeat**: `cat .admin_heartbeat` — age < 60s? (use `date +%s - $(cat .admin_heartbeat)`)
7. **CPU**: `top -bn1 | head -5` — watch for 100% (LLM-429 hot-loop signature)
8. **Disk**: `df -h /` — usage %
9. **Memory**: `free -m`
10. **Docker**: `docker ps` — RSSHub running?
11. **Cookie age**: `stat -c %Y twitter_cookies.json` — diff vs now, flag >24h
12. **Recent errors**: `grep -iE 'error|traceback' /tmp/start_all.log | tail -5`

## London VPS (ssh pm@london) — Poly/Manifold stack

1. **Systemd truth**: `systemctl cat pm-london | grep -E 'User|WorkingDirectory|ExecStart'` — match deploy target
2. **Git drift**: `cd ~/telegram-claude-bot && git rev-list --count HEAD..origin/main` — 0 = synced
3. **Service**: `systemctl is-active pm-london`
4. **Bot processes**: `pgrep -fa 'pm_|polymarket|manifold'`
5. **CPU**: `top -bn1 | head -5` — 100% = possible LLM 429 hot-loop (pm-bot.md rule)
6. **Disk**: `df -h /`
7. **Memory**: `free -m`
8. **Recent errors**: `journalctl -u pm-london --since '1 hour ago' | grep -iE 'error|traceback' | tail -5`
9. **Poly clobStream activity**: `grep 'clobStream' /var/log/pm-london/*.log | tail -3` (or equivalent log path)

## Mac

1. **Voice daemon**: `pgrep -f voice_daemon`
2. **Recording indicator**: `pgrep -f recording_indicator`
3. **CPU**: `top -l 1 | head -10 | grep 'CPU usage'`
4. **Disk**: `df -h / | tail -1`
5. **Git memory sync**: `cd ~/.claude/projects/-Users-bernard/memory && git rev-list --count HEAD..hel/main 2>/dev/null` — confirm Hel got latest
6. **NardoWorld sync**: `cd ~/NardoWorld && git rev-list --count HEAD..hel/main 2>/dev/null`
7. **ComfyUI**: `curl -s localhost:8188/system_stats` (if running)

## Output format

Status table with ✅/❌/⚠️ per item. Group by host (Hel / London / Mac). Highlight:
- ❌ systemd path ≠ deploy target → HARD fail (stale-code drift, per lesson_systemd_truth_drift)
- ❌ git drift ≥ 1 commit → stale code running
- ⚠️ CPU > 90% sustained → LLM 429 hot-loop likely
- ⚠️ Disk > 90% → purge JSONL tails
- ⚠️ Heartbeat > 60s → bot wedged

If any ❌: report loudly first, then rest of table.
