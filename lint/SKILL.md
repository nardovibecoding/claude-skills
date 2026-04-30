---
name: lint
description: |
  Unified system maintenance — wiki integrity, memory health, JSONL mining, skill audit, pattern promotion.
  Triggers: "lint", "memory maintenance", "clean memory", "mine sessions", "promote patterns", "audit skills".
  NOT FOR: editing memory files (just edit), installing skills (extractskill), security scans (skill-security-auditor).
user-invocable: true
---
<lint>

Run unified maintenance via lazy-loaded phase files. SKILL.md is the dispatcher only — each phase body lives in `references/`. Read only the phases your flag selects.

## Dispatcher

| flag | phases run | reads |
|---|---|---|
| `/lint` (no flag) | 1 + 1.5 + 2 + 3 + 4 + 5 + 6 + 7 + 9 + capacity | all 9 phase files |
| `/lint --quick` | 1 + 4 + capacity | `phase-1-scan.md`, `phase-4-stale.md` |
| `/lint --code` | 7 only | `phase-7-code.md` |
| `/lint --fix` | 1 with `--fix` + 1.5 + 9 with `--fix` + index rebuild + graph sync | `phase-1-scan.md`, `phase-1.5-dedup.md`, `phase-9-data.md` |
| `/lint --memory` | 3 + 4 + 5 | `phase-3-mining.md`, `phase-4-stale.md`, `phase-5-promote.md` |
| `/lint --skills` | 6 only | `phase-6-skills.md` |
| `/lint --claudemd` | 5b + 8 | `phase-5-promote.md`, `phase-8-claudemd.md` |
| `/lint --data` | 9 only | `phase-9-data.md` |
| `/lint --bot-data` | 9 only (synonym for `--data`) | `phase-9-data.md` |
| `/lint --unattended` | 1 + 1.5 + 2 + 3 + 4 + 5a + 5b + 9 (Phase 6 + 7 skipped) | `unattended.md` (which references each phase file) |

Always run **Capacity monitoring** at end (table below — small enough to keep inline).

## Phase file index

- `references/phase-1-scan.md` — wiki_lint.py deterministic scan (schema, orphans, dead links, dedup detection)
- `references/phase-1.5-dedup.md` — semantic dedup pair resolution (interactive [A/B/M/S], unattended writes memo)
- `references/phase-2-audit.md` — LLM deep audit: contradictions, gap detection, stale claims, skill audit
- `references/phase-3-mining.md` — JSONL mining + cleanup (>7d session logs)
- `references/phase-4-stale.md` — stale memory detection + wiki migration
- `references/phase-5-promote.md` — promote chain: lessons → rules, memory → rules, scope routing table
- `references/phase-6-skills.md` — skill audit (inventory, dup detection, broken scripts, lazy-load discipline)
- `references/phase-7-code.md` — code-redundancy scan (Phase-N prototype markers, superseded/replaced)
- `references/phase-8-claudemd.md` — CLAUDE.md classify-and-trim (folded from `claudemd-maintenance`, 2026-04-30)
- `references/phase-9-data.md` — bot-data + SSOT-log hygiene (cross-platform pollution, dead deprecated, oversized, schema drift, writer-gap)
- `references/unattended.md` — cron-safe variant: writes memos instead of prompting, auto-fix safe changes, git commit at end

## Capacity monitoring (report on every run)

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| MEMORY.md lines | < 120 | 120-180 | > 180 |
| CLAUDE.md lines | < 150 | 150-200 | > 200 |
| Topic files count | 0-15 | 16-30 | > 30 |
| Stale entries | 0 | 1-3 | > 3 |
| Pending JSONL (>7d) | 0 | 1-3 | > 3 |
| Skills count | < 80 | 80-120 | > 120 |
| Skills disk | < 100MB | 100-500MB | > 500MB |
| Project doc sync findings | 0 | 1-3 | > 3 |

## Execution rule

When invoked:
1. Parse flag from user input (default = full run).
2. Look up the row in the dispatcher table — read only the listed phase file(s) into context.
3. Execute each phase per its file's instructions, in order.
4. Run capacity monitoring (inline table above) — report any metric in Warning/Critical.
5. End with summary: phases run, files changed/skipped, memos written, capacity verdict.
</lint>
