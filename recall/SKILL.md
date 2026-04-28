---
name: recall
description: >
  Graph-aware context loader. Auto-fires (NOT user-invoked) when user mentions a project/system topic
  in a message. Implementation - HOOKS, not slash-command. Reads ~/NardoWorld/meta/hub_nodes.json
  + graph_index.json, follows wikilinks, injects context. Always-on per CLAUDE.md.

  Triggers - any project/system reference at session start or in user message
  ("go back to PM bot", "work on Edwin", "recall X", "load context for X").

  NOT FOR - explicit on-demand recall (this is automatic). For manual graph queries,
  read hub_nodes.json directly or run ~/.claude/skills/recall/search.mjs.
---

# /recall — graph-aware context loader

**Implementation type**: hook-based (NOT a conventional slash-command). The behavior is wired through
UserPromptSubmit hooks in `~/.claude/settings.json`, not a SKILL.md body. This file exists so
skill-loader / skill-router / skill-health-check / inventory tools can discover the entity.

A separate JS-based implementation also lives in this directory (`build-index.mjs` + `search.mjs`)
for FTS5/BM25 querying. The chat-time auto-recall path is the hooks; the JS path is for explicit
manual querying.

## How it actually works (auto-recall path)

1. User submits a message mentioning a topic (e.g., "PM bot", "Hel", "dagou", "kalshi").
2. UserPromptSubmit hooks fire in order (verified wired in `~/.claude/settings.json`):
   - `~/.claude/hooks/memory_recall_hook.py` — keyword → memory file lookup
   - `~/.claude/hooks/graph_context.py` — topic → hub_nodes.json hit + 1-hop neighbors
   - `~/.claude/hooks/concept_search_reminder.py` — guards against literal-only searches
3. Matched context is injected as a system reminder. Assistant has the relevant background without
   the user typing /recall.

## Manual query path

```
node ~/.claude/skills/recall/search.mjs "<query>"     # BM25 search across indexed corpus
node ~/.claude/skills/recall/build-index.mjs           # rebuild FTS5 index after large memory edits
```

## Data sources

- `~/NardoWorld/meta/hub_nodes.json` (~22KB, 1-hop graph index — fast lookup)
- `~/NardoWorld/meta/graph_index.json` (~576KB, full graph — deep traversal)
- `~/.claude/projects/-Users-bernard/memory/` (convo files + lessons indexed by build-index.mjs)

## Liveness check

```
ls -la ~/.claude/hooks/memory_recall_hook.py ~/.claude/hooks/graph_context.py ~/.claude/hooks/concept_search_reminder.py
jq '.hooks.UserPromptSubmit[].hooks[].command' ~/.claude/settings.json | grep -E "memory_recall|graph_context|concept_search"
```

All three hook paths must exist and all three commands must appear in settings.json.

## Recovery if broken

- Hooks missing: re-pull from `~/.claude/hooks` git remote (self-hosted bare repo on Hel — see
  `~/NardoWorld/meta/references/reference-memory-sync.md`).
- Hook wired but no context surfaces: check `~/NardoWorld/meta/hub_nodes.json` is non-empty + valid JSON;
  regenerate via the graph-builder script under `~/NardoWorld/scripts/` if stale.
- FTS index stale: `node ~/.claude/skills/recall/build-index.mjs`.
- False negatives ("not finding context for X"): widen synonyms in
  `~/.claude/hooks/concept_search_reminder.py`.

## Cross-refs

- `~/.claude/CLAUDE.md` §"Graph-aware recall (automatic)" — the canonical rule
- `~/NardoWorld/meta/references/reference-skill-and-daemon-map.md` §2 TIER-0 /recall entry
- `~/NardoWorld/meta/references/reference-memory-sync.md` — sync truth for hooks/memory repos

_Section last updated: 2026-04-29 14:00 CST_
