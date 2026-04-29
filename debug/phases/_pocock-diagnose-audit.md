# /debug bug vs Pocock's diagnose — gap audit (2026-04-29)

Source compared: <https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md>

Pocock loop: `reproduce → minimise → hypothesise → instrument → fix → regression-test`

Bernard's `/debug bug` 17-step engine (from `phases/bug.md`):

| Pocock step | Bernard step(s) | Gap? |
|---|---|---|
| **reproduce** | 1 REPRODUCE | none |
| **minimise** | — *(absent)* — | **GAP** |
| **hypothesise** | 6 HYPOTHESIS GEN + 7 EXPECTED-SIGNAL | none, arguably stronger |
| **instrument** | 8 INSTRUMENT | none |
| **fix** | 13 FIX | none |
| **regression-test** | 15 VERDICT-VERIFY (+ 16 LEDGER) | none |

## The MINIMISE gap

After step 1 REPRODUCE, the engine jumps straight to BUILD-MAP (2) / EXECUTION-MAP (3) / DEPENDENCY-MAP (4) — those are about understanding code structure, not shrinking the failing case.

**What MINIMISE adds**: take the working repro and reduce it to the smallest deterministic input that still fails. Strip dependencies, reduce data size, isolate the offending call. Done before hypothesizing.

**Why it matters**:
- Smaller repro = smaller hypothesis search space at step 6
- Forces identification of what's load-bearing vs incidental
- Catches "bug only reproduces with full system running" → reveals the bug isn't in the unit you thought it was

**Concrete shape if added**:
> **Step 1.5 MINIMISE** — reduce `experiments/repro.sh` to the smallest deterministic failing case. Strip env, strip data, strip dependencies one at a time; after each strip, re-run; keep the strip if the bug still reproduces, revert if it doesn't. Halt when no further strip leaves the failure intact. Output: `experiments/repro-min.sh` + `state/minimise-log.md` (what got stripped, what survived).

## Verdict

PARTIAL gap. The 17-step engine's PATTERN ANALYSIS (5) and DEPENDENCY-MAP (4) cover *some* of the same ground (finding what's relevant), but they map the *system*, not the *test case*. A 200-line failing repro and a 10-line failing repro feed both steps differently.

## Recommendation — SHIPPED 2026-04-29

Step 1.5 MINIMISE added between REPRODUCE and BUILD-MAP in `/debug bug` (bug mode only — drift/flaky/performance/wedge unchanged). Artifacts: `experiments/repro-min.sh` + `state/minimise-log.md` templates created on each invocation.

Files touched:
- `phases/bug.md` — added row 1.5 to 17-step engine table
- `bin/debug.py` — `_bug_step` accepts `int | float`; new step block between line 560 and former line 562
- `SKILL.md` — engine description string updated to include MINIMISE

Verified by dry-run smoke test 2026-04-29 17:?? :
```
step 1 REPRODUCE | --dry-run: skipped repro execution
step 1.5 MINIMISE | --dry-run: skipped minimise
step 2 BUILD-MAP | pipeline matches: 0 nodes, 0 edges
```

Followups for a future iteration:
- Extend MINIMISE to flaky mode (loop repro shrinking) and performance mode (metric-sample shrinking) — different shrinking shapes per mode
- Step number "1.5" is a stylistic choice to avoid renumbering the existing 17-step table; if a future refactor renumbers everything, fold into "step 2 MINIMISE" and shift the rest +1

## What NOT to import from Pocock

- Pocock's `diagnose` has no Iron Laws, no observation-isolation labels, no causal-chain depth-check, no 3-fail escalation, no fcntl-locked ledger. Bernard's engine is strictly stronger on epistemic discipline.
- His step list is a 6-word loop; Bernard's is a 17-row table. The verbosity gap is intentional — Bernard's table is the contract for subagents.

Source: pocock/skills MIT, audited at <https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md> on 2026-04-29.
