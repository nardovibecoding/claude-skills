# /debug Risk mode (Concern C5)

F-family: F4.1, F4.5 (sum-bound, conservation), F12.1 (cross-path equivalence)
Concern: C5 (Model accuracy)

Per `~/.claude/rules/concerns-taxonomy.md` §C5 — model output / Kelly / vol / tail-risk calibration.

Symptom: "Live PnL ≠ backtest" / "Kelly bet too big" / "drawdown deeper than expected" / "Brier score climbing" / "tail loss event we didn't price".

Distinct from `/debug bug` (logic wrong) and `/debug drift` (config drift). Risk mode questions whether the *model parameters* match reality.

---

## Iron Laws

```
NO RISK CLAIMS WITHOUT N≥30 SAMPLES
NO "MODEL PASSES" WITHOUT BRIER OR LOG-LOSS NUMBER CITED
```

---

## Step 1 — REPRODUCE the calibration signal

Pull from existing detector output (`model_calibration_scan`):
- 30d trailing Brier score on resolved predictions
- N (sample count); if N<20 → emit `risk_insufficient_samples` and STOP
- threshold from `<project>/.ship/_meta/concerns.md` field `calibration_brier_max`

Required `[cited <file>]` for the score; never asserted in-head.

---

## Step 2 — DECOMPOSE the miscalibration

Group resolved predictions by:
- predicted-prob bucket (0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
- compute realized rate per bucket
- gap = realized − predicted; gap > 0.10 in any bucket = bucket-level miscalibration

Patterns:

| pattern | signature | likely cause |
|---|---|---|
| systematic over-confidence | predicted=0.8, realized=0.5 across N samples | Kelly fraction too high; widen vol input |
| under-confidence | predicted=0.5, realized=0.7 | model under-uses signal; add factor |
| tail underestimation | 3σ events 2× expected frequency | distribution assumption (gaussian on fat-tail) wrong |
| regime shift | recent 7d Brier >> 30d Brier | concept drift; retrain or freeze model |

---

## Step 3 — CROSS-CHECK

Cross-path equivalence (F12.1): compute the SAME PnL via:
1. Realtime stream (live tick-by-tick)
2. Settlement (resolved-only)

If realtime PnL diverges from settlement PnL by > 5% on the same set of trades → realtime stream is wrong, not the model. Stop here; route to `/debug bug` on stream code.

---

## Step 4 — VERDICT

| Brier ≤ threshold | bucket gap < 0.10 | recent vs 30d Brier | Verdict |
|---|---|---|---|
| ✓ | ✓ | stable | `passes_C5` |
| ✗ | (one bucket spiking) | n/a | `risk_bucket_drift` (bucket=...) |
| ✗ | (uniform gap) | stable | `risk_systematic_bias` |
| ✗ | n/a | recent >> 30d | `risk_regime_shift` |

---

## Step 5 — RECEIPT + LEDGER

Append to `~/.claude/scripts/state/concern-receipts.jsonl`:

```json
{"ts": "<ISO>", "concern": "C5", "class": "<verdict>", "source": "/debug risk", "slug": "<project>", "value": <brier>, "threshold": <thresh>, "n": <samples>, "severity": "HIGH-$"}
```

Fix slice (when `risk_systematic_bias` or `risk_regime_shift`) → escalate to `/ship` per CLAUDE.md §Ship discipline. Tighten Kelly cap (D14 quantitative) before retraining if HIGH-$ exposure live.

---

## Causal-claim gate

Before "the model is mis-calibrated": confirm sample size N≥30 (statistical floor), distinct days ≥7 (no single-day skew), and cross-path equivalence (Step 3). One bucket of 5 samples = `[single-point]`; downgrade to "consistent with bucket drift, needs N≥30".

Per CLAUDE.md §Pricing discipline: LLM-as-sole-pricer is forbidden for long-dated markets. If the Brier-source model is an LLM long-horizon estimator, the verdict is `risk_invalid_pricer` regardless of Brier value.
