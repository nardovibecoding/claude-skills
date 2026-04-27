# Phase 4: Stale memory detection + wiki migration

1. Read all memory files in `~/.claude/projects/-Users-bernard/memory/`
2. Verify claims against current state:
   - Cron/systemd schedules: `crontab -l` / `systemctl --user list-timers` on VPS vs what memory says
   - File paths: do referenced files still exist?
   - Process names: do referenced services still run?
   - Feature descriptions: does the code still work that way?
3. Check file path references:
   ```bash
   grep -roE '[a-zA-Z0-9_/.-]+\.(ts|js|py|md|json|yaml|yml|sh)' "$MEMORY_DIR/"*.md | while read f; do
     [ ! -f "$f" ] && echo "STALE: $f"
   done
   ```
4. Auto-fix simple ones (wrong schedule times, renamed files)
5. Flag complex ones for user decision
6. Consolidate overlapping topic files (merge into broader file)
7. **Memory → wiki migration**: Before deleting any stale/obsolete memory entry, check if it contains valuable knowledge (architecture decisions, historical context, lessons learned). If yes, create a NardoWorld wiki article in the appropriate category (operations/, products/, lessons/) preserving the knowledge permanently. Only then remove from working memory.

## Unattended variant

Auto-fix simple ones: renamed paths (file moved but path string wrong), schedule drift (crontab actual time differs from memory string by ≤30 min).
Write memo for complex ones (service removed, architecture changed, contradicts current code):
`$MEMO_DIR/lint-stale-memory-$TODAY.md`
Format: `- <memory-file>: <stale-claim> → <suggested-fix-or-question>`
