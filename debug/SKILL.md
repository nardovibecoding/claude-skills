---
name: debug
description: |
  Unified debug skill — Wiring / Bug / Drift / Flaky / Performance / Leak / Race / Wedge / Zombie / Orphan modes.
  Reads Phase 4 graphs (state_registry / pipeline_graph / data_lineage / sync_graph / consistency_registry) read-only.
  Writes verdicts to ~/NardoWorld/realize-debt.md (the realization-debt ledger; lockfile-protected atomic writes).
  Shipped: Wiring (S1) + Bug (S3) + Drift/Flaky/Performance (S8) + Leak + Race + Wedge (kernel D-state diagnosis, 2026-04-27) + ledger view.

  Triggers (verb-first):
    /debug check <feature>          — Wiring mode (B: feature-first → runtime). "is X live", "did we wire X"
    /debug bug "<symptom>"          — Bug mode (A: symptom-first → root cause). 17-step engine. "X is wrong / broken"
    /debug drift <feature>          — Drift mode. "X used to work, now stale"; flags --baseline=<sha-or-iso> --dry-run
    /debug flaky "<symptom>"        — Flaky mode (loop reproducer, race priors). "X sometimes fails"; flags --runs=N --dry-run
    /debug performance <feature>    — Performance mode (latency / hot-loop / CPU). "X is slow / hot"; flags --baseline=<file>
    /debug leak <feature>           — Leak mode (RSS climb / OOM / heap). "X is leaking / OOM / RSS climb / heap exhausted / memory bloat"; flags --baseline=<file>
    /debug race <feature>           — Race mode (producer-consumer schedule mismatch). "X fires but Y is empty"; flags --check-systemd-on=<host>
    /debug wedge <unit>             — Wedge mode (process in kernel D-state, log rate=0, SIGTERM hangs). "X is wedged / frozen in kernel / D-state"; flags --capture-only --read-trace
    /debug critic <target>          — Critic mode (3-agent adversarial review: Reviewer / Critic / Lead). "what's wrong with X", "red team X", "find flaws in X"; flags --quick --diff
    /debug list                     — show realize-debt.md ledger

  Step 1.5 MINIMISE auto-mode (opt-in, all 3 verbs):
    bug:         /debug bug "<symptom>" --auto-minimise --fingerprint=exit:1 [--target=lines|env|files] [--reset-cmd=...]
    flaky:       /debug flaky "<symptom>" --auto-minimise --fingerprint=exit:1 --runs=10 --threshold=0.3
    performance: /debug performance <feature> --auto-minimise --baseline-ms=N --workload-axis=SIZE --workload-low=1 --workload-high=1000
  Common: --max-probes=N (default 100/30) | --strip-glob=<g> (files target) | --strip-env=K1,K2 (env target)
  Engine: Zeller binary-partition ddmin (lib at _lib/minimise.py). When unset, template-stub fallback preserved (zero regression).

  NOT FOR: random fixes (Iron Law forbids), claims without verification (second Iron Law forbids), replacing /ship audit (imports it).
verified_at: 2026-04-26
documents:
  - /Users/bernard/.claude/skills/debug/phases/wiring.md
  - /Users/bernard/.claude/skills/debug/phases/bug.md
  - /Users/bernard/.claude/skills/debug/phases/wedge.md
  - /Users/bernard/.claude/skills/debug/bin/debug.py
  - /Users/bernard/.claude/skills/debug/bin/_disc.py
  - /Users/bernard/.claude/skills/debug/bin/wedge-capture.sh
  - /Users/bernard/NardoWorld/meta/state_registry.json
  - /Users/bernard/NardoWorld/meta/pipeline_graph.json
  - /Users/bernard/NardoWorld/meta/data_lineage.json
  - /Users/bernard/NardoWorld/meta/sync_graph.json
  - /Users/bernard/NardoWorld/meta/consistency_registry.json
  - /Users/bernard/NardoWorld/realize-debt.md
  - /Users/bernard/.ship/master-debug/goals/00-master-plan.md
---

# /debug — unified debug + wiring skill

One mental engine, three entry directions. Subsumes wiring-check, bug-hunting, orphan detection, drift, zombie, performance, flaky modes.

## Realization Checks per verdict (added 2026-04-27 — mirror /ship)

Every `/debug` verb writes a verdict to `~/NardoWorld/realize-debt.md`. Before that write, the verb MUST run the universal Realization Checks from `~/.claude/skills/ship/phases/common/realization-checks.md`:

- **RC-1 (stub markers)** — if the changeset under investigation contains `[stub]`, `TODO:`, `NotImplementedError`, or `step N: <name>` placeholder pattern → degrade verdict to `partial` and tag in ledger as `needs_real_implementation`. Skeleton fixes do NOT count as `wired`.
- **RC-7 (hook-output blocklist)** — if the changeset commits any `.router_log.jsonl`, `.cache/`, `.session.json`, `hook_state*` → BLOCK verdict close (privacy regression).

For verbs that interact with multi-host or public repos:
- **RC-5 (cross-host smoke)** — PM bots, bigd: re-verify on Hel + London if both referenced.
- **RC-6 (cross-repo cross-link audit)** — when /debug runs against a public repo's README claims.

Verbs that interact with installer / sync changes:
- **RC-3 (idempotency)** — re-run installer in sandbox, assert no diff.
- **RC-4 (sync-hook allowlist)** — refuse `git add -A` patterns in any sync script.

Verbs operating purely on a live process with no changeset:
- Skip RC-1/RC-3/RC-4/RC-7 (no diff to scan).
- RC-5/RC-6 still apply if multi-host / public-repo.

Source: 2026-04-27 — /upskill v1 marked shipped while SOP steps 1-6 were stub echoes. Same failure mode threatens any /debug verb closing on stub-shaped fixes.

---

## Iron Laws (shared preamble — see `~/.claude/skills/_iron_laws.md`)

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Source: obra/superpowers (MIT). Both laws apply to all /debug modes; full enforcement spec in shared preamble.

## Trigger routing (per master plan §8)

| User phrase | Mode | Phase file |
|---|---|---|
| "is X live" / "is X wired" / "is X actually running" / "did we wire X" | Wiring (Group B) | `phases/wiring.md` |
| `/debug check <feature>` | Wiring (Group B) | `phases/wiring.md` |
| "X is wrong" / "X is broken" / "X is crashing" / "why isn't X" | Bug (Group A) | `phases/bug.md` |
| `/debug bug "<symptom>"` | Bug (Group A) | `phases/bug.md` |
| `/debug list` | (read-only ledger view) | inline below |
| "X is slow / hot / high CPU / event-loop lag" | Performance (Group A) | `phases/performance.md` |
| "X is leaking / OOM / RSS climb / heap exhausted / memory bloat" | Leak (Group A) | `phases/leak.md` |
| "X used to work, now stale" | Drift (Group A) | `phases/drift.md` |
| "X is flaky / sometimes fails" | Flaky (Group A) | `phases/flaky.md` |
| "X wedged / frozen in kernel / D-state / SIGTERM hangs / process alive but silent" | Wedge (Group A) | `phases/wedge.md` |
| "what's wrong with X" / "red team X" / "find flaws in X" / "attack X" / "critic X" | Critic (Group D) | `phases/critic.md` |
| (daemon-driven, no phrase) | Orphan / Zombie (Group C) | consistency-daemon detector (S5) |
| **2026-05-01 jz-mode concerns verbs** | | |
| `/debug stress <unit>` / "X under load" / "10x stress" / "saturation point" | Stress (Group A — Concern C6) | `phases/stress.md` |
| `/debug cost <unit>` / "X cost vs profit" / "token spend spike" / "tier exhausted" | Cost (Group A — Concern C1) | `phases/cost.md` |
| `/debug risk <unit>` / "Kelly calibration" / "vol estimate stale" / "Brier drift" / "live PnL ≠ backtest" | Risk (Group A — Concern C5) | `phases/risk.md` |

Shipped modes: Wiring (S1) + Bug (S3) + Drift/Flaky/Performance (S8) + ledger view + Stress/Cost/Risk (2026-05-02 — phase files live; verdicts must include `Concern: C<N>` line per debug-triage-gate.py). Zombie / Orphan modes remain daemon-driven (S5 not yet shipped).

## Verbs

### `/debug check <target>`
Wiring mode. `<target>` syntax:
- `<host>:<feature>` — e.g. `london:prewarm`, `hel:kalshi-stream`, `mac:dashboard`
- `<feature>` alone — checks all hosts

Loads `phases/wiring.md`. Returns one of `{wired, partial, not_wired, inconclusive}` + Phase 4 evidence citations + writes a ledger entry.

### `/debug bug "<symptom>"`
Bug mode. Walks the 17-step engine (TRIAGE → REPRODUCE → MINIMISE → BUILD-MAP → EXECUTION-MAP → DEPENDENCY-MAP → PATTERN ANALYSIS → HYPOTHESIS GEN → EXPECTED-SIGNAL → INSTRUMENT → RUNTIME-VERIFY → CLASSIFY → DEPTH-CHECK → ≥3-FAIL ESCALATION → FIX → CLEANUP → VERDICT-VERIFY → LEDGER). Loads `phases/bug.md`.

Flags:
- `--quick` — skip ⚡light steps (Step 4 DEPENDENCY-MAP)
- `--no-chain` — defer Step 11 causal-chain emission (non-prod bugs)
- `--bug-slug=<X>` — override auto-slug derivation
- `--dry-run` — walk all steps non-interactively, emit fixture state without prompting

Per-step artifacts under `~/.ship/<bug-slug>/{state,experiments}/`. Final ledger entry in `~/NardoWorld/realize-debt.md` with `mode: bug`.

### `/debug list`
Reads `~/NardoWorld/realize-debt.md`, returns most-recent 20 entries grouped by status. Read-only, no write.

### `/debug drift <feature>`
Drift mode — was correct, code moved under it, silently stale. Compression matrix per master plan §3 row "Drift" (steps 0,2,3,4,5,7,9,10,13,15,16). Loads `phases/drift.md`. Verdict: `current | stale-soft | stale-hard | inconclusive`. Flags: `--baseline=<sha-or-iso>` (default `30 days ago`), `--dry-run`.

### `/debug flaky "<symptom>"`
Flaky mode — intermittent (race / state-dependent). Reuses 17-step engine with REPRODUCE in loop mode. Output `experiments/flaky-runs.md` table; race-pattern priors auto-seeded (thread-safety, async-order, time-dependent, state-leak, external-API-timing). Loads `phases/flaky.md`. Verdict: `intermittent_low | flaky-confirmed | mostly-broken-not-flaky | inconclusive`. Flags: `--runs=N` (default 10), `--bug-slug=<X>`, `--dry-run`.

### `/debug performance <feature>`
Performance mode — fires correctly but slow / hot loop / leak. All 17 steps active; baseline metrics captured per `~/.claude/skills/ship/phases/bot/04-land.md` step 7. Loads `phases/performance.md`. Verdict: `within-budget | regression | leak | hot-loop | inconclusive`. Flags: `--baseline=<file>`, `--dry-run`.

### `/debug scan` (daemon mode)

Daemon scope (cmd_scan) — runs allowlisted rule-based modes only: wiring/drift live; wedge/leak/performance shipping in S3-S5. Bug/flaky/race NEVER auto-fire (manual symptom required).

Canonical allowlist: `_AUTO_DETECTORS` constant in `bin/debug.py`. Full SPEC at `~/.ship/debug-daemon/goals/01-spec.md` (+ `02-plan.md`).

Flags: `--dry_run` (print summary to stdout, no inbox write), `--verbose`, `--force`. Bare `--<unknown>` raises a clear error (no silent allow).

### `/debug wedge <unit>`
Wedge mode — process appears alive (`systemctl is-active = active`) but JS / userspace stops executing. Log rate drops to 0. SIGTERM hangs 90s+ → SIGKILL. Process state in `/proc/PID/status` is `D` (uninterruptible sleep). Loads `phases/wedge.md`.

Step 0.5 (kernel-capture) arms `bin/wedge-capture.sh` against the live PID — captures `/proc/PID/wchan` + per-thread state + wchan histogram on first D-state entry. The wchan symbol identifies the kernel function the bot is sleeping in (e.g. `mem_cgroup_handle_over_high` = cgroup soft-throttle, `sk_wait_data` = network read blocked).

Verdict: `wedge_eliminated | wedge_persists | wedge_shifted_to_<wchan> | inconclusive`. Flags: `--capture-only` (arm trace and exit, return path to log), `--read-trace=<file>` (skip Step 0.5, parse existing trace).

### `/debug critic <target>`
Critic mode — adversarial 3-agent review (Reviewer / Critic / Lead). On-demand only; never auto-fires. Loads `phases/critic.md`. Replaces standalone `/critic` skill (retired 2026-04-30).

`<target>` syntax:
- file path (e.g. `~/.claude/skills/debug/bin/debug.py`)
- directory (top 20 files by line count, skipping `node_modules`/`__pycache__`/test fixtures)
- commit range (e.g. `HEAD~3..HEAD`)
- `<host>:<feature>` (pipeline_graph.json lookup)
- `--diff` (uses `git diff --staged --name-only`)

Three isolated sub-agents fire in sequence: Reviewer ($1000-incentive prompt; outputs findings tagged by lens + severity), Critic (verdicts each finding with 2x false-dismissal penalty), Lead (symmetric +1/-1 arbiter). Output: 3-section markdown table (Confirmed / Low-confidence / Dismissed-collapsed) + ledger entry with `mode: critic`.

Verdict (top-level): `findings_present | clean | inconclusive`. Sibling JSON at `~/NardoWorld/critic-findings/<R-NNNN>.json` with full findings array.

Flags: `--quick` (skip Critic+Lead, single-agent fallback ~1/3 cost), `--diff` (target = git staged diff), `--run-id=<X>` (override auto run-id).

`bin/debug.py critic` is dispatcher only — no LLM calls in Python. The 3-agent orchestration lives in `phases/critic.md` (in-session execution).

### `/debug race <feature>`
Race-condition mode — feature deploys "successfully" but a producer/consumer schedule mismatch silently drops data. Detected after the bigd 6-daemon ship (Apr 27 2026): bundle assembler ran 4-15s before all daemons finished, capturing 8/18 instead of 18/18. Pure timing race, not a daemon bug.

**Checks (rule-based, no LLM):**
1. **G1 Schedule conflict scan** — for each LaunchAgent / systemd timer / cron entry related to `<feature>`, list scheduled fire time. Flag any pair within ±2min where one consumes another's output.
2. **G2 Producer-consumer chain audit** — find every "produces" file path declared by `<feature>`'s artifact (`.ship/<feature>/state/04-land.md` §Producer-consumer block, or by grep on the feature's run script for `> "$out"` / `write_text` patterns). For each producer, find consumers (greps for the path elsewhere). Confirm chain method is one of `{synchronous_call, done_marker, event_trigger}` — flag `schedule_coincidence` as FAIL.
3. **G3 Failure-mode declaration** — does the artifact spec declare what happens when upstream finishes late? Required: one of `{retry_next_tick, block_with_timeout, degrade_with_warning}`. Anything else (or absent) → FAIL.
4. **G4 Expected-count drift** — when the feature is a NEW producer (added to an existing N-producer system), find every consumer that hardcodes the count (`expected=N`, `for d in (N items)`, `range(N)`, `min=N` flags). Flag any still saying old N.

Loads `phases/race.md`. Verdict: `race_free | race_present_<gate> | inconclusive`. Flags: `--dry-run`, `--check-systemd-on=<host>` (additional remote scan).

**Auto-runs after `/ship` Phase 4 LAND for any feature whose artifact contains a Producer-consumer block.** Standalone invocation when investigating "X fires but Y is empty" symptoms.

## Implementation

`bin/debug.py` is the deterministic entrypoint (rule-based per CLAUDE.md "Rule-based > LLM for local classifiers"). `bin/_disc.py` provides shared discipline writers (observations / rounds / causal-chain / atomic ledger). Skill instructions delegate verb dispatch to that script:

```bash
python3 ~/.claude/skills/debug/bin/debug.py check <target>
python3 ~/.claude/skills/debug/bin/debug.py bug "<symptom>"
python3 ~/.claude/skills/debug/bin/debug.py drift <feature> [--baseline=<sha-or-iso>] [--dry-run]
python3 ~/.claude/skills/debug/bin/debug.py flaky "<symptom>" [--runs=N] [--dry-run]
python3 ~/.claude/skills/debug/bin/debug.py performance <feature> [--baseline=<file>] [--dry-run]
python3 ~/.claude/skills/debug/bin/debug.py wedge <unit> [--capture-only] [--read-trace=<file>]
python3 ~/.claude/skills/debug/bin/debug.py list
```

The script reads Phase 4 JSON files only; no LLM calls. Ledger writes are fcntl-locked + atomic (closes S1 D1). Feature matcher normalizes kebab/camel/snake/lower variants (closes S1 D2). Skill body (this file) explains the model and routing; phase files explain per-mode semantics.

## /ship discipline cross-refs (per master plan §6)

When invoked inside a /ship debug round (N>1 attempts on same bug), the wiring/bug phase files MUST cite:
- `~/.claude/skills/ship/phases/common/observations.md` — every live observation routes here as `[single-point]` / `[N-comparison]` / `[isolation-verified]`
- `~/.claude/skills/ship/phases/common/rounds.md` — round N+1 must log SHA + claimed-vs-actual variables
- `~/.claude/CLAUDE.md` → Causal-claim gate (3-question gate before any causal verb) + Multi-round confound check (premise inheritance)
- `~/.claude/rules/ship.md` → Debug-round isolation discipline + Causal chain completeness

These rules are enforced by the calling /ship phase, not by this skill. /debug provides verdict + evidence; /ship enforces process discipline around the verdict.

## Ledger

All writes to `~/NardoWorld/realize-debt.md` flow through this skill (per master plan §6 — ledger writer ownership). Schema = master plan §9. ID format `R-NNNN`. Append-only. Atomic writes via `bin/_disc.atomic_ledger_append()` (fcntl LOCK_EX + tmpfile + os.replace).
