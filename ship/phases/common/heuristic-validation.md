# Heuristic validation template

Used by /ship Phase 2 PLAN + Phase 3 EXECUTE when the deliverable is a regex / classifier / scorer / router / pattern-matcher / threshold / promotion-criteria.

Author-generated retro-test ≠ validation. Held-out corpus required before phase-close.

---

## Required experiment file

`/Users/bernard/.ship/<slug>/experiments/heuristic-validation.md`

Two measurements, both with `[cited cmd]` evidence:

### 1. RECALL (positives)

- Sample ≥30 hand-labeled true positives from a corpus the heuristic-author did NOT see while authoring.
- Run the heuristic against each. Count IDs hit (≥1 axis = hit).
- `recall = IDs hit / total TPs`. Target ≥80%. Reject phase if <60%.
- For misses: cluster by shape. If a recurring shape (≥3 misses) is uncovered, propose a new axis and re-measure.

### 2. PRECISION (negatives + false-positive rate)

- Sample ≥200 random items from the same corpus with NO seed-phrase filter (must include innocent text).
- Run the heuristic. Count hits.
- Hand-classify each hit as TP (real) vs FP (innocent fired wrongly).
- `fp_rate = FPs / total hits`. Target <10%. Reject phase if >30%.
- For high-FP axes: propose tightening (additional anchor word, negative lookbehind, contradicting register requirement).

---

## Coverage map (top of report)

- Total corpus size (file count + record count, `[cited wc -l]`)
- Window applied (e.g. 30d mtime filter, `[cited find -mtime]`)
- Hand-labeled TP count
- Random-sample size
- Regex hits in random sample
- Confidence label per measurement: HIGH (≥30 TPs and ≥200 random) / MEDIUM (shorter)

---

## Banned phrasings

- "X/X retro-test PASS" when the X positives were authored alongside the heuristic
- "Confidence HIGH" without the held-out corpus measurement
- "regex catches all known cases" without `[cited cmd]` count

## Allowed phrasings

- "X/X retro-test against author-generated examples (tautological by construction); held-out validation: recall N% (M/Q TPs), FP M% (P/H hits)"
- "[GAP — held-out validation pending, exp: see this template]" if held-out is deferred to a later phase

---

## Verdict labels

- **HEURISTIC-PASS** — recall ≥80% AND FP <10%. Ship.
- **HEURISTIC-NEEDS-AXIS-N** — recall <80% with a recurring missed shape; add the proposed axis, re-measure.
- **HEURISTIC-NEEDS-TIGHTEN** — FP >10% on a specific axis; tighten that axis, re-measure.
- **HEURISTIC-PIVOT** — recall <40% AND FP >30%; the heuristic is structurally wrong, redesign before continuing.

---

## Source

ship-bigd-lessons 2026-04-27. Phase 2 closed PASS on 4/4 retro-test + 8/8 phrasing robustness. Held-out 30d corpus (4234 user msgs): recall 19% (8/42 TPs), FP rate 71% (5/7 hits). The 4 retro-test examples were the same examples used to author the 5-axis regex — passing them was guaranteed by construction. Held-out measurement caught the gap pre-EXECUTE.
