# Phase 6: Skill audit + cleanup

## 6a: Inventory
```bash
du -sh ~/.claude/skills/*/ | sort -rh
ls -d ~/.claude/skills/*/ | wc -l
```

## 6b: Duplicate detection + trigger overlap audit
Extract every `Triggers:` line from all SKILL.md files. Tokenize trigger phrases. Flag:
- Identical trigger phrase in 2+ skills (hard conflict — ambiguous routing)
- Substring overlap ≥80% (soft conflict — likely one skill obsoletes the other)
- Same purpose stated in description despite different names
Report table: skill A | skill B | overlap type | recommended keep. Overlapping triggers = unpredictable skill routing, must resolve.

## 6c: Broken script detection
```bash
find ~/.claude/skills -path '*/scripts/*.py' -print 2>/dev/null | while read -r py; do
  python3 -c "import py_compile; py_compile.compile('$py', doraise=True)" 2>&1 || echo "BROKEN: $py"
done
find ~/.claude/skills -path '*/scripts/*.sh' -print 2>/dev/null | while read -r sh; do
  bash -n "$sh" 2>&1 || echo "BROKEN: $sh"
done
```

## 6d: Usage tracking
- Flag skills not invoked in 30+ days as candidates for removal
- Skills with no `user-invocable: true` that are never auto-triggered

## 6e: Upstream update check
For skills from known repos (anthropics/skills, etc.), compare local SKILL.md hash vs GitHub raw.

## 6f: SKILL.md quality check
Every skill must have: `name:`, `description:`, trigger conditions, anti-triggers (NOT FOR:).
Max 400 chars per description. Rewrite any over limit.

## 6g: Broken symlinks
```bash
find ~/.claude/skills/ -type l ! -exec test -e {} \; -print
```

## 6h: Lazy-load discipline
Per skill-health-check `Lazy-load heuristic`:
- Inline-bloat = (≥200 lines) AND (zero siblings) AND (zero on-demand reads). All three must hold.
- Two-of-three = borderline, flag but don't auto-recommend.
- Don't trust line count alone — `references/` dir + `Read` patterns + sibling content files mean it IS lazy.

## 6i: Actions
After report, offer to: delete replaced skills, disable unused (.disabled), update from upstream, fix broken scripts, convert inline-bloat skills to lazy stubs.

Skip Phase 6 for `/lint --quick`.
