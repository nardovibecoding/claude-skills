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

## Recommendation

If shipping a /debug bug v2, add explicit MINIMISE between REPRODUCE and BUILD-MAP. Cost: ~30 min spec work + an `experiments/repro-min.sh` artifact in the bug-slug dir. Upside: less wrong-direction investigation on long repros.

NOT shipping today — flagged for next /debug iteration. This file lives at `phases/_pocock-diagnose-audit.md` so the bug-mode owner can see it next time the engine is touched.

## What NOT to import from Pocock

- Pocock's `diagnose` has no Iron Laws, no observation-isolation labels, no causal-chain depth-check, no 3-fail escalation, no fcntl-locked ledger. Bernard's engine is strictly stronger on epistemic discipline.
- His step list is a 6-word loop; Bernard's is a 17-row table. The verbosity gap is intentional — Bernard's table is the contract for subagents.

Source: pocock/skills MIT, audited at <https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md> on 2026-04-29.
