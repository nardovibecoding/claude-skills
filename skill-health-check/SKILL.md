---
name: skill-health-check
description: Audit skill library health: enumerate broken symlinks, zero-byte stubs, stale disabled skills (60+ days), and orphaned refs in settings.json and skill-router. Run when user says "skill health", "check skills", or "skill audit".
user-invocable: true
triggers:
  - skill health
  - check skills
  - skill audit
  - health check skills
---

# Skill Health Check

Runs a structured audit of ~/.claude/skills/ and reports issues by severity.

## What It Checks

1. **Broken symlinks** -- find broken symlinks (e.g. gstack targets) in skills dir
2. **Stale disabled skills** -- SKILL.md.disabled files older than 60 days with no active refs
3. **Stub-only skills** -- SKILL.md under 200 bytes (just a skill-loader stub pointing nowhere valid)
4. **Orphan refs in skill-router** -- skill names in skill-router SKILL.md profiles that no longer exist as dirs
5. **Orphan refs in settings.json** -- hook commands pointing to files that no longer exist

## Output Format

```
SKILL HEALTH REPORT -- <date>
============================
[BROKEN SYMLINKS]   N found
  - <name> -> <target> (target missing)

[STALE DISABLED]    N found (>60 days, no inbound refs outside node_modules/.git)
  - <name> | <age> days | <size> bytes

[STUB SKILLS]       N found (<200 bytes, loader-only)
  - <name> | <size> bytes

[ORPHAN REFS]       N found
  - skill-router profile references: <missing-skill>
  - settings.json hook references: <missing-file>

[SUMMARY]
  Actionable: N  |  Clean: N  |  Total: N
```

## Execution Steps

1. Run each check using Bash (find, stat, grep)
2. Cross-reference skill dirs against skill-router profile entries
3. Check settings.json hook command paths for file existence
4. Print report -- do NOT auto-delete anything
5. Recommend specific actions: rm <symlink>, uninstall-skill <name>

## Guard Rules

- Read-only audit. Never delete, rename, or modify in health check mode.
- Flag conservatively: if unsure whether skill is in use, list as UNCLEAR not DELETE.
- Never flag as removable: /loop /s /combo /r1a /recall /ship /legends /lint extractskill github-publish strict-* agents skill-router skill-loader MCP.

## Bash Commands to Use

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
```
