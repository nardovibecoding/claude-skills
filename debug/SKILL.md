---
name: debug
description: |
  Unified debug skill — Wiring / Bug / Drift / Flaky / Performance / Zombie / Orphan modes.
  Reads Phase 4 graphs (state_registry / pipeline_graph / data_lineage / sync_graph / consistency_registry) read-only.
  Writes verdicts to ~/NardoWorld/realize-debt.md (the realization-debt ledger; lockfile-protected atomic writes).
  Shipped: Wiring (S1) + Bug (S3) + Drift/Flaky/Performance (S8) + ledger view.

  Triggers (verb-first):
    /debug check <feature>          — Wiring mode (B: feature-first → runtime). "is X live", "did we wire X"
    /debug bug "<symptom>"          — Bug mode (A: symptom-first → root cause). 17-step engine. "X is wrong / broken"
    /debug drift <feature>          — Drift mode. "X used to work, now stale"; flags --baseline=<sha-or-iso> --dry-run
    /debug flaky "<symptom>"        — Flaky mode (loop reproducer, race priors). "X sometimes fails"; flags --runs=N --dry-run
    /debug performance <feature>    — Performance mode (latency / hot-loop / CPU). "X is slow / hot"; flags --baseline=<file>
    /debug leak <feature>           — Leak mode (RSS climb / OOM / heap). "X is leaking / OOM / RSS climb / heap exhausted / memory bloat"; flags --baseline=<file>
    /debug race <feature>           — Race mode (producer-consumer schedule mismatch). "X fires but Y is empty"; flags --check-systemd-on=<host>
    /debug list                     — show realize-debt.md ledger

  NOT FOR: random fixes (Iron Law forbids), claims without verification (second Iron Law forbids), replacing /ship audit (imports it).
verified_at: 2026-04-26
documents:
  - /Users/bernard/.claude/skills/debug/phases/wiring.md
  - /Users/bernard/.claude/skills/debug/phases/bug.md
  - /Users/bernard/.claude/skills/debug/bin/debug.py
  - /Users/bernard/.claude/skills/debug/bin/_disc.py
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
| (daemon-driven, no phrase) | Orphan / Zombie (Group C) | consistency-daemon detector (S5) |

Shipped modes: Wiring (S1) + Bug (S3) + Drift/Flaky/Performance (S8) + ledger view. Zombie / Orphan modes remain daemon-driven (S5 not yet shipped).

## Verbs

### `/debug check <target>`
Wiring mode. `<target>` syntax:
- `<host>:<feature>` — e.g. `london:prewarm`, `hel:kalshi-stream`, `mac:dashboard`
- `<feature>` alone — checks all hosts

Loads `phases/wiring.md`. Returns one of `{wired, partial, not_wired, inconclusive}` + Phase 4 evidence citations + writes a ledger entry.

### `/debug bug "<symptom>"`
Bug mode. Walks the 17-step engine (TRIAGE → REPRODUCE → BUILD-MAP → EXECUTION-MAP → DEPENDENCY-MAP → PATTERN ANALYSIS → HYPOTHESIS GEN → EXPECTED-SIGNAL → INSTRUMENT → RUNTIME-VERIFY → CLASSIFY → DEPTH-CHECK → ≥3-FAIL ESCALATION → FIX → CLEANUP → VERDICT-VERIFY → LEDGER). Loads `phases/bug.md`.

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
