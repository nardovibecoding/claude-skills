# editorial-monocle — black + 1 accent, print-style

Two-column print rhythm. Serif display + serif body. The vibe of Monocle, The New Yorker online, Are.na editorial.

## OKLch palette (12 swatches)

```json
{
  "ink":         { "$type":"color", "$value":"oklch(0.18 0.00 0)"   },  // near-black
  "paper":       { "$type":"color", "$value":"oklch(0.97 0.005 90)" },  // warm off-white
  "paper-2":     { "$type":"color", "$value":"oklch(0.93 0.008 90)" },  // toned card
  "rule":        { "$type":"color", "$value":"oklch(0.30 0.00 0)"   },  // hairline
  "muted":       { "$type":"color", "$value":"oklch(0.50 0.01 60)"  },  // caption
  "accent":      { "$type":"color", "$value":"oklch(0.55 0.18 25)"  },  // single warm accent (rust/red)
  "accent-fg":   { "$type":"color", "$value":"oklch(0.97 0.005 90)" },
  "highlight":   { "$type":"color", "$value":"oklch(0.94 0.05 95)"  },  // pull-quote bg
  "byline":      { "$type":"color", "$value":"oklch(0.40 0.02 60)"  },
  "footer-bg":   { "$type":"color", "$value":"oklch(0.18 0.00 0)"   },
  "footer-fg":   { "$type":"color", "$value":"oklch(0.85 0.005 90)" },
  "link":        { "$type":"color", "$value":"oklch(0.30 0.10 25)"  }
}
```

## Font stacks (1 primary, 1 fallback)

- Display: `"Tiempos Headline", "GT Sectra", Georgia, serif`
- Body: `"Tiempos Text", "Source Serif 4", Georgia, serif`
- Optional caption sans: `"Söhne", "Inter", system-ui, sans-serif` (use sparingly)

[default — not from source: GT Sectra/Tiempos require commercial license; Source Serif 4 is free OFL fallback.]

## Density rules

- Body line-height 1.55-1.65. Generous. Reading-paced.
- Column max-width 65ch (≈600px).
- Two-column grid on desktop ≥1024px.
- Section breaks: hairline rule + 64-96px vertical air.
- Pull-quotes: 1.5× body size, italic, hanging-indent.

## Layout signature

- 12-col grid, gutter 24px, max width 1180px.
- Drop caps on lead paragraphs (4-line height).
- Captions in `muted` italic, hanging right or below image.
- Image figures: full-bleed OR contained-with-caption — never floating.

## When to use

- Long-form reading: blog, journal, magazine, essay.
- High-prestige product pages where copy carries weight.
- Year-in-review, annual reports.

## When NOT to use

- Dashboards, tables, dense data UI.
- Tech-utility surfaces (use `tech-utility`).
- Mobile-first commerce (cramped two-column on phones).
- Anywhere with >2 accent colors needed.

## Pairing

- Compatible registers: `luxury-editorial`, `craft-artisan`, `academic`.
- Incompatible registers: `cyber-streetwear`, `consumer-playful`.
