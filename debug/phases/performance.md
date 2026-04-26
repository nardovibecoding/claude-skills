# /debug Performance mode (Group A — symptom-first → cause)

Per master plan §3 compression matrix row "Performance": ALL 17 steps active.

Symptom: "X is slow / hot loop / leaking / high CPU". Fires correctly but consumes excessive resources.

---

## Iron Laws

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

---

## Baseline metrics (Step 1 REPRODUCE)

Per `~/.claude/skills/ship/phases/bot/04-land.md` step 7 — capture:

- scan-loop rate
- fill latency P50 / P99
- mem growth over 1h
- CPU idle %
- I/O wait
- API rate utilization
- socket reconnect frequency
- zombie procs
- N+1 query count
- unbounded cache size

If `--baseline=<file>` provided: read prior baseline, compute deltas. Else: capture current as "first baseline" and emit verdict `inconclusive` with note.

---

## Step 8 INSTRUMENT — perf marker pattern

`[DEBUG H1]` tagged log lines wrapped in `#region DEBUG ... #endregion` reversible blocks; sink → `~/.claude/debug.log`. Step 14 CLEANUP strips on close.

Common perf instrumentation idioms:
- timing wrappers around hot paths
- mem snapshot before/after suspect block
- counter increments for hot-loop hypothesis
- API call rate vs window size

---

## Step 10 CLASSIFY

| Metric delta | Verdict |
|---|---|
| within ±10% of baseline | `within-budget` |
| metric exceeds budget by 10..50% | `regression` |
| mem grows monotonically over 1h | `leak` |
| CPU saturated + scan rate > expected | `hot-loop` |
| baseline missing or metrics unreadable | `inconclusive` |

Exit codes: 0=within-budget, 1=regression|leak|hot-loop, 2=invalid, 3=inconclusive.

---

## Step 13 FIX (countermeasures)

- immediate: backoff / cache / batch / lock-fix the specific bottleneck
- preventive: rule/test that fails when budget exceeded
- detection: alarm wired to verify_cmd or consistency-daemon

---

## Cross-refs

- `~/.claude/CLAUDE.md` § Epistemic discipline (Causal-claim gate)
- `~/.claude/rules/ship.md` § Observations log
- master plan §3 row "Performance"
- `~/.claude/skills/ship/phases/bot/04-land.md` step 7 (baseline metrics)
