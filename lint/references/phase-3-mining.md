# Phase 3: JSONL mining + cleanup

Extract knowledge from expiring session logs before deletion.

1. Find JSONL files older than 7 days (Mac: `~/.claude/projects/*/`, VPS via SSH)
2. For each JSONL: extract head 100 + tail 300 lines, grep for text content
3. Look for: architecture decisions, new features, bug root causes, user corrections, cron changes, config changes
4. Cross-check against existing memory — skip duplicates
5. Save genuinely new findings to memory files
6. Delete scanned JSONL files (>7 days old)

Skip Phase 3 for `/lint --quick`.
Unattended mode runs identically — already non-interactive.
