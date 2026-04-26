# /debug Flaky mode (Group A — symptom-first → cause, loop reproducer)

Per master plan §3 compression matrix row "Flaky": ALL 17 steps active, with REPRODUCE in loop mode.

Symptom: "X is flaky / sometimes fails". Race / state-dependent / external-API timing.

---

## Iron Laws (verbatim from `~/.claude/skills/_iron_laws.md`)

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

---

## Engine reuse

Flaky mode reuses the S3 17-step engine via shared `_run_engine(symptom, mode='flaky', flags)`. Cmd_bug behavior is unchanged (regression invariant — verified post-ship).

---

## Loop semantics (Step 1 REPRODUCE delta)

- Run reproducer N times (default `--runs=10`).
- Per-run record: `(run#, outcome, fingerprint_hash)`.
- Output table → `~/.ship/<bug-slug>/experiments/flaky-runs.md`:
  ```
  | run | outcome     | fingerprint   |
  |---|---|---|
  | 1   | pass        | <sha8>        |
  | 2   | fail        | err-A-<sha8>  |
  ...
  ```
- Fingerprint frequency table — count distinct failure modes by hash.

In `--dry-run` mode, synthesize 10 fixture rows mixing pass/fail to exercise the path.

---

## Hypothesis priors (Step 6 GEN auto-seeded)

Race-pattern set:
- `H1: thread-safety` — concurrent access without lock
- `H2: async-order` — promise resolution order non-deterministic
- `H3: time-dependent` — clock skew, timeout, scheduling jitter
- `H4: state-leak` — prior run's state bleeds into next
- `H5: external-API-timing` — upstream provider variance

These are starting points; Step 6 still requires a single primary hypothesis "I think X because Y" per Iron Law #1.

---

## Step 10 CLASSIFY (Flaky-specific verdict thresholds)

| Failures / 10 runs | Verdict | Action |
|---|---|---|
| <2 | `intermittent_low` | log + monitor; no escalation |
| 2..7 | `flaky-confirmed` | continue 17-step engine to root cause |
| >7 | `mostly-broken-not-flaky` | abort flaky mode, re-run as `/debug bug` |

Exit codes: 0=intermittent_low, 1=flaky-confirmed, 4=mostly-broken-not-flaky, 2=invalid, 3=inconclusive.

---

## Multi-round protocol

Flaky mode benefits most from `~/.claude/rules/ship.md` § Debug-round isolation. Each loop iteration appended to `experiments/observations.md` as `[single-point]`. After N runs, the aggregate becomes `[N-comparison, N=10]` if all-else-equal preserved.

---

## Output

JSON to stdout + `experiments/flaky-runs.md` + ledger entry.

---

## Cross-refs

- `~/.claude/CLAUDE.md` § Epistemic discipline
- `~/.claude/rules/ship.md` § Observations log + Debug-round isolation
- master plan §3 row "Flaky"
