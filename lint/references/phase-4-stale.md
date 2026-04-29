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
8. **Project-root markdown stale-prose** (zero-relative-time scan): for each project P under `~/NardoWorld/projects/*/` read `P/CLAUDE.md`, `P/AGENTS.md`, `P/README.md` if present. Run zero-relative-time grep:
   ```bash
   grep -nE '今天|昨天|刚刚|最近|上周|currently|for now|the new approach|today|yesterday|recently' "$f"
   ```
   Each hit without an adjacent ISO date (`YYYY-MM-DD` within ±2 lines) becomes a stale-prose finding. Memo path: `$MEMO_DIR/lint-stale-prose-$TODAY.md` — format: `- <file>:<line>: <matched-phrase> — <surrounding context>`.
9. **Cross-project sync** via file-map dependency edges: parse `~/NardoWorld/projects/*/file-map.md` for dependency edges (project A's "depends_on" / "consumes" / "imports from" entries pointing at project B). For each edge A→B, when project B has had recent commits (last 7d) touching exported symbols (API endpoints, env-var names, DB table schemas), grep project A's docs for those symbol strings. Hits = potential staleness. Memo: `$MEMO_DIR/lint-cross-project-$TODAY.md`. If no machine-readable edge format, degrade to plain symbol-string grep across all projects.

## Unattended variant

Auto-fix simple ones: renamed paths (file moved but path string wrong), schedule drift (crontab actual time differs from memory string by ≤30 min).
Write memo for complex ones (service removed, architecture changed, contradicts current code):
`$MEMO_DIR/lint-stale-memory-$TODAY.md`
Format: `- <memory-file>: <stale-claim> → <suggested-fix-or-question>`
