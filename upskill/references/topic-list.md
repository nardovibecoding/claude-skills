# External scout source list

Source: `~/.ship/upskill/goals/01-spec.md` §2.1 SOP step 1.

Mechanism: shell out via `gh` CLI. NO caching for v1 — every invocation re-fetches (Bernard wants fresh).

## 1a. GitHub trending — primary

```bash
gh search repos --topic claude-code   --sort stars --limit 30 --json name,owner,description,stargazerCount,updatedAt
gh search repos --topic mcp           --sort stars --limit 30 --json name,owner,description,stargazerCount,updatedAt
gh search repos --topic ai-agent      --sort stars --limit 30 --json name,owner,description,stargazerCount,updatedAt
gh search repos --topic claude-skills --sort stars --limit 30 --json name,owner,description,stargazerCount,updatedAt
```

## 1b. Anthropic releases

```bash
gh api repos/anthropics/claude-code/releases?per_page=5
gh api repos/anthropics/anthropic-sdk-python/releases?per_page=5
gh api repos/anthropics/anthropic-sdk-typescript/releases?per_page=5
```

## 1c. Awesome-lists (curated catalogs)

```bash
gh api repos/hesreallyhim/awesome-claude-code/contents/README.md  # base64-decoded
gh api repos/awesome-mcp/awesome-mcp/contents/README.md           # if exists, soft-fail
```

## 1d. External release check (existing detector — pip/npm/swift)

```bash
python3 -c "from bigd.upgrade.detectors import external_release_check; print(external_release_check.run({}, {}, dry_run=True))"
```

## Filter heuristics (rule-based)

- `updatedAt >= now - 90d` (active project filter)
- `stargazerCount >= 50` for trending; `>= 10` for awesome-list children (lower bar — curation already filters)
- description must match one of: `agent|claude|mcp|skill|hook|cli|llm|harness` (case-insensitive)
- exclude already-installed: cross-ref `~/.claude/skills/*/SKILL.md` source URL frontmatter

## Output schema (per candidate)

```json
{"source": "github-trending|anthropic-release|awesome-list|pip-npm-swift",
 "name": "...", "owner": "...", "url": "...", "stars": N,
 "updated_at": "...", "description": "...", "category": "skill|cli|mcp|sdk|library"}
```

## Soft-fail policy

- Pre-flight: `gh api rate_limit` once at start; if `remaining < 100`, skip Step 1 entirely + emit `{scout_skipped: "rate_limit_low"}`.
- Each `gh` call wrapped with explicit exit-code capture; non-zero → emit `{source, error: "<exit_code>+<stderr_snippet>", scout_degraded: true}` instead of dropping silently.
- Time budget: ≤30s total (parallelize via `&` + `wait`).
- Total = 8 `gh` calls (4 topics + 3 releases + 1 awesome).
