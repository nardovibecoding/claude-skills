# Lens design (upskill v2)

A **lens** is a YAML config that biases /upskill scout + rank toward a topic.
One lens per scout invocation. Resolved via `scripts/lens_resolve.py`.

Cite: spec §2.1 (`~/.ship/upskill/goals/01-spec.md` lines 43-72), plan §S1 (`~/.ship/upskill/goals/02-plan.md` lines 53-62).

## Schema

Required:

| key | type | notes |
|---|---|---|
| `name` | string | unique label, used in output JSON + reports |
| `keywords` | list[string] | min 1; used by scout for GitHub/code search |
| `scoring_weights` | dict | keys: `stars`, `recency`, `keyword_fit`, `language_match`; floats summing to **1.0 ± 0.01** |
| `integration_cost_model` | string | one of: `skills` (2hr base), `code` (4hr), `infra` (8hr) — see spec §2.4 lines 120-126 |

Optional:

| key | type | notes |
|---|---|---|
| `gh_topics` | list[string] | hint for `gh search repos --topic ...` |
| `overlay_sources` | list[string] | bigd-* dataset names blended into rank |
| `lang` | string | `|`-separated language filter (e.g. `typescript|python`) |

## Validation rules (HARD)

- `sum(scoring_weights.values()) ∈ [0.99, 1.01]` — else `lens_resolve.py` exits 1.
- `integration_cost_model` must match one of `{skills, code, infra}`.
- `keywords` non-empty list.
- File >50 lines emits warning (spec §6 lens-bloat risk).

## Example (skills.yaml, annotated)

```yaml
name: skills                     # required, unique
keywords:                        # required, ≥1
  - claude skill                 # high keyword_fit weight (0.4) → match matters
  - agent capability
  - SKILL.md
  - anthropic skill
  - skill marketplace
gh_topics: [claude-code, claude-skill, anthropic]   # optional gh hint
scoring_weights:                 # required, sum=1.0 ± 0.01
  stars: 0.3                     # popularity less critical for new skills
  recency: 0.2                   # tolerant of older but solid skills
  keyword_fit: 0.4               # primary signal
  language_match: 0.1            # most skills are markdown anyway
integration_cost_model: skills   # 2hr base (skills are markdown-only)
overlay_sources: []              # no bigd overlay
```

## Custom menus

Use `--lens menu:<file.json>` to scout against a curated list.

```json
{
  "menu_id": "my-curated-list",
  "items": [
    {"id": "fastify", "keywords": ["fastify", "node http"], "priority": 1},
    {"id": "valkey", "keywords": ["valkey", "redis fork"], "priority": 2}
  ]
}
```

Auto-constructed lens uses generic weights (0.3 / 0.2 / 0.4 / 0.1) and `skills` cost model. Place files under `~/.claude/skills/upskill/lenses/menu/`.

## Authoring a new YAML lens

1. `cp ~/.claude/skills/upskill/lenses/general.yaml ~/.claude/skills/upskill/lenses/<name>.yaml`
2. Edit `keywords`, `gh_topics`, weights, cost model.
3. `python3 ~/.claude/skills/upskill/scripts/lens_resolve.py --lens <name> --out /tmp/check.json` — must exit 0.
4. `jq '.scoring_weights | values | add' /tmp/check.json` — must be ~1.0.
