---
name: vpstomac
description: |
  Migrate bots from VPS back to Mac and run locally.

  USE FOR:
  - When user says "switch to mac", "run locally", "vpstomac"
  - When VPS is down or user wants to develop/test locally
  - When migrating back from VPS to Mac
user_invocable: true
---

# VPS to Mac Migration

Stop bots on VPS, sync latest state back, and start locally on Mac.

## Server details
- VPS IP: 157.180.28.14 (Helsinki, Hetzner CX23)
- VPS User: bernard
- VPS Project: ~/telegram-claude-bot/
- Mac Project: ~/telegram-claude-bot/
- Service: telegram-bots (systemd)

## Steps

1. **Stop bots on VPS**:
```bash
ssh bernard@157.180.28.14 "sudo systemctl stop telegram-bots"
```

2. **Verify VPS bots stopped**:
```bash
ssh bernard@157.180.28.14 "pgrep -af 'run_bot.py|admin_bot.py'" || echo "All stopped"
```

3. **Sync state/data back from VPS** (cookies, caches, sessions — excludes venv, db, playwright):
```bash
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.playwright_profile' --exclude='*.db' --exclude='.git' bernard@157.180.28.14:~/telegram-claude-bot/ ~/telegram-claude-bot/
```

4. **Start bots locally on Mac**:
```bash
cd ~/telegram-claude-bot && ./start_all.sh
```

5. **Verify local bots running**:
```bash
sleep 5 && pgrep -af 'run_bot.py|admin_bot.py'
```

## Notes
- Same Telegram bot token cannot run on two machines simultaneously — always stop VPS first.
- Twitter cookies (`twitter_cookies.json`) are synced back so local bots can use them.
- `.db` files excluded from sync to avoid overwriting local memory DBs with VPS copies.
- To go back to VPS later, use `/vps`.
