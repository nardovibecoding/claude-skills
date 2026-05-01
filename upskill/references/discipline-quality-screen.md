# /upskill — Discipline-quality screen (added 2026-05-01)

Added to /upskill Step 7 (extract subroutine) AFTER security gate, BEFORE install. Screens external skill candidates against the 17 active disciplines from `~/.claude/rules/disciplines/_index.md`. Rejects skills that violate ≥3 disciplines or any HIGH-$ discipline.

Source: 2026-05-01 discipline scaffolding session. Backed by /extractskill being folded into /upskill (single install path via `scripts/extract.py`).

---

## Scoring rubric — 17 discipline checks

For each candidate skill (read SKILL.md + scripts/ + references/), answer YES/NO/N-A:

| # | check | YES if | NO if | severity |
|---|---|---|---|---|
| Q1 (D1) | SSOT — does skill avoid creating cache/mirror files for state already stored elsewhere? | no parallel state stores | spawns its own cache without invalidation hook | HIGH |
| Q2 (D2) | Idempotency — are mutating operations idempotent under replay? | retry-safe operations | side-effecting calls without idempotency-key | HIGH-$ |
| Q3 (D3a) | Schema-as-contract — do JSONL/log emits have declared schema? | uses zod / typed | string-interpolation logs | MEDIUM |
| Q4 (D3b) | RED/USE coverage — does long-running daemon emit Rate/Errors/Duration? | yes for daemons; N-A for one-shot | daemon with no metrics | MEDIUM |
| Q5 (D4) | Two-phase deprecation — when removing things, deprecate-then-delete? | warns before deletes | direct deletes / silent removals | MEDIUM |
| Q6 (D5) | Lifecycle pair — every open/lock/subscribe has paired close/release/unsub | all paths matched | half-open lifecycles | HIGH |
| Q7 (D6) | Live-truth — claims about live state cite live observation? | reads systemctl/launchctl/git rev-parse | trusts file mtime / cached state | HIGH |
| Q8 (D7) | Root-cause-first — debug paths investigate before retrying? | escalates root-cause | flag-tweak-retry loop | HIGH |
| Q9 (D8) | Bounded queue — long-lived collections have bounded capacity? | explicit cap or prune | unbounded Map/Array growth | HIGH |
| Q10 (D9) | Timeout — every external call has explicit timeout? | AbortSignal/timeout used | bare await fetch | HIGH |
| Q11 (D10) | Illegal states — TS strict mode + no `as any` write-bypass? | type-safe internal mutation | `(x as any).field=` patterns | HIGH |
| Q12 (D11) | Errors-as-values — fallible ops return Result, no swallow catch | typed error returns | `catch {}` empty bodies | HIGH |
| Q13 (D12) | Anti-AI-slop — no hallucinated imports, no clone-padding, no sycophant guards | clean code | bloated boilerplate / un-justified defensive code | MEDIUM |
| Q14 (D13) | Lesson-pipeline — if skill writes lessons, deduplicates? | uses BM25 dedup or skips | spams lesson dir | LOW |
| Q15 (D14) | Quantitative invariants — if skill manages money/limits, asserts? | runtime assertions | trust-only | HIGH-$ |
| Q16 (D15) | Permission-gate — dangerous ops gated by capability flag? | DRY_RUN-style guards | unconditional execution | HIGH-$ |
| Q17 (D16) | Numeric precision — money in int cents, NaN containment? | ints + epsilon compare | floats + raw === | HIGH-$ |

## Concern axes — 7 additional checks (added 2026-05-01 jz-mode)

Per `~/.claude/rules/concerns-taxonomy.md`. Concerns ≠ disciplines (orthogonal quality axes).

| # | check | YES if | NO if | severity |
|---|---|---|---|---|
| Q18 (C1) | Cost — skill respects token budget / declares per-invocation $ cost? | budget caps documented | unbounded LLM/API calls | HIGH-$ |
| Q19 (C2) | Resilience — degrades gracefully on upstream failure? | circuit-breaker / retry policy | bare external calls | MEDIUM |
| Q20 (C3) | Behavioral correctness — has spec/snapshot/golden-output validation? | output verified against ref | un-tested transformation | MEDIUM |
| Q21 (C4) | External drift — declares upstream APIs + version-pins? | locked deps + cited APIs | hardcoded floating refs | MEDIUM |
| Q22 (C5) | Model accuracy — if skill calls LLM/ML, evaluates output quality? | scoring loop | trust-without-eval | MEDIUM |
| Q23 (C6) | Performance — cold-start + p99 documented? | latency claimed and tested | unverified perf | LOW |
| Q24 (C7) | Security — credential handling / scope-of-access declared? | uses env / keychain, scoped | hardcoded keys | HIGH-$ |

## Verdict thresholds (updated)

Total: 17 D-checks + 7 C-checks = **24 checks**.

- **PASS-INSTALL**: ≥20/24 YES, all HIGH-$ checks (Q2, Q15, Q16, Q17, Q18, Q24) PASS, ≤3 NO total.
- **EXTRACT-ONLY** (write to `~/NardoWorld/atoms/extracted-patterns/<slug>-<date>.md`): 14-19 YES, no HIGH-$ NO. Saves the IDEA without installing flawed code.
- **REJECT** (do not install, do not extract): <14 YES OR any HIGH-$ NO.

## Integration into Step 7

In `~/.claude/skills/upskill/scripts/extract.py`:

```python
# AFTER security_auditor PASS, BEFORE install:
from discipline_screen import screen_candidate
verdict = screen_candidate(skill_dir, scoring_rubric_path="~/.claude/skills/upskill/references/discipline-quality-screen.md")

if verdict.action == "REJECT":
    print(f"REJECTED: {verdict.failed_checks} (HIGH-$ violations: {verdict.dollar_violations})")
    abort()
elif verdict.action == "EXTRACT-ONLY":
    write_to_atoms(skill_dir, verdict.summary)
    print(f"EXTRACT-ONLY: idea saved, code NOT installed (failures: {verdict.failed_checks})")
elif verdict.action == "PASS-INSTALL":
    proceed_to_install()
```

The `discipline_screen.py` module (TBD — separate /ship slice) implements the 17 yes/no checks. Until shipped, the rubric serves as a manual checklist Bernard runs during /upskill review.

## Manual rubric form (until automated)

When /upskill prompts adopt-gate `Y/n/skip`, output the rubric as a 17-line checklist:

```
Discipline screen for <skill-slug>:
Q1  D1  SSOT (no parallel state):                       [Y/N/?]
Q2  D2  Idempotency (HIGH-$):                           [Y/N/?]
...
Q17 D16 Numeric precision (HIGH-$):                     [Y/N/?]
Score: X/17 YES, Y HIGH-$ violations.
Verdict: PASS-INSTALL | EXTRACT-ONLY | REJECT
Adopt? [Y/n/skip]
```

Bernard fills in Y/N/? per his read of the candidate's SKILL.md. ? = "uncertain, defer to security_auditor". Until automated, this stays human-gated.

## Receipt logging

PASS-INSTALL writes a discipline-receipt entry per discipline that PASSED with high confidence:

```json
{"ts": "2026-05-01T08:30:00Z", "discipline": "D2", "source": "/upskill", "skill": "<slug>", "verdict": "PASS", "method": "manual-review"}
```

Path: `~/.claude/scripts/state/discipline-receipts.jsonl`.

REJECT writes a receipt logging WHICH discipline rejected — useful for cross-skill statistics.

## Cross-references

- /upskill SKILL.md §7 extract subroutine: `~/.claude/skills/upskill/SKILL.md:46-50`
- Existing security gate: `~/.claude/skills/upskill/scripts/skill_security_auditor.py`
- Discipline index: `~/.claude/rules/disciplines/_index.md`
- Invariant taxonomy: `~/.claude/rules/invariant-taxonomy.md`

Source: 2026-05-01 discipline scaffolding session.
