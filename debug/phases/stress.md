# /debug Stress mode (Concern C6)

F-family: F4.2, F4.3, F7.3 (rate-bound, count-bound, timeout under load)
Concern: C6 (Performance under stress)

Per `~/.claude/rules/concerns-taxonomy.md` §C6 — performance under stress / 10× load / saturation.

Symptom: "How does X behave at 10× load?" / "Find the saturation point" / "What breaks first under burst?"

Distinct from `/debug performance` (steady-state hot loop) and `/debug leak` (unbounded growth). Stress mode probes the *envelope* — when does the system fall off the edge?

---

## Iron Laws

```
NO STRESS CLAIMS WITHOUT FRESH N≥2 LOAD READINGS
NO "PASSED 10×" WITHOUT THE ACTUAL 10× INPUT REPLAYED
```

---

## Step 1 — REPRODUCE baseline

Capture under normal load (baseline = current input rate):
- p50 / p95 / p99 latency per critical loop
- RSS / heap / event-loop lag
- CPU idle %
- Saturation: queue depth, in-flight count, socket buffers

Source: existing `host_metrics` / `bot_metrics` ledgers in `~/inbox/_metrics/`. If absent → emit `stress_metric_absent` (matches detector `stress_load_drill`).

---

## Step 2 — DEFINE the load drill

| dimension | baseline | drill |
|---|---|---|
| input rate (signals/min, msg/s, req/s) | observed | 10× observed |
| concurrent sessions / connections | observed | 10× |
| upstream latency injected | none | +200ms p99 |
| burst spike duration | n/a | 60s spike |

Pick ONE drill per invocation. Don't combine unless steady-state already passed all four.

---

## Step 3 — REPLAY

Synthetic-load methods, in order of preference:
1. **Replay-from-jsonl** — find a prior 10× signal day in trade-journal/signal-trace; replay against staging or DRY_RUN bot.
2. **Synthetic generator** — Python script emits N× rate to local mock endpoint or DRY_RUN handler.
3. **Live shadow** — non-destructive shadow listener in production with 10× duplicated input. Last resort; only if (1)+(2) infeasible.

Each method MUST cite the input size + source (`[cited <file or cmd>]`).

---

## Step 4 — MEASURE under drill

Same metrics as Step 1, captured under drill. Required:
- p99 latency
- RSS slope
- Queue depth max
- Drop rate (rejected / total)
- First-failure mode (which subsystem crashed/throttled first)

---

## Step 5 — VERDICT

| baseline OK | drill p99 ≤ threshold | drill saturated | Verdict |
|---|---|---|---|
| ✓ | ✓ | n/a | `passes_C6_drill` |
| ✓ | ✗ (over threshold but no crash) | ✗ | `degrades_C6` (latency only) |
| ✓ | ✗ | ✓ (crashed/dropped) | `breaks_C6` |
| ✗ | n/a | n/a | `baseline_dirty` — fix steady-state first via `/debug performance` |

`threshold` from `<project>/.ship/_meta/concerns.md` field `p99_tick_latency_ms_max` (or per-project equivalent per M2 meta-rule).

---

## Step 6 — RECEIPT + LEDGER

Append to `~/.claude/scripts/state/concern-receipts.jsonl`:

```json
{"ts": "<ISO>", "concern": "C6", "class": "stress_p99_exceeded|stress_break", "source": "/debug stress", "slug": "<unit>", "value": <p99>, "threshold": <thresh>, "severity": "MEDIUM|HIGH"}
```

LAND verdict line in `~/NardoWorld/realize-debt.md` per master plan §9 schema, with `[file:line]` citation pointing at the saturation site (RC-10 enforcement-clause rule from `~/.claude/skills/ship/phases/common/realization-checks.md`).

---

## Causal-claim gate (per CLAUDE.md §Epistemic discipline)

Before "drill saturated at N×": confirm N≥2 readings (drill once, drill again) with same input. Single-point drill = `[single-point]` per `~/.claude/skills/ship/phases/common/observations.md`; downgrade phrasing to "consistent with saturation".
