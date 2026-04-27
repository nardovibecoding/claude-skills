# Phase 5: Promote chain (patterns → rules, lessons → rules)

## 5a: Pending lessons
```bash
grep -l "status: pending" ~/NardoWorld/lessons/*.md 2>/dev/null | wc -l
```
If count > 0:
- Run dry run: `cd ~/llm-wiki-stack && python3 promote/promote_lessons.py --limit 10`
- Show results to user, ask to apply

### Unattended (5a)
Run dry-run only (do NOT apply). Write full output to:
`$MEMO_DIR/lint-lessons-pending-$TODAY.md`
Header: `# Pending lessons — review and apply next interactive /lint`

## 5b: Memory → rules promotion

Score every actionable memory entry on three dimensions (0-3 each):

| Dimension | 0 | 1 | 2 | 3 |
|-----------|---|---|---|---|
| **Durability** | One-time fix | Session-specific | Multi-week relevant | Permanent convention |
| **Impact** | Nice to know | Saves minor time | Prevents bugs | Prevents outages |
| **Scope** | Single file | Single project area | Whole project | Cross-project |

**Promotion threshold: total score ≥ 7/9** (matches unattended Phase 5b threshold)

Recurring signals: same concept in 2+ files, user corrected Claude multiple times, imperative language ("always", "never"), survived 3+ maintenance cycles.

### SCOPE ROUTING (mandatory before setting target — first match wins)

| Keywords in rule text | Target |
|---|---|
| `kalshi`, `polymarket`, `manifold`, `hel`, `london`, `pm-bot`, `pm-london`, `prediction market`, `clobStream`, `whale`, `KMM` | `~/.claude/rules/pm-bot.md` |
| `agent`, `strict-plan`, `strict-execute`, `strict-research`, `strict-explore`, `strict-review`, `frontmatter`, `subagent_type`, `YAML` (agent context) | `~/.claude/rules/agents.md` |
| `/ship`, `ship phase`, `SPEC phase`, `PLAN phase`, `EXECUTE phase`, `LAND phase`, `MONITOR phase`, `OUTPUT CONTRACT` | `~/.claude/rules/ship.md` |
| `hook`, `guard`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop hook` | `~/.claude/rules/hooks.md` (create if missing) |
| `skill`, `SKILL.md`, `skill-router`, `.disabled` | `~/.claude/rules/skills.md` (create if missing) |
| `dagou`, `BSC`, `KOL`, `S5`, `sniper` | `~/.claude/rules/dagou.md` (create if missing) |
| File-type specific (python/markdown/yaml patterns) | `~/.claude/rules/<file-type>.md` |
| **No keyword match AND** rule is cross-cutting discipline (decide/ship/plan/communicate) | `~/.claude/CLAUDE.md` |
| **No keyword match AND** unclear scope | flag for MANUAL routing — do NOT default to CLAUDE.md |

Hard rule: if ANY project keyword matches, NEVER propose CLAUDE.md. CLAUDE.md is for universal only.

Transform from description to prescription, write as imperative, remove from memory source.

### Unattended (5b)
Score all actionable memory entries (Durability + Impact + Scope, 0-3 each, threshold ≥7/9 — not ≥6).
Write candidates scoring ≥7 to: `$MEMO_DIR/lint-rules-candidates-$TODAY.md`

Format per candidate:
```
## <entry title>
Score: D<n>/I<n>/S<n> = <total>/9
Source: <memory file>
Scope keywords detected: <list or "none">
Proposed target: <resolved path per routing table above>
> <rule text — imperative form>
```

## 5c: Skill extraction (when pattern is cross-project + non-obvious + multi-step)
Extract to `~/.claude/skills/<name>/SKILL.md`, remove source entries from memory.

Skip Phase 5 for `/lint --quick`.
