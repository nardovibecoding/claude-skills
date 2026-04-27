# IA categories — /upskill user surface

Source: `~/.ship/upskill/goals/01-spec.md` §4.5.

User-facing ranked candidate list. Stranger-test labels (no daemon-name jargon — Bernard pet-peeves that).

## 5 categories (≤6 per L4 scale rule)

1. `[FIX-DRIFT]` — silent_revert / git_drift / state_drift / cross_host
2. `[FIX-PERF]` — bot_metrics / host_metrics / cache_hit_rate / ctx_growth / token_spend spike
3. `[ADOPT-EXT]` — github trending / anthropic release / awesome-list candidate
4. `[TRIM-SKILL]` — dis_score_assess low / skill staleness
5. `[CLEAN-HOUSE]` — auto_healer / spread_shrink / phantom_infra / deploy_postflight

## Stranger test (passes)

- `[FIX-DRIFT]` reads "code/state drift, fix it" → pass
- `[FIX-PERF]` reads "performance bottleneck" → pass
- `[ADOPT-EXT]` reads "external thing worth adopting" → pass
- `[TRIM-SKILL]` reads "skill not earning its keep" → pass
- `[CLEAN-HOUSE]` reads "low-stakes cleanup" → pass

## Anti-pattern caught

Avoid `gaps` / `performance` / `upgrade` in user surface (those are daemon-internals).

## Handoff routing per category

| category | handoff line |
|---|---|
| `[ADOPT-EXT]` | `/extractskill <url>` (Bernard invokes manually) |
| `[FIX-DRIFT]` | `/ship continue upskill-<slug>` |
| `[FIX-PERF]` | `/ship continue upskill-<slug>` |
| `[TRIM-SKILL]` | `/ship continue upskill-<slug>` |
| `[CLEAN-HOUSE]` | `/ship continue upskill-<slug>` |

## Display template

```
== UPSKILL CANDIDATES <DATE> ==
[1] [FIX-DRIFT] <name> — ROI=X.XX (impact=N, est_token_cost=K)
    <url>  ★<stars>  updated <Nd ago>
    one-line value prop
[2] ...
[5] ...

== SUGGESTED TOP-1 ==
<auto-spec written to .ship/upskill-<slug>/goals/01-spec.md>
Hand off: <handoff line per category above>

(Bernard: accept top-1 [Enter], pick another [N], or ignore [n])
```
