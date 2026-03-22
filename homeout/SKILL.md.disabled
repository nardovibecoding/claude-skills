# Home Out — Transfer session to phone

When triggered, sync everything to VPS so TG Claude auto-continues.

Steps:
1. Git commit any uncommitted memory changes: `cd ~/telegram-claude-bot && git add memory/ && git diff --cached --quiet || git commit -m "memory: sync before homeout" && git push origin main`
2. Sync cookies to VPS: `scp ~/telegram-claude-bot/twitter_cookies.json bernard@157.180.28.14:~/telegram-claude-bot/`
3. Trigger VPS git pull: `ssh bernard@157.180.28.14 "cd ~/telegram-claude-bot && git pull origin main --ff-only"`
4. Find current session ID: get the basename (without .jsonl) of the most recent .jsonl in ~/.claude/projects/-Users-bernard/
5. Write pending resume file on VPS: `ssh bernard@157.180.28.14 "echo '<session_id>' > ~/.claude/projects/-home-bernard/memory/pending_resume.txt"`
6. Also write a summary of what you were working on in this session:
   `ssh bernard@157.180.28.14 "cat > ~/.claude/projects/-home-bernard/memory/pending_summary.txt << 'EOF'
   <brief summary of current work: what was done, what's in progress, what's next>
   EOF"`
7. Send notification to Telegram via ~/send_session_to_tg.sh with the summary
8. Confirm: "Synced. TG Claude will auto-continue when you message it."
