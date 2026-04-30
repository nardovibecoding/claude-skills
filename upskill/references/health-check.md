# /upskill health — skill library health audit

Folded from the retired `skill-health-check` skill (2026-04-30, skill-consolidation step 19).

Read-only audit of `~/.claude/skills/`. Reports issues by severity. NEVER auto-deletes.

## What it checks

1. **Broken symlinks** — `~/.claude/skills/<name>` symlink with missing target (e.g. gstack pointing nowhere).
2. **Stale disabled skills** — `SKILL.md.disabled` files older than 60 days with no inbound refs (excluding node_modules/.git).
3. **Stub-only skills** — `SKILL.md` under 200 bytes (just a skill-loader stub pointing nowhere valid).
4. **Orphan refs in skill-router** — skill names in skill-router profiles that no longer exist as dirs.
5. **Orphan refs in settings.json** — hook commands pointing to files that no longer exist.
6. **Inline-bloat skills** (lazy-load discipline) — `SKILL.md` ≥200 lines AND zero sibling content (no `references/` dir, no `scripts/` dir, no `*.md` peers, no `Read .*\.md` / `references/` patterns inside). These load full body on every invocation and should split.

## Lazy-load heuristic (HARD RULE — don't repeat the bigd/legends miscall)

Line count alone is NOT the signal. A 700-line SKILL.md can be perfectly lazy if it dispatches to sibling files; a 250-line SKILL.md can be fully inline if it has no siblings.

Audit order:
1. `ls <skill-dir>` — does it have siblings (`references/`, `scripts/`, `*.md` peers, `*.yaml` data files)?
2. `grep -E 'Read |references/|@.*\.md|phases/|<dir>/<file>\.md' SKILL.md` — does the body read sibling content on-demand?
3. **Inline-bloat verdict** = (≥200 lines) AND (zero siblings) AND (zero on-demand reads). All three must hold. Two-of-three = borderline, flag but don't auto-recommend.
4. Skills whose SKILL.md content IS the skill (small dispatchers, e.g. `chatid`, `tab`) are exempt regardless of line count.

## Output format

```
SKILL HEALTH REPORT — <date>
===============================================
[BROKEN SYMLINKS]   N found
  - <name> -> <target> (target missing)

[STALE DISABLED]    N found (>60 days, no inbound refs outside node_modules/.git)
  - <name> | <age> days | <size> bytes

[STUB SKILLS]       N found (<200 bytes, loader-only)
  - <name> | <size> bytes

[ORPHAN REFS]       N found
  - skill-router profile references: <missing-skill>
  - settings.json hook references: <missing-file>

[INLINE BLOAT]      N found (≥200 lines + zero siblings + zero on-demand reads)
  - <name> | <lines> lines | suggest split

[SUMMARY]
  Actionable: N  |  Clean: N  |  Total: N
```

## Execution steps

1. Run each check using Bash (find, stat, grep).
2. Cross-reference skill dirs against skill-router profile entries.
3. Check settings.json hook command paths for file existence.
4. Print report — do NOT auto-delete anything.
5. Recommend specific actions: `rm <symlink>`, `mv SKILL.md SKILL.md.disabled` (manual disable), or `/lint --skills` for deeper audit.

## Guard rules

- Read-only audit. Never delete, rename, or modify in health check mode.
- Flag conservatively: if unsure whether skill is in use, list as UNCLEAR not DELETE.
- Never flag as removable: `/loop`, `/s`, `/combo`, `/r1a`, `/recall`, `/ship`, `/legends`, `/lint`, `extractskill`, `github`, `strict-*` agents, `skill-router`, `skill-loader` MCP.

## Bash commands

```bash
# Broken symlinks
find ~/.claude/skills -maxdepth 2 -type l ! -exec test -e {} \; -print

# Age of disabled skills (macOS)
find ~/.claude/skills -name 'SKILL.md.disabled' -maxdepth 3 | while read f; do
  age=$(( ($(date +%s) - $(stat -f %m "$f")) / 86400 ))
  size=$(wc -c < "$f")
  echo "$age days | $size bytes | $f"
done | sort -rn

# Stub check (< 200 bytes)
find ~/.claude/skills -name 'SKILL.md' -maxdepth 3 | while read f; do
  size=$(wc -c < "$f")
  [ "$size" -lt 200 ] && echo "$size bytes | $f"
done

# skill-router orphans
grep -oP "\`[^\`]+\`" ~/.claude/skills/skill-router/SKILL.md | tr -d '\`' | while read s; do
  [ ! -d ~/.claude/skills/$s ] && echo "ORPHAN in skill-router: $s"
done

# settings.json orphan hooks
python3 -c "
import json, os
s = json.load(open(os.path.expanduser('~/.claude/settings.json')))
for hook_set in s.get('hooks', {}).values():
    for h in hook_set:
        for cmd in h.get('hooks', []):
            path = cmd.get('command', '').split()[1] if cmd.get('type') == 'command' else None
            if path and path.startswith('/') and not os.path.exists(path):
                print(f'ORPHAN hook path: {path}')
"
```
