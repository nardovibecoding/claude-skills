# /debug Leak mode (Group A — symptom-first → cause)

Per master plan §3 compression matrix row "Leak": ALL 17 steps active.

Symptom: "RSS climbs / OOM / heap exhausted / memory bloat / bot keeps restarting from memory pressure".

Sibling to `/debug performance`. Use `/debug leak` when the dominant signal is monotonic memory climb. Use `/debug performance` for CPU/latency/event-loop without memory growth.

---

## Iron Laws

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

---

## Step 1 REPRODUCE — liveness verdict + symptom triage

**Mandatory 3-step liveness protocol before claiming OOM** (per `~/.claude/rules/pm-bot.md` §Liveness verdict):
1. `ssh <host> "systemctl is-active <unit>"`
2. `ssh <host> "journalctl -u <unit> --since '5 min ago' --no-pager | tail -20"`
3. `ssh <host> "systemctl show <unit> -p MainPID -p MemoryCurrent -p ActiveEnterTimestamp"`

**Distinguish OOM vs graceful stop** (lesson 2026-04-27):
- Real OOM: kernel `dmesg` shows "killed process X (cmd) total-vm... anon-rss... oom_score_adj"; or `journalctl` shows `cgroup memory.events high...max...oom_kill`
- Graceful stop: `journalctl` shows `Stopping <unit>` + bot's own `Shutting down...` lines. Memory peak *under* cgroup MemoryMax. Triggered by external SIGTERM (watchdog / dashboard /reboot endpoint / cron / oomd).
- File mtime ≠ activity. RSS climb ≠ OOM (could be normal cold-start load).

**RSS slope baseline** — capture twice with 4-5 min gap, same PID:
```
ssh <host> "systemctl show <unit> -p MainPID -p MemoryCurrent && date -u +%Y-%m-%dT%H:%M:%SZ"
```
Slope ≤ 5 MB/min = bounded. > 15 MB/min = active leak. 5-15 = monitor.

---

## Step 4 BUILD-MAP — call-site verification (§No mental math compliance)

**HARD RULE**: before claiming "remove call at file:line" or "two call sites" or any structural fix, paste evidence:

```
grep -nC 5 '<symbol>' <file>          # context-rich
grep -c '<symbol>' <file>              # count
LSP findReferences <symbol>            # when available, prefer
```

Line-number arithmetic FORBIDDEN. "lines 3282/3283/3284 = 3 call sites" is wrong — that's one call site on consecutive lines. Verify enclosing scope (which function / setInterval / setTimeout contains the call).

Source: 2026-04-27 round-4 brief misread fast-loop call site, 65k tokens burned before strict-execute caught the §0.5 premise failure.

---

## Step 5 EXECUTION-MAP — slow vs fast loop discipline

For long-running services with periodic work, classify each scan/strategy/handler:

| location | typical cadence | who belongs there |
|---|---|---|
| fast-loop (`setInterval` 100-500ms) | 2-10×/sec | arb-trigger, WS-driven, race-sensitive only |
| slow-loop (`while(true) { await sleep(N) }` 60-300s) | 1-5/min | statistical bets, longshot, calibration, edges |
| event-driven (no loop) | on-demand | hooks, dashboard endpoints |

**Misplaced slow strategy in fast loop = #1 hidden leak source.** Each 250ms tick allocates fresh markets/signals/strings even though input data refreshes every 30s+. Fix: throttle to match slowest input refresh.

**Premise audit** (§0.5 inheritance): when prior round claimed "X runs every Yms", grep the actual `setInterval` period AND the throttle constants. Constants can be dead code if config overrides them (e.g. `FAST_INTERVAL_MS=100` constant + `config.fastLoopMs=250` config → constant is dead).

---

## Step 8 INSTRUMENT — heap evidence ladder

In order of preference (fast → slow, mechanical → manual):

1. **`process.memoryUsage()` periodic log** — cheapest. Add 1 line at scan boundary, watch `heapUsed` / `external` / `rss` deltas.

2. **`--heapsnapshot-near-heap-limit=N`** node flag — auto-writes snapshot when V8 heap nears `--max-old-space-size`. **Caveat**: only fires on V8 OOM; useless if external SIGTERM kills before V8 panics. Bot must actually hit its JS heap ceiling.

3. **`SIGUSR2` + `--heapsnapshot-signal=SIGUSR2`** — manual on-demand. **Stalls on >1GB heaps** (uninterruptible disk I/O for 30s+, blocks event loop). Lesson 2026-04-27: produced 0-byte file twice. Use only when heap < 800MB or you can tolerate the freeze.

4. **`node-oom-heapdump`** (Node 20-) or **`--heap-snapshot-on-oom`** (Node 22+) — installs a V8 OOMErrorHandler that captures snapshot **right before** the abort. Strictly better than near-heap-limit for catching the actual final retainer state.

5. **`memlab find-leaks`** (Meta) — diff two snapshots, name the dominant retainer chain. Pair with SIGUSR2 (taken at low + high RSS).

6. **Chrome DevTools Memory tab → Load profile** — manual retainer-graph analysis. Sort by Retained Size, top 5-10 = leak suspects.

When heap snapshot keeps failing (large heap, disk I/O stall, external SIGTERM): switch class. Don't keep trying. Move to slow/fast loop architecture audit instead.

---

## Step 10 CLASSIFY — leak typology

| pattern | verdict | typical fix |
|---|---|---|
| Module-scope `Map<K, V>` keyed by unstable string (`Date.now()`, UUID, random) → never dedupes → unbounded growth | `unstable-key` | stabilize key (drop timestamp suffix), add periodic sweep |
| Module-scope `Map`/`Set` with no eviction, no size cap | `unbounded-collection` | hard size cap (FIFO eviction) or TTL sweep |
| Append-only array (`.push` per event, no `.shift`) | `unbounded-array` | rolling window (cap + shift) or running stats |
| Outer Map key never deleted when inner array empties | `phantom-key` | delete-when-empty after prune step |
| Dynamic `await import()` per tick | `import-microtask` | static import at file top |
| Diagnostic log firing per-event from fast loop | `log-spam` | revert probe / throttle / move to slow path |
| Slow strategy in fast loop allocating per tick | `cadence-mismatch` | throttle to match input refresh, or demote to slow loop |
| Cold-start RSS climbs 15-50 MB/min then plateaus | `cold-start-load` | not a leak; expected for heavy boot (profile cache, large JSONL, etc.) |
| Steady-state climb 1-15 MB/min over hours | `steady-state-leak` | one of patterns above |
| Bot OOM-restart cycle but cgroup peak < MemoryMax | `not-a-leak` | external trigger (watchdog / cron / dashboard /reboot / oomd) |

Exit codes: 0=within-budget, 1=leak (any class), 2=invalid, 3=inconclusive.

---

## Step 13 FIX (countermeasures by class)

- `unstable-key` → drop timestamp/uuid suffix; stable key + 60s sweep
- `unbounded-collection` → hard cap (200-1000 entries) + FIFO eviction; OR `setInterval(() => { for (const [k,v] of m) if (v.until <= now) m.delete(k); }, 60_000).unref()`
- `unbounded-array` → rolling window (`if (a.length > N) a.shift()`)
- `phantom-key` → after pruning inner: `if (inner.length === 0) outer.delete(key)`
- `import-microtask` → static `import { fn } from "./mod.js"` at top
- `log-spam` → revert (if diagnostic) or last-logged-ts gate
- `cadence-mismatch` → `if (now - lastX > 30_000) { ...; lastX = now; }` wrapper, match input refresh rate
- `cold-start-load` → no fix needed; raise `--max-old-space-size` if necessary
- `steady-state-leak` → one of above
- `not-a-leak` → audit external trigger (watchdog log, cron, dashboard endpoint, oomd)

---

## Step 14 CLEANUP

- Strip diagnostic probe logs added during investigation (don't leave probes in fast loop)
- Update stale prose comments touching changed cadence/architecture (per CLAUDE.md §Stale-prose)
- Verify `--max-old-space-size` aligns with cgroup `MemoryMax` (V8 limit < cgroup max - native overhead)

---

## Step 16 VERDICT-VERIFY

Falsification gate (T+5 min after restart):
- Build green ✓
- New MainPID active ≥ 60s ✓
- RSS slope T+0 → T+5 ≤ 5 MB/min (or strictly less than pre-fix slope)
- No regression in scan/strategy log frequency (throttle didn't break feature)

If gate fails: write `realization-failed-<round>-<ts>.md` with readings + journal excerpt. **Do not declare resolved without T+30 min sustained slope check.**

---

## Cross-refs

- `~/.claude/CLAUDE.md` §Epistemic discipline (Causal-claim gate, Independent re-derivation, Diagnostic-method audit) + §No mental math (call-site counting)
- `~/.claude/rules/ship.md` §Realization Check + §Observations log + §Causal chain completeness + §Debug-round isolation
- `~/.claude/rules/pm-bot.md` §Liveness verdict protocol
- `~/.claude/rules/agents.md` §LSP-first
- master plan §3 row "Leak"
- `~/.claude/skills/ship/phases/bot/04-land.md` step 7 (baseline metrics)
- Lessons distilled from pm-london heap-leak hunt 2026-04-27 (5 rounds: gateSkipMemo → same-class caps → slow-loop sleep clamp → probe revert → fast-loop strategy throttle)
