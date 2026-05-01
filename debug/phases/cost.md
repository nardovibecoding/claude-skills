# /debug Cost mode (Concern C1)

F-family: F4.3 (rate-bound on API calls), cross-cutting cost axis
Concern: C1 (Cost)

Per `~/.claude/rules/concerns-taxonomy.md` §C1 — token spend + infra $ vs revenue.

Symptom: "X is expensive" / "token spend spike" / "cost-revenue ratio drift" / "why did the LLM bill jump".

Distinct from `/debug performance` (latency, not $) and `/debug leak` (memory, not $). Cost mode follows the money: $-spent / $-generated.

---

## Iron Laws

```
NO COST VERDICTS WITHOUT $-SPENT AND $-GENERATED BOTH CITED
NO "OPTIMIZED X" WITHOUT BEFORE/AFTER LEDGER ROWS
```

---

## Step 1 — REPRODUCE the cost signal

Pull from existing detector output (`cost_profit_ratio_scan`):
- 30d trailing $-spent (token + infra)
- 30d trailing $-generated (PnL or value proxy)
- ratio = spend / generated

If detector hasn't run today: invoke once via `python3 ~/NardoWorld/scripts/bigd/performance/daemon.py --once` (DRY-able) and read its findings.

Required `[cited <file>]` for both numbers — never asserted in-head per CLAUDE.md §No mental math.

---

## Step 2 — LOCALIZE the spend

Token spend ledger: `~/inbox/_metrics/token_spend.jsonl`. Group by:
- model (opus / sonnet / haiku)
- caller (bot src path / hook / skill name)
- time-of-day pattern (burst vs sustained)

Top-3 callers by 7d spend → these are the audit targets.

---

## Step 3 — FIND the bug-class

Common shapes (cross-ref `~/.claude/rules/disciplines/bounded-queue.md` D8 + `pm-bot.md` §LLM 429 cooldown):

| shape | signature | fix-class |
|---|---|---|
| hot-loop API call | spend ∝ time, no debounce | add cooldown / rate-bound |
| retry storm on 429/5xx | spend spike correlated with error rate | exponential backoff |
| fallback to expensive model | spend spike coincident with degradation | gate fallback on cost cap |
| unbounded prompt growth | per-call cost climbing over days | reset / truncate context |
| no caching | identical prompts billed N× | prompt-cache breakpoint |

---

## Step 4 — VERDICT

| ratio ≤ threshold | per-caller spike | retry storm | Verdict |
|---|---|---|---|
| ✓ | n/a | n/a | `passes_C1` |
| ✗ | (one caller >50% of total) | n/a | `cost_drift_localized` (caller=...) |
| ✗ | (distributed) | ✓ | `cost_drift_retry_storm` |
| ✗ | (distributed) | ✗ | `cost_drift_diffuse` — full audit needed |

`threshold` = `cost_revenue_ratio_max` from `<project>/.ship/_meta/concerns.md`.

---

## Step 5 — RECEIPT + LEDGER

Append to `~/.claude/scripts/state/concern-receipts.jsonl`:

```json
{"ts": "<ISO>", "concern": "C1", "class": "<verdict>", "source": "/debug cost", "slug": "<project>", "value": <ratio>, "threshold": <thresh>, "severity": "HIGH-$" }
```

Fix slice (when ratio ≥ 1.5× threshold or caller spike) → escalate to `/ship` immediately per CLAUDE.md §Ship discipline (decided 2x, ship now).

---

## Causal-claim gate

Before "the trigger is X retry": run 3-Q gate (CLAUDE.md §Causal-claim gate). Cost spike correlated with retry rate is `[suggestive, not isolated]` until you compare a same-interval window pre-spike with retries=baseline.
