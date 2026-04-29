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

## Step 1.5 MINIMISE (performance variant — added 2026-04-29)

After REPRODUCE captures the baseline metrics, MINIMISE shrinks the workload until ONLY the offending metric still busts budget. Pocock/skills `diagnose` (MIT) — performance shape.

Differs from bug-mode MINIMISE: not "still fails" but "still over budget on the metric that triggered the symptom." Goal is isolating the load-bearing axis (concurrency, payload size, dataset rows, request rate).

- Identify which baseline metric is over budget (e.g. `mem_growth_1h_pct`, `fill_latency_p99`).
- Shrink the workload along **one axis at a time**: request volume, payload size, concurrency, dataset rows.
- Re-capture the baseline after each shrink.
- KEEP the shrink if the offending metric still busts budget; REVERT if budget recovers.
- Halt when no further shrink leaves the budget bust intact.

Output:
- `experiments/workload-min.sh` — smallest workload that still triggers the perf regression
- `state/minimise-log.md` — per-shrink table: `# | Shrunk | Offending metric | Still over budget? | Decision`

The result tells you which axis the regression depends on — that drives Step 6 HYPOTHESIS.

---

## Step 1.1 INVENTORY — P1-P4 detector pack (shipped 2026-04-29)

Symptom-first inventory. When user types `/debug performance <host>`,
`cmd_performance` fires four detectors via `~/.claude/skills/debug/detectors/run_all`.
Replaces the planned standalone `/debug zombie` and `/debug orphan` verbs — now
they're detectors INSIDE performance, surfaced when user reports a host symptom.

| detector | what it scans | thresholds (mac / hel-london) |
|---|---|---|
| **P1 zombie** | `ps STAT == 'Z'` count | warn ≥10 / ≥1, crit ≥30 / ≥5 |
| **P2 orphan** | `PPID==1 && (defunct OR git-pack pattern)` | warn ≥1 suspicious, crit ≥5 |
| **P3 hot-loop** | sustained `pcpu` over 2 samples 3s apart | warn ≥5 procs ≥5% / ≥1, crit ≥3 procs ≥50% / ≥1 |
| **P4 leak** | top-20 RSS + 30s delta | warn ≥8GB-RSS / ≥800MB, crit ≥16GB / ≥1.5GB |

Each detector writes `<perf_slug>/experiments/p<N>-<name>.md` with verdict, summary,
evidence_cmd, and up to 20 findings. Verdicts feed Step 10 CLASSIFY: any `crit` or
`warn` overrides `inconclusive` and emits `regression`.

P2 was sized for the 2026-04-29 London `git index-pack` orphan incident (32 PPID=1
git-pack procs from sshd disconnect-mid-push). Suspicious pattern list:
`git index-pack`, `git receive-pack`, `git upload-pack`, `<defunct>`.

Host alias resolves from the verb argument: `/debug performance mac|hel|london|local`
treats the bare alias as `detector_host`. `/debug performance hel:kalshi-bot` takes
host from prefix and feature from suffix (existing parse_target shape).

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

---

## UI / native-app perf addendum (added 2026-04-29 from VibeIsland session)

When the symptom is "UI is jerky / animation stutters / button click drops / tab switch freezes" rather than "scan-loop hot / mem grows": classic server-perf metrics (scan rate, fill latency) DO NOT apply. Use this addendum.

### Distinct symptom shapes

| symptom | likely class |
|---|---|
| sustained CPU >5% at idle | classic hot-loop — use top of file |
| **CPU 0% but UI jerks** | SwiftUI invalidation cascade or main-thread block during animation |
| **button click does nothing** | main thread blocked >100ms when click arrived (AppKit coalesces dropped) |
| **animation frame drops** | view re-layout during animation; setContent fired pre-animation; or implicit Charts animation |
| **tab switch freeze** | onAppear cascades trigger N concurrent loads on main |
| **app self-quits silently** | search for `NSApp.terminate` callers; small icons next to Refresh button = mis-click trap |

### Sample DURING action, not idle (HARD RULE)

A 30s sample over an idle window will show low CPU even when the app is jerky. The cost is bursty during interactions. Workflow:

1. Tell user: "do rapid <action> for 30s"
2. `sample <pid> 30 -file /tmp/<slug>-debug.txt`
3. Analyze module breakdown:
   - high `libicucore` → Formatter init storms; cache as `static let`
   - high `Foundation` + `String.contents` → sync file I/O on main; off-load via DispatchQueue
   - high `SwiftUI` / `SwiftUICore` → re-render cascade; reduce @Published surface or LazyVStack
   - high `libsystem_kernel` (kevent / wait) → blocked on Process()/ssh; parallelize or move off main

### Disable-and-retry isolation

When suspect is a heavy framework (Charts, AVKit, MapKit, WebKit), replace with placeholder Text first:

```swift
// [INTERIM <date>] disabled to confirm bottleneck
Text("[<framework> disabled — N items]")
```

If symptom resolves → confirm. Then ship permanent (e.g., hand-drawn `Path` sparkline for Charts).

### Multi-detector inventory (perf-daemon-style scan)

Run as 6 detectors over `Sources/`:

1. **timer_inventory** — every `Timer.scheduledTimer` + `Timer.publish` + `Combine.timer`. Capture cadence, queue, payload.
2. **main_thread_blockers** — `Process()`, `String(contentsOfFile:)`, `JSONSerialization`, ssh, *Formatter() reachable from main thread.
3. **polling_dedup** — same path read by ≥2 callers (e.g. `pipeline_graph.json` read by HelTabView + LondonTabView).
4. **formatter_alloc** — every `*Formatter()` allocation per render frame.
5. **queue_contention** — serial-queue work that mutates @Published → SwiftUI invalidation rate.
6. **live_sample** — sample during 3 distinct windows: idle, during typical timer fire, during user interaction.

Each detector outputs `findings.md` with `[cited file:line]` evidence + severity. Rank by `impact × user-visibility`.

### @Published cascade audit

A 5s timer that calls `self.states = next` on `@Published var states` triggers SwiftUI invalidation across every view that observes the store. With N observers + 5s tick = 0.2N invalidations/sec at idle. During animations, this storm causes frame drops even when no single view is heavy.

Mitigations:
- Widen tick interval (5s → 15s)
- Diff-aware update (only assign if changed)
- Split monolithic store into per-domain stores so observers subscribe narrowly

### Animation pre-content trap (HARD RULE)

When a window resize animates 0.28s+, do NOT call `setContent(...)` BEFORE `reposition(animate: true)`. SwiftUI lays out new content at OLD frame size, then re-lays out on every animation tick (~17 frames at 60fps). Defer content swap to animation completion handler. Mirror collapse-pattern symmetry for expand.

### Stale-build verification (HARD RULE)

If both a packaged `.app` (`/Applications/<Name>.app`) and a debug build (`.build/debug/<Name>`) exist:

```bash
ps -p $(pgrep -f <Name> | head -1) -o command
```

Verify which binary is running BEFORE concluding patches did/didn't help. The packaged `.app` may auto-launch on login or via Dock and run stale code that ignores all live-edit patches. Rebuild + replace the `.app` after patches stabilize.

### Quit-button-mis-click trap

Small icons (≤24px) next to other clickable buttons in app headers are mis-click vectors. If `launchctl print gui/$(id -u)/<label>` shows `runs=N` where N >> manual restart count, suspect: (a) crash loop (check `last exit code`), (b) silent `NSApp.terminate` from accidental click. Add confirmation alert to all destructive UI buttons.

### Cross-refs (UI-perf-specific)

- Apple sample / time profiler in Instruments for deeper drill (when `sample` cmd output ambiguous)
- `~/.ship/vibeisland-event-driven/experiments/perf-scan-findings.md` — example of detector output
- `~/NardoWorld/atoms/vibeisland-charts-framework-perf-2026-04-29.md` — Charts-as-jerk-source canonical lesson
