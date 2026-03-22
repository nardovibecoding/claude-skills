# Home In — Resume session from phone

When triggered, pull latest from VPS, sync everything, and auto-continue TG work.

Steps:
1. Pull latest code + memory: `cd ~/telegram-claude-bot && git pull origin main --ff-only`
2. Sync cookies from VPS: `scp bernard@157.180.28.14:~/telegram-claude-bot/twitter_cookies.json ~/telegram-claude-bot/`
3. Check for pending resume file: `ssh bernard@157.180.28.14 "cat ~/.claude/projects/-home-bernard/memory/pending_resume.txt 2>/dev/null"`
4. If a session ID is found:
   - Read the last 100 lines of that session's JSONL on VPS: `ssh bernard@157.180.28.14 "tail -100 ~/.claude/projects/-home-bernard-telegram-claude-bot/<session_id>.jsonl 2>/dev/null"`
   - Extract the text content and summarize what was discussed/done
   - Present the summary: "Here's what you were working on via TG: [summary]"
   - Then AUTOMATICALLY continue the work — don't ask, just pick up where TG left off
   - If TG session had unfinished tasks, start working on them immediately
   - Clean up: `ssh bernard@157.180.28.14 "rm -f ~/.claude/projects/-home-bernard/memory/pending_resume.txt"`
5. If no pending session, say "Memory synced from VPS. No pending TG session."
