# Phase 8 — CLAUDE.md classification + trim

Triggered by `/lint --claudemd` flag (added 2026-04-30 via skill-consolidation step 18, folding the retired `claudemd-maintenance` skill).

Audits and consolidates a CLAUDE.md file (default: `~/.claude/CLAUDE.md`) to reduce context token burn. Combines well with Phase 5b §SCOPE ROUTING — rules that are CUSTOM but project-specific should be moved into `~/.claude/rules/<scope>.md` rather than kept in the global file.

---

## Phase 8.1 — Audit

Read the target CLAUDE.md. For each section (identified by `## ` or `### ` headers), classify:

| Classification | Definition | Action |
|---|---|---|
| INTERNALIZED | Claude already does this by default (safety, reasoning, coding best practices) | REMOVE |
| REINFORCED | Claude generally does this but has FAILED at it (check `~/NardoWorld/lessons/` or `self_review.md`) | TRIM to 1-2 lines |
| CUSTOM | Project-specific rules Claude would never know without being told | KEEP (or ROUTE to scoped file via §Phase 5b) |
| HISTORICAL | Specific past incidents, not actionable rules | MOVE to `~/NardoWorld/lessons/` or memory file |
| REDUNDANT | Says the same thing as another rule | MERGE with the other |

### Classification rules

**INTERNALIZED indicators (safe to REMOVE):**
- Generic engineering advice ("verify your work", "don't guess", "be thorough")
- Built-in Claude safety behavior ("don't expose API keys", "don't inject SQL")
- Aspirational platitudes ("continuously improve", "learn from mistakes")
- Rules with NO evidence of failure in lessons/self_review

**REINFORCED indicators (TRIM, don't remove):**
- Has corresponding entry in `~/NardoWorld/lessons/` (Claude failed at this)
- Project-specific nuance that makes the generic rule non-obvious
- Keep the ACTION ("do X when Y"); cut the STORY ("last time Z happened because…")

**CUSTOM indicators (must KEEP):**
- File paths, directory structure, tool names specific to projects
- Workflow patterns (combo, hookify, agent spawning rules)
- Integration details (MCP servers, bot tokens, API endpoints)
- Team conventions (commit style, deploy flow, sync architecture)

**HISTORICAL indicators (MOVE to memory):**
- Contains dates ("2026-03-20", "last session")
- References specific incidents ("XHS search failed because…")
- Starts with "Lesson:" or "Example:" followed by a story

**REDUNDANT indicators (MERGE):**
- Two sections that both say "verify before doing X" in different words
- A rule that's a subset of a more comprehensive rule
- A checklist item already covered by a higher-level rule

---

## Phase 8.2 — Report

Present a summary table:

```
| Action  | Count | Lines Saved |
|---------|-------|-------------|
| REMOVE  | X     | Y           |
| TRIM    | X     | Y           |
| MOVE    | X     | Y           |
| MERGE   | X     | Y           |
| ROUTE   | X     | Y           |  (CUSTOM rules going to rules/<scope>.md per Phase 5b)
| KEEP    | X     | 0           |
| TOTAL   |       | ~Z lines    |
```

Show current line count, projected post-trim line count, and estimated token savings (~2.5 tokens per line). Flag if CLAUDE.md exceeds 150-line cap (per CLAUDE.md §Rule meta length cap).

---

## Phase 8.3 — Apply (on user approval)

Unattended mode (`--unattended`) auto-applies safe categories: INTERNALIZED REMOVE, REDUNDANT MERGE, HISTORICAL MOVE-with-link. TRIM and ROUTE require interactive confirmation (they alter rule wording or scope, easier to get wrong).

Per category:
- **REMOVE**: delete the section.
- **TRIM**: shorten to 1-2 lines keeping the action rule; cut explanation/examples.
- **MOVE**: append to `~/NardoWorld/lessons/<topic>-<date>.md` with frontmatter; replace section in CLAUDE.md with one-line link.
- **MERGE**: combine into the stronger of the two rules; delete the weaker.
- **ROUTE**: cut from CLAUDE.md, paste into matching `~/.claude/rules/<scope>.md` (per Phase 5b SCOPE ROUTING table).

After all changes, report:
```
CLAUDE.md: X lines (was Y), saves ~Z tokens/message
rules/<scope>.md updated: <list>
lessons/ added: <list>
```

---

## Phase 8.4 — Cap enforcement

If CLAUDE.md still exceeds 150 lines after the audit pass, re-prompt user to demote at least N more sections to scoped rule files. Hard cap per CLAUDE.md §Rule meta length cap.

If a scoped rule file (`~/.claude/rules/*.md`) exceeds 150 lines, flag it as needing further sub-split. Same cap applies.

---

## Targets (in priority order)

1. `~/.claude/CLAUDE.md` (default — global rules)
2. `~/.claude/rules/<scope>.md` (each scoped file, capped 150 lines)
3. Project-local `CLAUDE.md` files (user passes `--target=<path>`)

Skip targets when:
- File is under 80 lines (no bloat to trim).
- File modified in the last 24h (active editing — wait for steady state).
