# DTCG lint rules — 10 checks

Run unconditionally as `/design` step 6. Reject emit if any rule fails.

## Rules

### 1. `broken-ref`

**Trigger**: a token's `$value` references `{group.token}` that doesn't exist.
**Check**: parse all `{...}` strings in tokens.json, verify each path resolves to a defined token.
**Fix**: rename the ref OR define the missing token.

### 2. `missing-primary`

**Trigger**: tokens.json missing `color.brand.primary` (or designated brand accent).
**Check**: assert `color.brand.primary` exists with valid `$value`.
**Fix**: add the token. Every project needs a designated primary accent.

### 3. `contrast-ratio`

**Trigger**: text-on-background pairs fail WCAG AA (4.5:1 normal, 3:1 large ≥18px).
**Check**: for every pair `(text.primary, surface.bg)`, `(text.secondary, surface.bg)`, `(button.text, button.bg)`, compute relative luminance ratio. AAA is 7:1 (recommended for civic-formal register).
**Fix**: darken/lighten one side until ratio passes. NEVER ignore.

```js
function contrast(hex1, hex2) {
  const l1 = relLuminance(hex1);
  const l2 = relLuminance(hex2);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}
```

### 4. `orphaned-tokens`

**Trigger**: a token defined but referenced nowhere (not in renderer output, not in another token's ref).
**Check**: grep emitted CSS/Swift/etc + all token refs. Find tokens with zero references.
**Fix**: remove the token, OR document why it's reserved (`$description: "reserved for v2"`).

### 5. `section-order`

**Trigger**: DESIGN.md sections out of canonical order.
**Check**: parse `## N. <title>` headings, verify sequence: 1.Visual Theme → 2.Color → 3.Typography → 4.Components → 5.Layout → 6.Depth → 7.Do/Don't → 8.Responsive → 9.Agent Prompt Guide.
**Fix**: reorder sections. The 81 vendored brand files all conform — keep the convention.

### 6. `color-count`

**Trigger**: >6 base color tokens OR >12 total color tokens (including shades).
**Check**: count `$type:"color"` tokens. Group by base name (e.g. `gray-100, gray-200` count as 1 base + 2 shades).
**Fix**: consolidate similar shades. Beyond 12 = decoration drift.

### 7. `font-count`

**Trigger**: >2 unique `fontFamily` values across tokens.
**Check**: extract all `$type:"fontFamily"` values + composite typography fontFamily refs. Count uniques.
**Fix**: drop the third font. Sans + serif OR sans + mono. NEVER three.

### 8. `hardcoded-hex-in-renderer-output`

**Trigger**: literal `#rrggbb` or `rgb()` / `rgba()` in renderer output files (`*.swift`, `*.css`, `*.tsx`).
**Check**: regex `#[0-9a-fA-F]{3,8}\b` and `(?:rgba?|hsla?)\(` over emitted files. Whitelist generated `tokens.css` / `Tokens+Color.swift`.
**Fix**: replace literal with token reference (`var(--color-brand)`, `Color.brandPrimary`).

### 9. `off-scale-spacing`

**Trigger**: `padding`, `margin`, `gap` values not in the defined spacing scale.
**Check**: extract numeric px/rem values from CSS/JSX/Swift. Verify each is in `space.*` token set.
**Fix**: snap to nearest scale value. Magic numbers (e.g. `padding: 13px`) forbidden.

### 10. `off-scale-radius`

**Trigger**: `border-radius` / `cornerRadius` values not in radius scale.
**Check**: similar to off-scale-spacing.
**Fix**: snap to defined `radius.*` token.

## Output format

```
LINT REPORT — <project>/design/

PASS  broken-ref          0 issues
PASS  missing-primary     present
FAIL  contrast-ratio      2 issues
       - text.secondary on surface.bg → 3.8:1 (need 4.5:1)
       - button.text on button.bg → 2.9:1 (need 4.5:1)
PASS  orphaned-tokens     0 orphans
PASS  section-order       canonical
PASS  color-count         5 base, 9 total
PASS  font-count          2 families
FAIL  hardcoded-hex       1 issue
       - src/components/Card.tsx:14 → "#0071e3"
PASS  off-scale-spacing
PASS  off-scale-radius

VERDICT: REJECT (2 contrast failures, 1 hardcoded hex)
```

## Implementation hint

Rule-based, no LLM (per CLAUDE.md §Rule-based > LLM). Pure JS/Python script. Style Dictionary v4 has built-in ref resolution + can plug custom validators. Sources: `aficat/design-linter`, `destefanis/design-lint`.
