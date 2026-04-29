# /debug Bug mode (Group A — symptom-first → root cause)

Per master plan §3 compression matrix row "Bug": all ✅ steps run (0, 1, 2, 3, 4 ⚡, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16). DEPENDENCY-MAP step 4 stays light (orphan_registry pre-S5 fallback inherited from S1 wiring.md).

---

## Iron Laws (verbatim from `~/.claude/skills/_iron_laws.md`)

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```
From `obra/superpowers/skills/systematic-debugging` (MIT).

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```
From `obra/superpowers/skills/verification-before-completion` (MIT). Both laws apply to every Bug-mode invocation; Step 6 cannot be skipped (Iron #1), Step 15 cannot be skipped (Iron #2).

---

## Red Flags — STOP and follow process (verbatim from obra-systematic-debugging)

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- "One more fix attempt" (when already tried 2+)
- Each fix reveals new problem in different place

ALL of these mean: STOP. Return to Step 1.

---

## Common Rationalizations table (verbatim from obra-systematic-debugging)

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |

---

## 17-step engine

| # | Step | Source | Output artifact | Schema |
|---|---|---|---|---|
| 0 | TRIAGE | new + 5whys | `state/triage.md` | What/When/Where/Impact (5-Whys problem template); auto bug-slug |
| 1 | REPRODUCE | doraemonkeys + obra Phase 1.2 | `experiments/repro.sh` + exit code | deterministic fail cmd; if non-determ → halt + gather more data |
| 1.5 | MINIMISE | pocock/skills `diagnose` (MIT) | `experiments/repro-min.sh` + `state/minimise-log.md` | shrink `repro.sh` to smallest deterministic failing case; strip env/data/deps one at a time, re-run after each strip; keep when bug survives, revert when it doesn't; halt when nothing else can be removed without losing the failure |
| 2 | BUILD-MAP | Phase 4 L1+L3 (read-only) | inline cite | substring match on pipeline_graph + data_lineage |
| 3 | EXECUTION-MAP | Phase 4 L1+L2 (read-only) | inline cite | substring match on state_registry + sync_graph |
| 4 | DEPENDENCY-MAP | Phase 4 L4 + orphan-sweep (⚡light) | inline cite | consistency_registry signals + pre-S5 fallback for orphan_registry |
| 5 | PATTERN ANALYSIS | obra Phase 2 + Phase 0 Recall | `state/pattern.md` | graph-recall hub_nodes hits + lessons grep + working-example diff |
| 6 | HYPOTHESIS GEN | obra Phase 3.1 (Iron Law #1) | `state/hypotheses.md` | "I think X because Y" — single hypothesis, written down |
| 7 | EXPECTED-SIGNAL | new | `state/hypotheses.md` (per H) | observable predicate per hypothesis |
| 8 | INSTRUMENT | doraemonkeys | code edits w/ `[DEBUG H1]` tags + `#region DEBUG` blocks | sink → `~/.claude/debug.log`; reversible scaffolding |
| 9 | RUNTIME-VERIFY | obra Phase 1.4 + organ_check | `experiments/observations.md` | per-observation `[single-point]` / `[N-comparison]` / `[isolation-verified]` |
| 10 | CLASSIFY | uditgoenka trichotomy | `state/hypotheses.md` (per H) | confirmed / disproven / inconclusive |
| 11 | DEPTH-CHECK / 5-Whys | 5whys | `state/causal-chain.md` | numbered Why chain depth ≤5; root-cause characteristics test (Actionable/Preventable/Fundamental/Verifiable) |
| 12 | ≥3-FAIL ESCALATION | obra Phase 4.5 | `experiments/rounds.md` (round N+1 prereq) | hard halt + Bernard prompt if 3 H disproven |
| 13 | FIX | 5whys + obra Phase 4 | code edit + commit SHA | one change at a time; 3-axis countermeasures |
| 14 | CLEANUP | doraemonkeys | strip `#region DEBUG` blocks; archive `~/.claude/debug.log.<bug-slug>.<ts>` | reversible cleanup |
| 15 | VERDICT-VERIFY | obra verification-before-completion (Iron #2) | `state/verify.md` | run verify cmd in this session, paste full output, THEN claim |
| 16 | LEDGER | new | `~/NardoWorld/realize-debt.md` | mode=bug, status=bug-fixed/abandoned/inconclusive |

---

## Per-mode compression matrix (verbatim from master plan §3)

| Mode | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Bug | ✅ | ✅ | ✅ | ✅ | ⚡ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

`--quick` flag skips ⚡light steps (Step 4 only). `--no-chain` defers Step 11 causal-chain emission for non-prod bugs.

---

## 5-Whys depth-check (Step 11 stop condition)

A true root cause passes all four characteristics:

| Characteristic | Test |
|---|---|
| Actionable | Can we do something about it? |
| Preventable | Would fixing this prevent recurrence? |
| Fundamental | Asking "why" again yields nothing actionable |
| Verifiable | Can we prove this is the cause? |

Backward validation chain (mandatory before declaring root cause):
```
If [Root Cause] is fixed
→ Then [Why 4] wouldn't happen
→ Then [Why 3] wouldn't happen
→ Then [Why 2] wouldn't happen
→ Then [Why 1] wouldn't happen
→ Then [Problem] wouldn't occur
```

If chain breaks at any point, revisit that level — root cause is still a symptom.

---

## Causal-chain template (Step 11 output)

Per `~/.claude/rules/ship.md` § Causal chain completeness — every audit/spec on a bug must produce a numbered chain trigger → observed effect. Every step `[cited file:line]` or `[GAP — unverified, exp:<X>]`. Zero `???` leaps.

```
1. <trigger event> [cited <file:line> | <log/cmd>]
2. <next step in chain> [cited ...]
3. ...
N. <observed effect> [cited ...]
```

A fix brief (Step 13) MUST cite which chain step it closes + a falsification condition. Symptom-level fixes allowed only when Bernard explicitly authorizes skipping root-cause via the `--symptom-fix` (no such flag exists; this is intentional — Iron Law #1 forbids).

---

## /ship discipline cross-refs (verbatim per spec §4)

Bug mode imports — does NOT replace — /ship audit discipline:

- `~/.claude/skills/_iron_laws.md` — both Iron Laws pinned at top of this phase file
- `~/.claude/skills/ship/phases/common/observations.md` — every live observation routes here with isolation label
- `~/.claude/skills/ship/phases/common/rounds.md` — round N+1 logs SHA + variables before next round
- `~/.claude/CLAUDE.md` § Epistemic discipline — Evidence-tagging, Causal-claim gate, Independent re-derivation, Multi-round confound check, Diagnostic-method audit
- `~/.claude/rules/ship.md` § Debug-round isolation discipline + Observations log + Causal chain completeness

These rules travel in-context (CLAUDE.md does not auto-load for subagents nor for /debug invoked inside another skill).

---

## Multi-round protocol

Round N+1 begins ONLY after `experiments/rounds.md` records round N's git SHA + claimed-vs-actual variables. Cite `~/.claude/rules/ship.md` HARD RULE.

If 3+ consecutive `[unisolated]` rounds → escalate to `/ship audit <area>` (per master plan §20 row 14). Current debug method is producing noise, not signal.

---

## Verbs

```
/debug bug "<symptom>"                 — full 17-step engine (default)
/debug bug "<symptom>" --quick         — skip ⚡light steps (Step 4 only currently)
/debug bug "<symptom>" --no-chain      — defer Step 11 causal-chain to manual write
/debug bug "<symptom>" --bug-slug=<X>  — override auto-slug derivation
/debug bug "<symptom>" --dry-run       — walk all steps without prompting; emit fixture state
```

Auto-slug: lowercased, non-alnum → `-`, suffix with timestamp `<symptom-slug>-<YYYYMMDDHHMMSS>` to avoid collision across invocations of same symptom.

Output: per-step JSON to stdout + artifacts written under `~/.ship/<bug-slug>/`. Final verdict in `state/verify.md` + ledger entry in `~/NardoWorld/realize-debt.md`.

---

## Iron-Law self-check before returning verdict (Step 15)

Before printing `bug-fixed`:
- Did Step 9 read fresh evidence in THIS invocation? (not "should be wired", not "was fixed last time")
- Was Step 11 causal chain produced with no `???` leaps?
- Was Step 15 verify cmd run + full output read?

If any answer is no → downgrade verdict to `inconclusive` and do not write `bug-fixed` to ledger.
