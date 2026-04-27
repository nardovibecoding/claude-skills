# ROI formula — /upskill ranking

Source: `~/.ship/upskill/goals/01-spec.md` §3.

**Formula**: `ROI = impact / expected_token_spend`. Higher = better.

## Impact tier (1-5 integer, rule-based by category)

| category | impact | rationale |
|---|---|---|
| drift (silent_revert / git_drift / state_drift) | 5 | corruption-class, blocks correct execution |
| silent-revert | 5 | (subset of drift, explicit) |
| bottleneck-perf (host_metrics critical / bot_metrics down) | 4 | live trading affected |
| cache-hit-rate / ctx-growth >20%/wk | 3 | cost bleed, no immediate failure |
| external-upskill (github trending / anthropic release / awesome-list) | 3 | speculative — needs probe |
| dis-score-assess low | 2 | wasted skill surface, no critical path |
| spread-shrink-pass / auto-healer | 1 | INFO-tier housekeeping |

## Expected token spend (base costs, per category)

```python
base_costs = {
    "drift":              60_000,   # debug-bug 17-step engine, multi-host
    "silent-revert":      40_000,   # git-bisect + cherry-pick + verify
    "bottleneck-perf":    80_000,   # /debug performance + /ship fix
    "cache-hit-rate":     30_000,   # tighter prompt caching, edit a few prompts
    "ctx-growth":         50_000,   # context-budget audit
    "external-upskill":  120_000,   # /extractskill + integrate + verify (uncertain)
    "dis-score-assess":   25_000,   # rewrite SKILL.md or retire
    "spread-shrink":      15_000,   # housekeeping (single-file usually)
    "auto-healer":        10_000,
}
```

## Multipliers

- **Cross-host**: if candidate touches >1 host, `base *= 1.5`.
- **Cache discount**: pull `recent_7d_per_model_per_day` from `bigd/performance/detectors/token_spend.py`. Compute `cache_hit = cache_read / (cache_read + input)`. Apply `base *= (1 - 0.3 * cache_hit)` (up to 30% discount when cache warm).

## Pseudocode

```python
def estimate_fix_cost_tokens(candidate):
    base = base_costs.get(candidate.category, 50_000)
    if candidate.cross_host:
        base *= 1.5
    recent = token_spend.get_recent_7d_per_model()
    recent_input = sum(r["input_tokens"] for r in recent)
    recent_cache_read = sum(r["cache_read_tokens"] for r in recent)
    if recent_input > 0:
        cache_hit = recent_cache_read / (recent_cache_read + recent_input)
        base *= (1 - 0.3 * cache_hit)
    return int(base)

def roi_score(candidate):
    return candidate.impact / max(estimate_fix_cost_tokens(candidate), 1)
```

## Tiebreaker

Higher impact wins → lower expected_token_spend → more recent `updated_at` (external) or `last_seen` (internal).

## Co-tied display

When top-2 ROI within 10%, both flagged `co_tied_top: true` and shown to Bernard.

## NEVER

- Estimated hours — Bernard rejected. Token spend is the only currency.
- LLM ranking — rule-based per CLAUDE.md "Rule-based > LLM" HARD RULE.
