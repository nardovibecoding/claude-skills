# Phase 2: LLM deep audit (only if Phase 1 finds errors/warnings)

1. **Contradictions**: Read file pairs with overlapping entities, check for conflicting facts.
2. **Gap detection**: Broken wikilinks that SHOULD have pages -- create if valuable.
3. **Stale claims**: Files flagged 90+ days -- verify key facts.
4. **Skill audit**: Glob `~/.claude/skills/*/SKILL.md*` -- flag unused skills.
5. **Project doc sync**: for each project under `~/NardoWorld/projects/*/`, read `<project>/docs/*.md` + `<project>/README.md` + `<project>/CLAUDE.md` if present. For each cited code symbol, env-var, or file path, verify it resolves in the live project tree. Mismatch → memo entry.

## Unattended variant

Auto-fix anything obvious (dead wikilinks, schema field typos, orphan files with clear target).
For complex/ambiguous items write memo: `$MEMO_DIR/lint-audit-flagged-$TODAY.md`
Format: bulleted list, one line per item: `- [TYPE] <filename>: <issue>`
Project-doc-sync mismatches → `$MEMO_DIR/lint-project-doc-sync-$TODAY.md` with `- <project>/<file>:<line>: <claim> → <live-state>`.
