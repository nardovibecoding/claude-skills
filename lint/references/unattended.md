# /lint --unattended (cron-safe)

If invoked as `/lint --unattended` (e.g. from a cron wrapper), skip ALL user prompts.
Write decisions-needed as memo files to `~/telegram-claude-bot/memo/pending/` for resolution
at next interactive session. Auto-fix obvious issues; defer ambiguous ones.

```bash
MEMO_DIR="$HOME/telegram-claude-bot/memo/pending"
TODAY=$(date '+%Y-%m-%d')
```

## Phases run (in order)

For each phase, follow the regular phase reference file but use the "Unattended variant" subsection where present:

1. **Phase 1** — `references/phase-1-scan.md` (run as-is with `--fix`)
2. **Phase 1.5** — `references/phase-1.5-dedup.md` (Unattended variant — write memo, no deletes)
3. **Phase 2** — `references/phase-2-audit.md` (Unattended variant — auto-fix obvious, memo for complex)
4. **Phase 3** — `references/phase-3-mining.md` (already non-interactive, no change)
5. **Phase 4** — `references/phase-4-stale.md` (Unattended variant — auto-fix simple, memo for complex)
6. **Phase 5a** — `references/phase-5-promote.md` (Unattended 5a section — dry-run only, write memo)
7. **Phase 5b** — `references/phase-5-promote.md` (Unattended 5b section — score ≥7 → memo)

Phase 6 + Phase 7 SKIPPED in unattended (interactive review required for skill cleanup + code deletion).

## End of run: git commit

After all phases complete:

**memory dir** (`~/.claude/projects/-Users-bernard/memory/`):
- Check if git repo: `git -C "$MEMORY_DIR" rev-parse --is-inside-work-tree 2>/dev/null`
- If NOT a git repo: log warning, skip. (Currently not a git repo — skip.)
- If IS a git repo: `git -C "$MEMORY_DIR" add -A && git -C "$MEMORY_DIR" commit -m "lint --unattended: $TODAY" && git -C "$MEMORY_DIR" push`

**NardoWorld** (`~/NardoWorld/`):
- Always commit if changes exist: `git -C ~/NardoWorld add -A && git -C ~/NardoWorld commit -m "lint --unattended: $TODAY"`
- No remote → skip push, log: `WARN: NardoWorld has no remote, skipping push`
