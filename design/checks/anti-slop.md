# anti-slop — taste enforcement

Catch generic-AI-design tells. Run unconditionally as `/design` step 7.

## Rules

### A. Accent overuse

**Rule**: accent color used at most TWICE per visible surface.
**Check**: scan emitted view — count accent fills, accent text, accent borders. If >2 per screen/component, fail.
**Fix**: demote secondary uses to neutral.
**Why**: accent loses signal value when sprinkled everywhere.

### B. Density-mood mismatch

**Rule**: density must match direction's mood.
**Check**: compare emitted padding/spacing/line-height vs direction's stated rules.
- `tech-utility` + airy whitespace (>32px section padding internal) = FAIL.
- `editorial-monocle` + cramped grid (rows <40px) = FAIL.
- `soft-warm` + sharp 2px borders = FAIL.
**Fix**: rebuild density to match direction's signature.

### C. AI-cliche detector

Flag any of these, FAIL on hit:

1. **Purple-to-pink gradient** on hero or CTA — ChatGPT-marketing slop signature.
2. **Glassmorphism without rich background** — pointless blur.
3. **"Get Started" overuse** — appears >2× per page = drift. Specific verbs only.
4. **Lorem-ipsum-feel headlines** — "Reimagine X" / "The Future of Y" / "Unlock the power of Z" / "Empower your..." = drift.
5. **Perfect bilateral symmetry** in editorial — drift; editorial wants tension.
6. **Stock-photo "team smiling"** — instant slop.
7. **3-col equal-weight features** with same-style icons = AI-default. Vary at least one visually.
8. **Pricing without numbers** ("Contact for pricing" all tiers) = enterprise-unfriendly.
9. **Onboarding emoji parade** in serious products.
10. **`<input>` with no border AND no underline** — invisible affordance.

### D. Forbidden combinations

Reject these direction × register combos:

- `brutalist` × `glassmorphism` archetype — incompatible aesthetics.
- `academic` register × neon accents — register breaks.
- `civic-formal` register × any animation > opacity fade.
- `enterprise-trust` × decorative illustrations.
- `luxury-editorial` × emoji.
- `editorial-monocle` × consumer-playful register — cultural conflict.

### E. AI design tells (detected in emitted code)

Each tell adds 1 slop-point. Score >3 = FAIL.

- Same 4-corner card style for all card types (no variation).
- Identical icon style for every feature (Lucide default at 24px everywhere).
- "Made with [library]" badge in footer.
- `box-shadow: 0 4px 20px rgba(0,0,0,0.1)` (the universal AI shadow).
- `border-radius: 12px` on absolutely everything.
- Multi-tier pricing where middle tier has a `Recommended` ribbon AND a different bg AND bold border (overdetermined).
- Hero with floating product mockup at slight rotation (-3 to -8deg).
- "We respect your privacy" cookie banner with toggle row.

### F. Voice-register mismatch

If the chosen register is e.g. `luxury-editorial` and the copy contains:
- "Get started"
- "Sign up free"
- Exclamation marks
- Emoji
- "Save 20%"

→ FAIL. Voice must match register lock.

## Output format

```
ANTI-SLOP REPORT — <project>/

A. Accent overuse           PASS (2 uses)
B. Density-mood             PASS
C. AI-cliche                FAIL
   - hero CTA: purple-to-pink gradient detected
   - features: 3 identical Lucide icons at 24px
D. Forbidden combos         PASS
E. AI design tells          3 points (THRESHOLD)
   - 0 4 20 0.1 shadow on every card
   - radius 12px on every component
   - floating mockup at -5deg in hero
F. Voice-register match     PASS

VERDICT: REJECT — fix C + reduce E to <3.
```

## Implementation

Rule-based regex + structural scans, NO LLM (per CLAUDE.md §Rule-based > LLM). Run on emitted CSS / Swift / TSX as static analysis. Source: `nexu-io/open-design` anti-slop rules.
