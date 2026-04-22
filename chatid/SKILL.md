---
name: chatid
description: Session ID for resuming elsewhere.
user_invocable: true
---

# Chat ID

Show the current session ID and instructions to resume on Telegram.

1. Find the current session ID by reading the conversation JSONL file path from the project directory.
2. The session ID is the filename (without .jsonl) of the active conversation file in `~/.claude/projects/*/`.
3. Display it clearly and give the TG resume command:

```
/session <session_id>
```
