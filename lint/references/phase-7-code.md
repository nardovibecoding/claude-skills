# Phase 7: Code-redundancy scan (source files)

Scans source code for Phase-N prototype markers, superseded/replaced/deprecated comments, and other dead-code signals. Complements Phase 1's wiki/memory scan + Phase 6's skill audit by covering the source-file gap.

```bash
python3 ~/llm-wiki-stack/lint/scripts/code_redundancy_scan.py --severity HIGH
```

Default scopes: `~/prediction-markets/packages/`, `~/.claude/hooks/`, `~/.claude/scripts/`.

Flags:
- `--scope <dir>` — override scope (repeatable)
- `--severity LOW|MEDIUM|HIGH` — minimum severity to report
- `--json` — machine-readable output

Markers detected:
- HIGH: `Phase N prototype/experimental/alpha`, `superseded by`, `replaced by`
- MEDIUM: `deprecated`, `legacy`, `// killed` / `# killed`, `// removed` / `# removed`, `// dead code`
- LOW: `TODO: delete/remove/kill`, `out of scope for this module`

Output: file:line + match + severity + reason. Human reviews HIGH first; if module is config-off + superseded + still wired, delete (per CLAUDE.md "replaced = deleted" rule).

NOT auto-fix — code deletion is too risky for unattended cron. For each HIGH finding, show user, ask delete/keep/defer.

Skip Phase 7 for `/lint --quick`.

Source: pm-london wedge 2026-04-25 — adversarial-detector.ts was a Phase 1 prototype superseded by Python pipeline, config-off, but ingestion still wired. Caused production wedge. This scanner catches that pattern.

## Silent unused-imports scan (added 2026-04-30)

The marker scan above misses **silent unused imports** — symbols imported but never used, with no `// killed` annotation. Most common form of disable-without-cleanup debt (CLAUDE.md §Naming hygiene).

Detection: parse `tsc --noEmit` output for TS6133 (`'X' is declared but its value is never read`) across `~/prediction-markets/packages/bot/`. Optional: `npx ts-prune` for dead-export detection.

```bash
cd ~/prediction-markets && npm run build 2>&1 | grep -E "TS6133|error TS6192" | sort -u
```

For each finding: `git blame` the import line, surface the originating commit subject (often a `feat:` later rolled back via config-disable). Severity: MEDIUM (clutter), HIGH if the unused import is from a strategy module that's still partially wired (config-off but ingestion code pulls the symbol via re-export).

Source: 2026-04-30 — 12 unused imports across `main.ts` + `risk.ts` traced to 6 disable-without-cleanup commits over 22 days (`executeArb`, `MetaculusClient`, `scanStaleMarkets`, `mkdirSync`, `STOP_LOSS_PCT`, etc.). Phase 7 originally caught only commented-out call sites, missed the imports themselves.
