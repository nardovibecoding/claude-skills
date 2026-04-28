---
name: singlesourceoftruth
description: |
  Mac ↔ Hel ↔ London sync. Code via GitHub, memory + NardoWorld via self-hosted bare git on Hel. Cookies the only rsync exception.
  Triggers: "deploy", "push to vps", "sync", "mactovps", "vpstomac", "sync to server", "single source of truth".
  NOT FOR: git commits (just use git), skill installs (use extractskill).
  Produces: synced state across Mac, Hel, London.
user-invocable: true
---

# Single Source of Truth

All state flows through git. No rsync (except cookies). No scp. Git is the bus.

## Architecture

The full SSOT route map lives at `~/NardoWorld/meta/references/reference-memory-sync.md` (verified live; updated whenever sync architecture changes). This skill triggers on sync/deploy intents — see commands below. The canonical doc is the source of truth for which path is the latest version of any file.

## Hosts

- **Mac** — primary dev, Claude Code sessions
- **Hel** (157.180.28.14, user=bernard) — Kalshi bots + memory/NardoWorld bare repos. Service: `telegram-bots` systemd unit.
- **London** (78.141.205.30, user=pm) — Polymarket + Manifold bots (pm-london systemd service).

## Commands

### Deploy Mac → Hel (code + skills)

```bash
cd ~/telegram-claude-bot && git add -A && git commit -m "..." && git push origin main
cd ~/.claude/skills && git add -A && git diff --cached --quiet || git commit -m "..." && git push origin main
ssh bernard@hel "cd ~/telegram-claude-bot && git pull --ff-only origin main"
ssh bernard@hel "sudo systemctl restart telegram-bots"
ssh bernard@hel "sleep 3 && sudo systemctl status telegram-bots --no-pager | head -5"
```

### Memory / NardoWorld sync (self-hosted bare repo)

Fire-and-forget. Mac Stop hook (`memory_auto_commit.py`) commits on session end; Hel cron pulls every 5 min.

**Manual push (Mac → Hel):**
```bash
cd ~/.claude/projects/-Users-bernard/memory && git add -A && git diff --cached --quiet || git commit -m "manual save" && git push hel main
cd ~/NardoWorld && git add -A && git diff --cached --quiet || git commit -m "manual save" && git push hel main
```

**Verify Hel got it:**
```bash
ssh bernard@hel "cd ~/.claude/projects/-home-bernard/memory && git log --oneline -3"
ssh bernard@hel "cd ~/NardoWorld && git log --oneline -3"
```

### London deploy (PM bots)

London pulls `telegram-claude-bot` from GitHub — push the bot repo and London's cron does the rest.

```bash
cd ~/telegram-claude-bot && git push origin main
ssh pm@london "sudo systemctl restart pm-london"  # if immediate restart needed
ssh pm@london "sudo systemctl status pm-london --no-pager | head -8"
```

**Systemd-as-truth check** (per CLAUDE.md HARD RULE): before asserting London's code path, always:
```bash
ssh pm@london "systemctl cat pm-london | grep -E 'User|WorkingDirectory|ExecStart'"
```

### Pull Hel → Mac (TG Claude changes)

```bash
cd ~/telegram-claude-bot && git pull --ff-only origin main
cd ~/.claude/skills && git pull --ff-only origin main
cd ~/.claude/projects/-Users-bernard/memory && git pull --ff-only hel main
cd ~/NardoWorld && git pull --ff-only hel main
```

### Switch to Mac (stop VPS, run locally)

Hel = Kalshi only. London = Poly/Manifold only. When switching to Mac:
```bash
ssh bernard@hel "sudo systemctl stop telegram-bots"
ssh pm@london "sudo systemctl stop pm-london"
ssh bernard@hel "pgrep -af 'run_bot.py|admin_bot' || echo 'Hel stopped'"
ssh pm@london "pgrep -af 'pm_|polymarket' || echo 'London stopped'"
cd ~/telegram-claude-bot && git pull --ff-only origin main
cd ~/.claude/skills && git pull --ff-only origin main
rsync -az bernard@hel:~/telegram-claude-bot/twitter_cookies.json ~/telegram-claude-bot/
cd ~/telegram-claude-bot && ./start_all.sh
sleep 5 && pgrep -af 'run_bot.py|admin_bot'
```

### Switch back to VPS

```bash
pkill -f 'start_all.sh' 2>/dev/null; pkill -f 'run_bot.py' 2>/dev/null; pkill -f 'admin_bot' 2>/dev/null
cd ~/telegram-claude-bot && git add -A && git diff --cached --quiet || git commit -m "Mac changes before VPS switch" && git push origin main
cd ~/.claude/skills && git add -A && git diff --cached --quiet || git commit -m "Skill changes" && git push origin main
ssh bernard@hel "cd ~/telegram-claude-bot && git pull --ff-only origin main && sudo systemctl start telegram-bots"
ssh pm@london "cd ~/telegram-claude-bot && git pull --ff-only origin main && sudo systemctl start pm-london"
ssh bernard@hel "sleep 3 && sudo systemctl status telegram-bots --no-pager | head -5"
ssh pm@london "sleep 3 && sudo systemctl status pm-london --no-pager | head -5"
```

## Conflict resolution

**Memory / NardoWorld (Hel bare repo):** `git pull --ff-only hel main` aborts on divergence. Inspect with `git log --oneline hel/main..HEAD` and `git log --oneline HEAD..hel/main`. Usually Mac vs Hel edited different files → `git merge hel/main`. Same-file conflict → manual resolve.

**Code repos (GitHub):** same pattern, swap `hel` for `origin`.

**NEVER:** `git reset --hard` without confirming the other side's commits are preserved somewhere.

## --ff-only silent-abort guard

`vps_sync.sh` section 5 wraps `git pull --ff-only` with exit-code check. If pull aborts due to divergence, the script fails loud (no silent skip). Do NOT weaken this.

## Important rules

- NEVER use `scp` to deploy code — bypasses git, overwrites commits
- NEVER run bots on Mac AND VPS simultaneously — same token = Telegram Conflict error
- Always `git pull --ff-only` first, then push
- Cookies are the ONLY rsync exception (twitter_cookies.json, not in git for security)
- After code changes: auto commit+push+vpssync per rule #7 (no manual prompt)
- Skills + hooks sync every 10 min both sides — manual push only for urgency
- Hel cron `*/5 min` auto-commits + pushes memory/NardoWorld; rarely need manual push
