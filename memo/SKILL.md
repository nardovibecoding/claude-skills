---
name: memo
description: |
  Show the most recent /memo entries (both pending + already-archived).
  Use to verify a memo arrived from TG admin_bot, or to re-read what you just sent.
  Triggers: "/memo", "last memo", "check memo", "did my memo save", "show memos", "recheck memo".
user_invocable: true
---

# Memo Recheck

Shows the 5 most recent memos from local disk (Mac), covering both:
- `~/telegram-claude-bot/memo/pending/` — pushed from VPS but not yet shown by `memo_display.py` hook
- `~/telegram-claude-bot/memo/done/` — already shown + archived

## Steps

1. **Pull latest**:
   ```bash
   cd ~/telegram-claude-bot && git pull --ff-only --quiet 2>/dev/null
   ```

2. **List 5 newest memos across both dirs**:
   ```bash
   ls -t ~/telegram-claude-bot/memo/pending/*.md ~/telegram-claude-bot/memo/done/*.md 2>/dev/null | head -5
   ```

3. **Show each one compactly** — for each file, print:
   - timestamp (from filename `YYYY-MM-DD_HHMMSS.md`)
   - status: `PENDING` (in pending/) or `done` (in done/)
   - body (content after frontmatter)

4. **Output format**:
   ```
   | When (HKT)        | Status  | Content |
   |-------------------|---------|---------|
   | 04-20 22:20:50    | done    | https://x.com/_avichawla/... |
   | 04-20 22:20:36    | done    | test |
   | 04-20 22:20:13    | done    | https://x.com/_avichawla/... |
   ```
   File timestamps are UTC; convert to HKT (UTC+8) for display.

5. **If no files in pending/ or done/**: fall back to git:
   ```bash
   cd ~/telegram-claude-bot && git log --all --oneline --grep='memo:' -10
   ```

## Notes

- Memos arrive automatically via `memo_display.py` hook on every UserPromptSubmit — this skill is for manual recheck only.
- `done/` never gets cleared automatically, so history persists. If it grows large (>500 files) consider `mv done/old_* archive/` but not needed at current rate.
- If VPS push is lagging (>5 min) and expected memo is missing, check `ssh hel 'ls -t ~/telegram-claude-bot/memo/pending/*.md | head -3'` for VPS-side unpushed files.
