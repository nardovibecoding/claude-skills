# self-critique — 5-dimensional review

After every emit, score 1-5 on each dimension. Verdict per dimension. Below 4 = fix-list required.

## Dimensions

### 1. Clarity of hierarchy

**Question**: can the eye land on the most important thing in <1 second?
**5**: clear visual lead, single focal element, supporting items recede.
**3**: works but eye wanders.
**1**: every element competing for attention.
**Fix patterns**: increase scale gap between hero element and rest (1.5×+); demote secondary to muted color/smaller weight; remove decorative competing elements.

### 2. Restraint

**Question**: would removing 20% of the visuals make it stronger?
**5**: nothing left to remove without losing function.
**3**: one or two elements feel decorative-not-functional.
**1**: visual noise, gradients, multiple accents, redundant icons.
**Fix patterns**: drop secondary illustrations; collapse 3-color palette to 2; remove background gradients; pick one decorative move per surface.

### 3. Specificity to surface

**Question**: would this look the same on any project? (bad) Or is it tuned to THIS thing? (good)
**5**: unmistakably this brand/register/direction. Generic-AI smell absent.
**3**: register evident but generic in details.
**1**: looks like a Vercel template. Could be anyone.
**Fix patterns**: add register signature moves (mono pill for startup-techy, hairline rule for editorial, ring shadow for soft-warm, redacted box for cyber-streetwear); tune copy voice; avoid Lucide-default icons.

### 4. Token discipline

**Question**: any literal values bypassing tokens? Any off-scale magic numbers?
**5**: every value via token reference. Lint clean.
**3**: 1-2 literals slipped in (timestamps, debug-only).
**1**: hex literals everywhere, off-scale spacings, hardcoded fonts.
**Fix patterns**: re-run `checks/lint.md` rules 8/9/10; replace literals with token refs.

### 5. Cultural register coherence

**Question**: does the work read as the chosen register, or drift toward "default AI startup"?
**5**: a stranger could identify the register from the design alone.
**3**: register present but diluted.
**1**: drifted into generic SaaS template territory.
**Fix patterns**: re-read the chosen register's `registers/<key>.md`; verify all "Forbidden moves" absent; verify ≥2 "Allowed moves" signature elements present; tune copywriting voice.

## Output format

```
SELF-CRITIQUE — <project>/<surface>

1. Clarity of hierarchy        4/5  good — single hero focal works, but secondary CTA fights primary
   FIX: ghost-style secondary OR move below fold
2. Restraint                   3/5  one decorative gradient + 3 accent uses
   FIX: remove gradient, demote 3rd accent to muted
3. Specificity to surface      4/5  startup-techy register evident
   FIX: none required
4. Token discipline            5/5  lint clean
5. Cultural register           4/5  voice slightly off — "Get started" should be "Open the docs"
   FIX: copy edit hero CTA

OVERALL: 4.0/5  — 2 quick fixes before ship.
```

## Verdict thresholds

- All 5 ≥ 4: **SHIP**.
- Any 1 score < 4: **FIX FIRST**, re-run.
- Any score = 1: **REJECT EMIT**, return to plan.

## Honest grading

Don't grade nice. Grading 5/5 on every dimension = critique failure. Self-critique exists to catch the assistant's blind spots. If unsure between 3 and 4, pick 3 and document the doubt.

## Combine with anti-slop

Anti-slop catches generic AI tells (binary fail). Self-critique catches taste calibration (graded). Both run unconditionally. Lint catches contract violations. Three-stage gate.
