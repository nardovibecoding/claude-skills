---
name: mactovps
description: |
  Deploy code changes to the Hetzner VPS and restart bots.

  USE FOR:
  - When user says "deploy", "push to vps", "sync to server"
  - After code changes that need to go live
  - When user wants to restart bots on the VPS
user_invocable: true
---

# VPS Deploy

Deploy local code to the Hetzner VPS and restart bots.
IMPORTANT: Always pull VPS changes first to avoid overwriting TG-made edits.

## Server details
- IP: 157.180.28.14 (Helsinki, Hetzner CX23)
- User: bernard
- Project: ~/telegram-claude-bot/
- Service: telegram-bots (systemd)

## Steps

0. **Sync Claude memory** (bidirectional, before deploy):
```bash
/Users/bernard/sync_claude_memory.sh
```

1. **Pull VPS changes first** (auto-commit VPS state, then check for diffs):
```bash
# Auto-commit any VPS changes
ssh bernard@157.180.28.14 "cd ~/telegram-claude-bot && git add -A && git diff --cached --quiet || git commit -m 'VPS auto-commit before deploy'"

# Pull VPS code to a temp dir and diff against Mac
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.playwright_profile' --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' --exclude='.git' --exclude='.env' --exclude='twitter_cookies.json' --dry-run bernard@157.180.28.14:~/telegram-claude-bot/ ~/telegram-claude-bot/ 2>&1
```
**Review the dry-run output.** If VPS has changes Mac doesn't (files that would be overwritten), pull them first:
```bash
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.playwright_profile' --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' --exclude='.git' --exclude='.env' --exclude='twitter_cookies.json' bernard@157.180.28.14:~/telegram-claude-bot/ ~/telegram-claude-bot/
```
Then review the diff with `git diff` on Mac. Merge manually if needed, commit on Mac.

2. **Push code to VPS** (excludes venv, pycache, playwright profile, db files):
```bash
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.playwright_profile' --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' --exclude='.git' --exclude='.env' --exclude='twitter_cookies.json' ~/telegram-claude-bot/ bernard@157.180.28.14:~/telegram-claude-bot/
```

3. **Restart bots**:
```bash
ssh bernard@157.180.28.14 "sudo systemctl restart telegram-bots"
```

4. **Verify**:
```bash
ssh bernard@157.180.28.14 "sudo systemctl status telegram-bots --no-pager -l | head -20"
```

5. **Commit on both sides** (keep git in sync):
```bash
cd ~/telegram-claude-bot && git add -A && git commit -m "Deploy sync"
ssh bernard@157.180.28.14 "cd ~/telegram-claude-bot && git add -A && git commit -m 'Deploy sync'"
```
