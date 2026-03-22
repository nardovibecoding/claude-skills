---
name: skillcleaning
description: |
  Audit, clean, and monitor all installed Claude Code skills.
  Checks for: outdated skills, duplicates, broken scripts, unused skills,
  upstream updates, disk usage, and inconsistencies.

  USE FOR:
  - "skill cleaning", "clean skills", "audit skills"
  - "check for skill updates", "are my skills up to date"
  - "which skills am I not using", "skill health"
  - Periodic maintenance (monthly recommended)
user-invocable: true
---

# Skill Cleaning — Audit, Monitor & Maintain Skills

## When to Run
- Monthly maintenance
- After installing new skills
- When skills list feels bloated
- Before major deployments

## Checks to Run

### 1. Inventory & Disk Usage

List all skills with size:
```bash
du -sh ~/.claude/skills/*/  | sort -rh
```

Count total:
```bash
ls -d ~/.claude/skills/*/ | wc -l
```

### 2. Duplicate Detection

Check for skills that do the same thing:
- singlesourceoftruth vs mactovps/vpstomac (old ones should be deleted)
- system-check vs any health check skill
- Multiple skills with overlapping triggers

Flag duplicates and recommend which to keep.

### 3. Broken Script Detection

For each skill with scripts/:
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

### 4. Missing Dependencies

For skills with Python scripts, check imports:
```bash
for py in ~/.claude/skills/*/scripts/*.py; do
  python3 -c "
import ast, sys
with open('$py') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        mod = node.module if hasattr(node, 'module') and node.module else (node.names[0].name if node.names else '')
        if mod:
            try:
                __import__(mod.split('.')[0])
            except ImportError:
                print(f'MISSING: {mod} in $py')
" 2>/dev/null
done
```

### 5. Usage Tracking

Check which skills have actually been invoked recently:
- Search conversation logs for skill invocations
- Flag skills not used in 30+ days as candidates for removal
- Skills with no SKILL.md frontmatter `user-invocable: true` that are never auto-triggered

### 6. Upstream Update Check

For skills from known repos, check if newer versions exist:

| Source | Check method |
|--------|-------------|
| anthropics/skills (docx, pdf, pptx, xlsx) | Compare local SKILL.md hash vs GitHub raw |
| alirezarezvani/claude-skills | Compare version in metadata |
| claude-plugins-official | Plugin manager handles this |
| Custom skills | No upstream — skip |

```bash
# Example: check if official skills have updates
for skill in docx pdf pptx xlsx; do
  LOCAL_HASH=$(md5 -q ~/.claude/skills/$skill/SKILL.md 2>/dev/null)
  REMOTE_HASH=$(curl -s "https://raw.githubusercontent.com/anthropics/skills/main/skills/$skill/SKILL.md" | md5 -q 2>/dev/null)
  if [ "$LOCAL_HASH" != "$REMOTE_HASH" ] && [ -n "$REMOTE_HASH" ]; then
    echo "UPDATE AVAILABLE: $skill"
  fi
done
```

### 7. Git Sync Status

Check if skills repo is clean and synced:
```bash
cd ~/.claude/skills
git status --short
git log --oneline HEAD..origin/main 2>/dev/null | head -5
```

### 8. Security Re-scan

Re-run skill-security-auditor on all installed skills:
```bash
for skill in ~/.claude/skills/*/; do
  python3 ~/.claude/skills/skill-security-auditor/scripts/skill_security_auditor.py "$skill" --json 2>/dev/null
done
```

### 9. Symlink Check

Find broken symlinks:
```bash
find ~/.claude/skills/ -type l ! -exec test -e {} \; -print
```

### 10. SKILL.md Quality Check

Every skill should have:
- [ ] `name:` in frontmatter
- [ ] `description:` in frontmatter
- [ ] Clear trigger conditions (when to use)
- [ ] No prompt injection patterns

Flag skills missing these.

## Output Format

```
=== Skill Cleaning Report ===

Total skills: 26
Total disk: 45MB

DUPLICATES:
  (none found)

BROKEN:
  (none found)

MISSING DEPS:
  docx/scripts/accept_changes.py — needs lxml (pip install lxml)

UNUSED (30+ days):
  indicator-plugged — never invoked
  indicator-unplugged — never invoked
  event-register — last used 2026-02-15

UPDATES AVAILABLE:
  pdf — upstream changed 2026-03-18
  xlsx — upstream changed 2026-03-19

GIT STATUS:
  Clean, synced with origin

SECURITY:
  All PASS

RECOMMENDATIONS:
  1. Remove indicator-plugged/unplugged if not using dual monitor
  2. Update pdf and xlsx from upstream
  3. Install lxml for docx scripts
```

## Actions

After the report, offer to:
- Delete unused skills (with confirmation)
- Update skills from upstream
- Install missing dependencies
- Fix broken scripts
- Commit and push changes to skills repo
