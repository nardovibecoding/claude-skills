---
name: lint
description: |
  Unified system maintenance — wiki integrity, memory health, JSONL mining, skill audit, pattern promotion.
  Combines former lint + memory-maintenance + skillcleaning into one skill.
  Triggers: "lint", "memory maintenance", "clean memory", "stale memory", "mine sessions", "promote patterns", "skill cleaning", "audit skills", "unused skills".
  NOT FOR: editing specific memory files (just edit), installing skills (use extractskill), security scans (use skill-security-auditor).
user-invocable: true
---
<lint>
Run unified maintenance: wiki integrity + memory health + JSONL mining + promotion.

## --unattended mode

If invoked as `/lint --unattended` (e.g. from a cron wrapper), skip ALL user prompts.
Write decisions-needed as memo files to `~/telegram-claude-bot/memo/pending/` for resolution
at next interactive session. Auto-fix obvious issues; defer ambiguous ones.

MEMO_DIR="$HOME/telegram-claude-bot/memo/pending"
TODAY=$(date '+%Y-%m-%d')

### Phase 1 (unattended): Deterministic scan
Run as-is: `cd ~/llm-wiki-stack/lint/scripts && python3 wiki_lint.py --fix`

### Phase 1.5 (unattended): Semantic dedup — NO deletions
DO NOT delete or archive any file. Instead:
1. Collect every `semantic_dedup` warning pair from Phase 1 output.
2. For each pair: read both files, extract title + 1-line summary.
3. Write a single memo file: `$MEMO_DIR/lint-dedup-pairs-$TODAY.md`
   Format per pair:
   ```
   ## Pair N
   **File A**: <title> — <1-line summary>
   **File B**: <title> — <1-line summary>
   **Recommended**: [A|B|M|S] — <reason>
   Pick: [A] [B] [M] [S]
   ```
4. Skip if no dedup warnings found.

### Phase 2 (unattended): LLM deep audit
Run subagent as normal for contradictions, gap detection, stale claims, skill audit.
Auto-fix anything obvious (dead wikilinks, schema field typos, orphan files with clear target).
For complex/ambiguous items write memo: `$MEMO_DIR/lint-audit-flagged-$TODAY.md`
Format: bulleted list, one line per item: `- [TYPE] <filename>: <issue>`

### Phase 3 (unattended): JSONL mining + cleanup
Run as-is — already non-interactive. Finds JSONLs >7 days, mines knowledge, deletes sources.
No change from interactive mode.

### Phase 4 (unattended): Stale memory detection
Auto-fix simple ones: renamed paths (file moved but path string wrong), schedule drift (crontab
actual time differs from memory string by ≤30 min).
Write memo for complex ones (service removed, architecture changed, contradicts current code):
`$MEMO_DIR/lint-stale-memory-$TODAY.md`
Format: `- <memory-file>: <stale-claim> → <suggested-fix-or-question>`

### Phase 5a (unattended): Lessons promotion — dry-run only
```bash
cd ~/llm-wiki-stack && python3 promote/promote_lessons.py --limit 10
```
Run in dry-run mode (do NOT apply). Write full output to:
`$MEMO_DIR/lint-lessons-pending-$TODAY.md`
Header: `# Pending lessons — review and apply next interactive /lint`

### Phase 5b (unattended): Memory → rules scoring
Score all actionable memory entries (Durability + Impact + Scope, 0-3 each, threshold ≥7/9 — not ≥6).
Write candidates scoring ≥7 to: `$MEMO_DIR/lint-rules-candidates-$TODAY.md`
Format per candidate:
```
## <entry title>
Score: D<n>/I<n>/S<n> = <total>/9
Source: <memory file>
Proposed target: CLAUDE.md | .claude/rules/<topic>.md | ~/.claude/CLAUDE.md
> <rule text — imperative form>
```

### End of unattended run: git commit
After all phases complete:

**memory dir** (`~/.claude/projects/-Users-bernard/memory/`):
- Check if git repo: `git -C "$MEMORY_DIR" rev-parse --is-inside-work-tree 2>/dev/null`
- If NOT a git repo: log warning, skip. (Currently not a git repo — skip.)
- If IS a git repo: `git -C "$MEMORY_DIR" add -A && git -C "$MEMORY_DIR" commit -m "lint --unattended: $TODAY" && git -C "$MEMORY_DIR" push`

**NardoWorld** (`~/NardoWorld/`):
- Always commit if changes exist: `git -C ~/NardoWorld add -A && git -C ~/NardoWorld commit -m "lint --unattended: $TODAY"`
- No remote → skip push, log: `WARN: NardoWorld has no remote, skipping push`

## Phase 1: Deterministic scan
```bash
# Full run:
cd ~/llm-wiki-stack/lint/scripts && python3 wiki_lint.py
# Quick run (--quick flag): pass --no-semantic to skip dedup
cd ~/llm-wiki-stack/lint/scripts && python3 wiki_lint.py --no-semantic
```
Checks: schema conformance, orphan files, dead links, stale refs, missing cross-refs, expired memos, graph sync.

Options:
- `--fix` -- auto-fix: strip broken wikilinks, rebuild indexes, sync graph
- `--scope memory|wiki|all` -- limit scan scope
- `--json` -- machine-readable output

## Phase 1.5: Merge near-duplicates (if semantic_dedup warnings found)

After Phase 1, check for `semantic_dedup` warnings in the output. For each flagged pair:

1. Read both files
2. Show the user a one-line summary of each: title, type, key facts
3. Ask: **"[A] Keep A, [B] Keep B, [M] Merge both, [S] Skip"**
4. Before any deletion: move the file to be deleted into `~/NardoWorld/archive/` (safety backup — not a git commit, just a move)
5. Act on answer:
   - **A**: archive fileB, update all wikilinks in all files pointing to fileB's title → fileA's title; remove fileB's entry from `~/NardoWorld/index.md` and `MEMORY.md` if present
   - **B**: archive fileA, update all wikilinks pointing to fileA's title → fileB's title; remove fileA's entry from indexes
   - **M**: combine both files — merge content (keep best of each section, deduplicate facts, union tags/labels, use earlier `created`, today's `updated`), write merged result to fileA, archive fileB, update wikilinks + indexes
   - **S**: leave both, continue
6. After resolving all pairs, re-run `--no-semantic` to confirm no new issues.

Skip Phase 1.5 for `/lint --quick`.

## Phase 2: LLM deep audit (only if Phase 1 finds errors/warnings)
1. **Contradictions**: Read file pairs with overlapping entities, check for conflicting facts.
2. **Gap detection**: Broken wikilinks that SHOULD have pages -- create if valuable.
3. **Stale claims**: Files flagged 90+ days -- verify key facts.
4. **Skill audit**: Glob `~/.claude/skills/*/SKILL.md*` -- flag unused skills.

## Phase 3: JSONL mining + cleanup

Extract knowledge from expiring session logs before deletion.

1. Find JSONL files older than 7 days (Mac: `~/.claude/projects/*/`, VPS via SSH)
2. For each JSONL: extract head 100 + tail 300 lines, grep for text content
3. Look for: architecture decisions, new features, bug root causes, user corrections, cron changes, config changes
4. Cross-check against existing memory — skip duplicates
5. Save genuinely new findings to memory files
6. Delete scanned JSONL files (>7 days old)

Skip Phase 3 for `/lint --quick`.

## Phase 4: Stale memory detection + wiki migration

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

## Phase 5: Promote chain (patterns → rules, lessons → rules)

### 5a: Pending lessons
```bash
grep -l "status: pending" ~/NardoWorld/lessons/*.md 2>/dev/null | wc -l
```
If count > 0:
- Run dry run: `cd ~/llm-wiki-stack && python3 promote/promote_lessons.py --limit 10`
- Show results to user, ask to apply

### 5b: Memory → rules promotion

Score every actionable memory entry on three dimensions (0-3 each):

| Dimension | 0 | 1 | 2 | 3 |
|-----------|---|---|---|---|
| **Durability** | One-time fix | Session-specific | Multi-week relevant | Permanent convention |
| **Impact** | Nice to know | Saves minor time | Prevents bugs | Prevents outages |
| **Scope** | Single file | Single project area | Whole project | Cross-project |

**Promotion threshold: total score >= 6**

Recurring signals: same concept in 2+ files, user corrected Claude multiple times, imperative language ("always", "never"), survived 3+ maintenance cycles.

Promotion targets:
| Pattern type | Target |
|---|---|
| Project-wide convention | CLAUDE.md |
| File-type specific | `.claude/rules/<topic>.md` |
| Personal preference | `~/.claude/CLAUDE.md` |

Transform from description to prescription, write as imperative, remove from memory source.

### 5c: Skill extraction (when pattern is cross-project + non-obvious + multi-step)
Extract to `~/.claude/skills/<name>/SKILL.md`, remove source entries from memory.

Skip Phase 5 for `/lint --quick`.

## Phase 6: Skill audit + cleanup

### 6a: Inventory
```bash
du -sh ~/.claude/skills/*/ | sort -rh
ls -d ~/.claude/skills/*/ | wc -l
```

### 6b: Duplicate detection
Check for skills with overlapping triggers or identical purpose. Flag and recommend which to keep.

### 6c: Broken script detection
```bash
for skill in ~/.claude/skills/*/; do
  for py in "$skill"scripts/*.py 2>/dev/null; do
    python3 -c "import py_compile; py_compile.compile('$py', doraise=True)" 2>&1 || echo "BROKEN: $py"
  done
  for sh in "$skill"scripts/*.sh 2>/dev/null; do
    bash -n "$sh" 2>&1 || echo "BROKEN: $sh"
  done
done
```

### 6d: Usage tracking
- Flag skills not invoked in 30+ days as candidates for removal
- Skills with no `user-invocable: true` that are never auto-triggered

### 6e: Upstream update check
For skills from known repos (anthropics/skills, etc.), compare local SKILL.md hash vs GitHub raw.

### 6f: SKILL.md quality check
Every skill must have: `name:`, `description:`, trigger conditions, anti-triggers (NOT FOR:).
Max 400 chars per description. Rewrite any over limit.

### 6g: Broken symlinks
```bash
find ~/.claude/skills/ -type l ! -exec test -e {} \; -print
```

### 6h: Actions
After report, offer to: delete replaced skills, disable unused (.disabled), update from upstream, fix broken scripts.

Skip Phase 6 for `/lint --quick`.

## Capacity monitoring (report on every run)

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| MEMORY.md lines | < 120 | 120-180 | > 180 |
| CLAUDE.md lines | < 150 | 150-200 | > 200 |
| Topic files count | 0-15 | 16-30 | > 30 |
| Stale entries | 0 | 1-3 | > 3 |
| Pending JSONL (>7d) | 0 | 1-3 | > 3 |
| Skills count | < 30 | 30-50 | > 50 |
| Skills disk | < 100MB | 100-500MB | > 500MB |

## Flags
- `/lint` -- full run (Phase 1 + 1.5 + 2 + 3 + 4 + 5 + 6 + capacity)
- `/lint --quick` -- Phase 1 + 4 only (deterministic, fast, no LLM, no merge, no mining)
- `/lint --fix` -- Phase 1 with auto-fix + index rebuild + graph sync (includes merge)
- `/lint --memory` -- Phase 3 + 4 + 5 only (memory-focused maintenance)
- `/lint --skills` -- Phase 6 only (skill audit + cleanup)
- `/lint --unattended` -- fully non-interactive; writes memos instead of prompting; auto-fix safe changes; git commit at end. Intended for cron invocation.
</lint>
