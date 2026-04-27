# Phase 1: Deterministic scan

```bash
# Full run:
cd ~/llm-wiki-stack/lint/scripts && python3 wiki_lint.py
# Quick run (--quick flag): pass --no-semantic to skip dedup
cd ~/llm-wiki-stack/lint/scripts && python3 wiki_lint.py --no-semantic
```

Checks: schema conformance, orphan files, dead links, stale refs, missing cross-refs, expired memos, graph sync.

Options:
- `--fix` -- auto-fix: strip broken wikilinks, rebuild indexes, sync graph
- `--scope memory|wiki|all` -- limit scan scope
- `--json` -- machine-readable output
