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
