---
name: remind
description: Set a timer reminder that alerts in the terminal. Usage: /remind 16:55 電話 or /remind 30m check deploy
---

Set a reminder that prints an alert in this terminal at the specified time.

Supports two formats:
- **Absolute time**: `/remind 16:55 電話要接` — alerts at 16:55 HKT
- **Relative time**: `/remind 30m check deploy` — alerts in 30 minutes

Steps:
1. Parse the time argument (HH:MM for absolute, Nm/Nh for relative)
2. Calculate seconds until target time (use HKT timezone: `TZ=Asia/Hong_Kong`)
3. Run in background: `(sleep SECONDS && echo -e "\n\n⏰⏰⏰ 提醒：MESSAGE ⏰⏰⏰\n") &`
4. Confirm: "Timer set: TIME HKT — MESSAGE"
