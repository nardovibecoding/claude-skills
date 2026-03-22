---
name: home
description: |
  Transfer session between Mac and phone. /home out = transfer to phone (TG).
  /home in = resume on Mac from phone. Triggers: "homeout", "homein",
  "transfer to phone", "resume from phone", "switch to mobile".
---

# Home — Session Transfer

## /home out (transfer to phone)
1. Save current session context to a summary
2. Send summary + session ID to Telegram admin chat
3. User continues conversation on phone via TG bot

## /home in (resume on Mac)
1. Read the TG session summary
2. Restore context from the phone conversation
3. Continue working on Mac with full context

Usage: `/home out` or `/home in`
