# DESIGN.md schema — human-readable companion

`DESIGN.md` lives next to `tokens.json` in every project's `design/` folder. It is the prose rationale: WHY each token exists, how to combine them, and what NOT to do. Mirrors `google-labs-code/design.md` spec.

## File structure

YAML frontmatter (machine-parseable token snapshot) + Markdown body (rationale).

```markdown
---
name: <project-name>
direction: <direction-key>
register: <register-key>
brand: <brand-key | null>
last_updated: 2026-04-29
tokens_path: ./tokens.json
renderers: [swiftui | html | extension]
---

# <Project Name> — Design System

## 1. Visual Theme & Atmosphere
[1-3 paragraphs. What this design FEELS like. Reference register + direction.]

## 2. Color Palette & Roles
- Brand: ...
- Surface: ...
- Text: ...
- Semantic: ...
[Each color cites token name + hex + role.]

## 3. Typography Rules
- Headline: <font> @ <weight>, line-height <lh>
- Body: ...
- Code: ...

## 4. Component Stylings
[Buttons, cards, inputs, nav. Cite tokens.]

## 5. Layout Principles
- Spacing scale: ...
- Grid: ...
- Whitespace philosophy: ...

## 6. Depth & Elevation
[Shadow / border / ring rules.]

## 7. Do's and Don'ts
### Do
- ...
### Don't
- ...

## 8. Responsive Behavior
[Breakpoints + collapse strategy. Skip if SwiftUI/extension only.]

## 9. Agent Prompt Guide
[Quick color reference + 3-5 example component prompts.]
```

## Required sections

Sections 1-7 mandatory. Section 8 mandatory for `html` renderer, optional for `swiftui`/`extension`. Section 9 mandatory (agents read this for code generation).

## Section ordering (lint rule `section-order`)

The 9 sections must appear in the order above. Reordering breaks brand-file consistency across all 81 vendored brands.

## Frontmatter fields

| field | type | required | notes |
|---|---|---|---|
| `name` | string | yes | project / brand name |
| `direction` | string | yes (or null if brand) | one of 5 direction keys |
| `register` | string | yes | one of 9 register keys |
| `brand` | string\|null | optional | matches `brands/<key>.md` |
| `last_updated` | ISO date | yes | bump on every edit |
| `tokens_path` | rel path | yes | usually `./tokens.json` |
| `renderers` | string[] | yes | which renderers consume this |

## Authoring rules

- Every color cited in body MUST exist in `tokens.json`.
- Every font name cited MUST appear in a `typography` token.
- Hex codes in prose are allowed (e.g. `Terracotta (#c96442)`) but MUST match the token value.
- Never cite a literal hex in a Do/Don't list without naming the token role.
- Do's and Don'ts: each entry one sentence, action-first.

## Tone guide

Prose density matches the brand register. Examples from vendored brands:

- `apple.md` — measured, technical-editorial, "precision editorial system"
- `claude.md` — warm, literary, "literary salon reimagined as a product page"
- `linear-app.md` — clipped, opinionated, technical

Match the register's voice — civic-formal section 1 reads bureaucrat-clear; underground-zine section 1 reads zine-fragment.

## Lint hooks for DESIGN.md

`checks/lint.md` enforces:
- `section-order` — sections in canonical order
- `missing-frontmatter` — all required fields present
- `prose-hex-mismatch` — hex in prose ≠ hex in tokens.json
- `font-not-in-tokens` — font cited in §3 but missing from `typography` group

## Authoring workflow

1. Write `tokens.json` first.
2. Generate `DESIGN.md` skeleton via `/design refresh` from tokens.
3. Hand-edit prose to match register's voice.
4. Run `/design audit` — lint + anti-slop + self-critique.
5. Commit both files atomically.

## Stranger-test

A new contributor reading only `DESIGN.md` should be able to build a new component without reading `tokens.json` first. Token names + hex + role should be enough.
