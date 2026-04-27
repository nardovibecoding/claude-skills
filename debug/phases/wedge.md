# /debug Wedge mode (Group A — symptom-first → kernel-level cause)

Per master plan §3 compression matrix: ALL 17 steps active, plus an extra Step 0.5 KERNEL-CAPTURE specific to wedge mode.

Symptom: process appears alive (`systemctl is-active = active`, `ps` shows it), but JS / userspace stops executing. Log emission rate drops to zero. SIGTERM hangs (90s+ timeout, then SIGKILL). Service appears to "restart on a timer" because it cannot be stopped gracefully.

Sibling to `/debug leak` and `/debug performance`. Use `/debug wedge` when:
- log rate drops to 0 with NO crash signal in journal
- `systemctl stop` or `systemctl restart` triggers 90s+ SIGTERM-then-SIGKILL pattern
- process state in `/proc/PID/status` is `D` (uninterruptible sleep) or `S` for >30s while service looks "active"
- userspace tools say "alive", file-mtime says "fresh", but Telegram/dashboard/output is silent

Use `/debug leak` instead when RSS climb is monotonic + bot exits cleanly via OOM (state=R until kill). Use `/debug performance` for slow-but-alive (state=R, log rate reduced not zero).

---

## Iron Laws

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

---

## Step 0.5 KERNEL-CAPTURE — arm the wedge trace BEFORE doing anything else

The wedge mechanism is hidden from `journalctl` and `top`. The ONLY reliable signal is `/proc/PID/wchan` (the kernel function the main thread is sleeping in) at the moment the wedge fires. By the time you notice, the process may have been SIGKILL'd and the evidence is gone. **Always arm the kernel-trace FIRST, then trigger or wait for the wedge.**

Canonical capture script: `~/.claude/skills/debug/bin/wedge-capture.sh` (auto-installed via skill bin/). It:
1. Runs as the same user as the target service (no sudo needed for `wchan` / `syscall` / per-thread `task/<tid>/wchan`).
2. Polls every 30s for 25 min (covers a typical wedge cycle + buffer).
3. On first transition to state=D OR state=S with log rate <200 lines/30s, emits a **DEEP CAPTURE block**:
   - `/proc/PID/status` excerpt (State, Threads, VmRSS, voluntary/nonvoluntary ctxt switches, signal masks)
   - main thread `wchan`
   - per-thread (tid, state, syscall_nr, wchan) for ALL threads
   - **wchan histogram** across threads (most common kernel function)
   - syscall_nr histogram
   - open file count + cumulative I/O (`/proc/PID/io`)
   - last 50 journal lines from this PID
4. Output: `/tmp/wedge-trace-v3-<PID>.log` — readable by the running user, no root needed.

**Caveat — `/proc/PID/stack` requires CAP_SYS_PTRACE.** Not captured here (would need root + sudoers `bash` allowlist, often unavailable). `wchan` is sufficient for kernel-function identification; only use `stack` if `wchan` returns ambiguous symbols.

Arm command (Bernard's bot example, no sudo path):
```bash
ssh <host> "nohup bash /tmp/wedge-capture.sh <unit> >/dev/null 2>&1 & disown"
```

Read after wedge fires:
```bash
ssh <host> "sed -n '/=== DEEP CAPTURE/,/=== END DEEP CAPTURE/p' /tmp/wedge-trace-v3-*.log"
```

---

## Step 1 REPRODUCE — confirm wedge fingerprint

Before any hypothesis, capture three baselines:

1. **Cycle period.** Read systemd unit lifecycle history:
   ```bash
   ssh <host> "journalctl -u <unit> --no-pager -q | grep -oE 'node\\[[0-9]+\\]:.*Multi-platform' | sort -u"
   ```
   Cross-reference with per-PID start time:
   ```bash
   for pid in <each>; do
     ssh <host> "journalctl _PID=$pid --no-pager -q | grep '<startup banner>' | head -1"
   done
   ```
   Wedge fingerprint = constant inter-restart interval ±30s across N≥3 cycles. Random/clustered intervals → not a wedge, route to `/debug leak` or `/debug bug`.

2. **Log silence window.** For one cycle, find the LAST log line emitted by the wedged PID. Time from last log → next PID start = silence window. Wedges typically have 5-15 min silence before SIGKILL.

3. **systemd termination class.** From journal (needs sudo for `systemd[1]` lines OR root SSH):
   ```
   <ts> systemd[1]: Stopping <unit>...
   <ts+90s> systemd[1]: <unit>: State 'stop-sigterm' timed out. Killing.
   <ts+90s> systemd[1]: Killing process <PID> with signal SIGKILL.
   <ts+90s> systemd[1]: Failed with result 'timeout'.
   ```
   `Result='timeout'` + 90s SIGTERM hang = process unresponsive in kernel. Confirms wedge class.

---

## Step 2 BUILD-MAP — read the unit file + cgroup config

```bash
ssh <host> "systemctl cat <unit>"
ssh <host> "systemctl show <unit> -p MemoryHigh -p MemoryMax -p MemorySwapMax -p RuntimeMaxUSec -p WatchdogUSec -p Restart -p RestartUSec"
```

Flag any of:
- `MemoryHigh < MemoryMax` — soft-throttle window, prime suspect for `mem_cgroup_handle_over_high` wedges (see remediation §A below)
- `--max-old-space-size=<X>` close to or below MemoryHigh — V8 grows toward the throttle boundary every cycle
- `MemoryMax` set without `OOMScoreAdjust` — kernel will SIGKILL via cgroup OOM but no priority hint
- `Restart=always` + `RestartSec` short — masks the wedge as "auto-recovery", hides the bug for weeks

Also read kernel sysctls:
```bash
ssh <host> "cat /proc/sys/vm/overcommit_memory /proc/sys/vm/swappiness /proc/sys/vm/dirty_ratio"
```

---

## Step 3 EXECUTION-MAP — capture wedge moment

Arm the trace (Step 0.5) and wait for next cycle. Read DEEP CAPTURE. Identify the **main thread wchan**. The wchan symbol is THE root-cause signal. Common wedge-causing kernel functions and their meaning:

| wchan | Meaning | Remediation route |
|---|---|---|
| `mem_cgroup_handle_over_high` | cgroup soft-throttle (MemoryHigh exceeded), kernel parking process to apply pressure | §A — raise MemoryHigh to MemoryMax |
| `do_iobio_lock` / `wait_on_page_bit` / `folio_wait_bit` | blocked on disk I/O (slow disk, frozen mount, page cache reclaim) | §B — investigate disk health, check `iostat`, look for failing block device |
| `sk_wait_data` / `tcp_recvmsg` | network read blocked (peer not sending, dead connection no SO_KEEPALIVE) | §C — set SO_KEEPALIVE on long-lived sockets, audit timeouts |
| `futex_wait_queue` ON MAIN THREAD | userspace mutex deadlock OR Node.js libuv worker thread starvation | §D — flame graph + check libuv pool size |
| `pipe_read` / `pipe_wait` | child process pipe stuck (subprocess hung, parent waiting) | §E — audit subprocess timeout handling |
| `do_wait` | parent waiting for child that never exits | §E |
| `schedule_timeout` | generic sleep — likely benign if other threads still active | not wedge, re-investigate |

Per-thread wchan histogram supports differential diagnosis. If 9/11 threads in `futex_wait_queue` (V8 worker idle pattern) and main in `mem_cgroup_handle_over_high`, the kernel cgroup is the unique culprit.

---

## Step 4 DEPENDENCY-MAP, Step 5 PATTERN ANALYSIS, Step 6 HYPOTHESIS GEN, Step 7 EXPECTED-SIGNAL, Step 8 INSTRUMENT

Identical to `/debug bug` 17-step engine. Hypothesis must be expressed as a wchan signature change ("if root cause = MemoryHigh throttle, then raising MemoryHigh = MemoryMax should make wchan never enter `mem_cgroup_handle_over_high`").

---

## Step 9 RUNTIME-VERIFY — verify hypothesis WITHOUT triggering the wedge

Before deploying any fix, do ONE of:

- **Local repro under `node --inspect`.** Synthesize the load that triggers the wedge in a sandbox. Attach Chrome DevTools at the wedge moment. (Hard for production-only triggers.)
- **fault-injection.** Force the bot to allocate aggressively for ~25min (synthetic memory pressure) under the current cgroup config. If wedge reproduces with same wchan, confirms the trigger. If not, wedge has additional condition.
- **cgroup property reduction.** TEMPORARILY set MemoryHigh = MemoryMax via `systemctl set-property` (live, no restart). Watch for next-cycle wedge. If wedge disappears, root cause confirmed. (Reverts on next daemon-reload of original unit.)

---

## Step 10 CLASSIFY → Step 14 FIX

Map wchan → remediation per §A-§E table. Apply minimal fix. Most common: §A.

### §A. mem_cgroup_handle_over_high → raise MemoryHigh

Edit unit file: change `MemoryHigh=<X>M` to match `MemoryMax=<Y>M` (or remove MemoryHigh entirely). Apply via:
```bash
# Pull current unit
scp <host>:/etc/systemd/system/<unit>.service /tmp/<unit>.service.fetched

# Edit locally (Edit tool or sed)

# Push back via sudoers-allowed install (most pm-style sudoers permit /usr/bin/install)
scp /tmp/<unit>.service.fetched <host>:/tmp/<unit>.service
ssh <host> "sudo -n install -m 0644 -o root -g root /tmp/<unit>.service /etc/systemd/system/<unit>.service && sudo -n systemctl daemon-reload && sudo -n systemctl restart <unit>.service"
```

Verify:
```bash
ssh <host> "systemctl show <unit> -p MemoryHigh -p MemoryMax && cat /sys/fs/cgroup/system.slice/<unit>.service/memory.high"
```

Both should equal MemoryMax (in bytes) after the fix.

### §B-§E

(Stub — populate when first encountered. Each remediation MUST include: minimal unit/code change, falsification condition, post-fix wchan expected histogram.)

---

## Step 16 VERDICT-VERIFY — confirm wedge eliminated

Re-arm Step 0.5 trace against the post-fix PID. Wait 1.5× the original cycle period. Pass conditions:

- No state=D entry past prior wedge moment (uptime > prior_cycle_silence_start + 5min)
- main wchan never enters the function identified in Step 3
- log rate stays > healthy floor (defined in Step 1) for entire window

Fail = wedge re-fires with same OR different wchan. Same wchan → fix incomplete (raise threshold further, or wrong cgroup property targeted). Different wchan → secondary wedge mechanism, restart wedge investigation from Step 3.

**Negative result is informative.** If trace shows wedge AT a different wchan than predicted, document in `experiments/wedge-trace.md`. Do NOT claim verdict.

---

## Step 17 LEDGER

Write to `~/NardoWorld/realize-debt.md` with:
- `mode: wedge`
- `wchan_observed: <kernel_function>`
- `wchan_post_fix: <kernel_function or null>`
- `cycle_period_pre: <Nmin>`
- `cycle_period_post: <Nmin or "no cycle">`
- `unit_property_changed: <name=old → name=new>`

---

## Trigger phrases

- "wedges" / "is wedged" / "keeps wedging"
- "frozen in kernel" / "kernel sleep"
- "D-state" / "uninterruptible sleep" / "process stuck in D"
- "SIGTERM hangs" / "won't shut down" / "graceful-stop hang"
- "every N min restart" + "log rate goes to 0"
- "mem_cgroup_handle_over_high" or any specific wchan symbol
- "process alive but silent"

---

## Today's canonical case (2026-04-27 pm-london)

| step | observed |
|---|---|
| Step 1 | 6 cycles, ~25min ±15s, last log at uptime ~15min, then 10min silence, then SIGKILL |
| Step 2 | `MemoryHigh=1400M`, `MemoryMax=1700M`, `--max-old-space-size=1300` |
| Step 3 | main wchan = `mem_cgroup_handle_over_high`, 9 V8 workers in `futex_wait_queue` |
| Step 14 | edit unit: `MemoryHigh=1400M` → `MemoryHigh=1700M`. install via sudoers `install -m 0644 -o root -g root /tmp/*.service /etc/systemd/system/*` |
| Step 16 | T+25min check: PID stable past prior wedge moment |

Lesson source: `~/.ship/pm-london-heap-leak/experiments/rounds.md` Round 6.
