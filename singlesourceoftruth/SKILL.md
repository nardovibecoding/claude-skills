---
name: singlesourceoftruth
description: |
  Unified Mac-VPS sync via GitHub. Replaces mactovps and vpstomac.
  Everything flows through git — code, memory, skills, config.

  USE FOR:
  - "deploy", "push to vps", "sync to server", "mactovps"
  - "switch to mac", "run locally", "vpstomac"
  - "sync", "sync everything", "single source of truth"
  - After any code/skill/config change that needs to reach the other side
user-invocable: true
---

# Single Source of Truth

All state flows through GitHub. No rsync. No scp. Git is the bus.

## Architecture

```
Mac ──push──> GitHub <──pull── VPS
Mac <──pull── GitHub ──push──> VPS (when TG Claude commits)
```

### What syncs and how

| What | Repo | Mac location | VPS location | Auto-sync |
|------|------|-------------|-------------|-----------|
| Bot code + memory | telegram-claude-bot | ~/telegram-claude-bot/ | ~/telegram-claude-bot/ | VPS pulls every 1 min |
| CLAUDE.md | telegram-claude-bot | synced to ~/.claude/projects/ | synced to ~/.claude/projects/ | Via sync script |
| Skills | claude-skills | ~/.claude/skills/ | ~/.claude/skills/ | Every 10 min both sides |
| MCP config | sync_claude_config.py | ~/.claude/settings.json | ~/.claude/settings.json | Every 10 min |
| Cookies | rsync (only exception) | ~/telegram-claude-bot/ | ~/telegram-claude-bot/ | On refresh |

### What does NOT sync (stays local)

| What | Why |
|------|-----|
| .env | Secrets — never in git |
| *.db | SQLite memory DBs — platform-specific |
| venv/ | Python virtual env — platform-specific |
| .playwright_profile/ | Browser sessions — machine-specific |
| __pycache__/ | Compiled bytecode |

## Server details

- VPS: 157.180.28.14 (Helsinki, Hetzner CX23)
- User: bernard
- Service: telegram-bots (systemd)

## Commands

### Deploy Mac → VPS

When you made changes on Mac and want them live on VPS:

```bash
# 1. Commit and push code
cd ~/telegram-claude-bot && git add -A && git commit -m "description" && git push origin main

# 2. Commit and push skills (if changed)
cd ~/.claude/skills && git add -A && git diff --cached --quiet || git commit -m "skill update" && git push origin main

# 3. VPS pulls automatically every 1 min, but to force immediate:
ssh bernard@157.180.28.14 "cd ~/telegram-claude-bot && git pull --ff-only origin main"

# 4. Restart bots
ssh bernard@157.180.28.14 "sudo systemctl restart telegram-bots"

# 5. Verify
ssh bernard@157.180.28.14 "sleep 3 && sudo systemctl status telegram-bots --no-pager | head -5"
```

### Pull VPS → Mac

When TG Claude made changes on VPS and you want them on Mac:

```bash
# 1. Pull code
cd ~/telegram-claude-bot && git pull --ff-only origin main

# 2. Pull skills
cd ~/.claude/skills && git pull --ff-only origin main

# 3. Sync CLAUDE.md to local project
~/sync_claude_memory.sh
```

### Switch to Mac (stop VPS, run locally)

```bash
# 1. Stop VPS bots
ssh bernard@157.180.28.14 "sudo systemctl stop telegram-bots"

# 2. Verify stopped
ssh bernard@157.180.28.14 "pgrep -af 'run_bot.py|admin_bot' || echo 'All stopped'"

# 3. Pull latest from both repos
cd ~/telegram-claude-bot && git pull --ff-only origin main
cd ~/.claude/skills && git pull --ff-only origin main

# 4. Sync cookies (only thing not in git)
rsync -az bernard@157.180.28.14:~/telegram-claude-bot/twitter_cookies.json ~/telegram-claude-bot/

# 5. Start locally
cd ~/telegram-claude-bot && ./start_all.sh

# 6. Verify
sleep 5 && pgrep -af 'run_bot.py|admin_bot'
```

### Switch back to VPS

```bash
# 1. Stop local bots
pkill -f 'start_all.sh' 2>/dev/null
pkill -f 'run_bot.py' 2>/dev/null
pkill -f 'admin_bot' 2>/dev/null

# 2. Push any local changes
cd ~/telegram-claude-bot && git add -A && git diff --cached --quiet || git commit -m "Mac changes before VPS switch" && git push origin main
cd ~/.claude/skills && git add -A && git diff --cached --quiet || git commit -m "Skill changes" && git push origin main

# 3. VPS pulls and starts
ssh bernard@157.180.28.14 "cd ~/telegram-claude-bot && git pull --ff-only origin main && sudo systemctl start telegram-bots"

# 4. Verify
ssh bernard@157.180.28.14 "sleep 3 && sudo systemctl status telegram-bots --no-pager | head -5"
```

## Conflict resolution

If git pull fails with merge conflict:
```bash
# Check what diverged
git log --oneline HEAD..origin/main
git diff HEAD origin/main

# Usually: Mac and VPS edited different files → safe to merge
git merge origin/main

# If same file edited on both sides → manual resolve needed
# Open the conflicted file, fix the markers, then:
git add <file> && git commit -m "Resolve merge conflict"
```

## Important rules

- NEVER use scp to deploy code — it bypasses git and overwrites commits
- NEVER run bots on both Mac AND VPS simultaneously — same token = Telegram Conflict error
- Always pull before push — `git pull --ff-only` first
- Cookies are the ONLY thing that uses rsync (not in git for security)
- Skills repo auto-syncs every 10 min on both sides — manual push only needed for urgency
