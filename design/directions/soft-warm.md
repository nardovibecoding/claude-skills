# soft-warm — cream/sand/sage palette, organic spacing

Warm grays. Rounded shapes. Söhne or DM Serif. Vibe: Anthropic's Claude site, Aesop, Mailchimp pre-Intuit, mid-Notion, slow living publications.

## OKLch palette (12 swatches)

```json
{
  "paper":       { "$type":"color", "$value":"oklch(0.96 0.015 90)"  },  // parchment cream
  "ivory":       { "$type":"color", "$value":"oklch(0.98 0.010 90)"  },  // lifted card
  "sand":        { "$type":"color", "$value":"oklch(0.91 0.020 85)"  },  // button bg
  "border":      { "$type":"color", "$value":"oklch(0.90 0.015 85)"  },  // soft cream border
  "ink":         { "$type":"color", "$value":"oklch(0.20 0.005 60)"  },  // warm near-black
  "olive":       { "$type":"color", "$value":"oklch(0.45 0.010 80)"  },  // body secondary
  "stone":       { "$type":"color", "$value":"oklch(0.60 0.010 80)"  },  // tertiary
  "accent":      { "$type":"color", "$value":"oklch(0.62 0.13 40)"   },  // terracotta
  "accent-fg":   { "$type":"color", "$value":"oklch(0.98 0.010 90)"  },
  "sage":        { "$type":"color", "$value":"oklch(0.72 0.04 145)"  },  // muted green secondary
  "rust-soft":   { "$type":"color", "$value":"oklch(0.72 0.10 50)"   },  // illustration warm
  "shadow-warm": { "$type":"color", "$value":"oklch(0.20 0.005 60 / 0.05)" }
}
```

## Font stacks

- Display: `"DM Serif Display", "Tiempos", Georgia, serif`
- Body: `"Söhne", "Inter", system-ui, sans-serif`

[default — not from source: Söhne is licensed; Inter is the OFL fallback. DM Serif Display is OFL.]

## Density rules

- Body line-height 1.6 (literary). Heading 1.2.
- Border-radius: 12-16px standard, 24-32px featured. NEVER sharp <8px.
- Spacing: organic. 4/8/12/20/32/48/80. Avoid rigid 4×N for hero sections.
- Section padding: 80-120px. Generous.

## Layout signature

- Cards on Ivory atop Paper bg — barely-visible elevation.
- Ring shadows (`0 0 0 1px <warm-tint>`) instead of drop shadows.
- Two-column where used: 40/60 asymmetry, NOT 50/50.
- Illustrations: hand-drawn-feeling, organic shapes, terracotta/sage palette.
- Section alternation: light/dark warm — chapter rhythm.

## When to use

- Wellness, hospitality, slow-living brands.
- AI products that want to feel human (Claude pattern).
- Editorial content with soft personality.
- Consumer apps where warmth differentiates from sterile competitors.

## When NOT to use

- Trader / dashboard / data UI (use `tech-utility`).
- Enterprise B2B (use `modern-minimal` with `enterprise-trust` register).
- Anything that needs cool blues / pure whites / hard edges.
- Cyber / underground / brutalist projects.

## Pairing

- Compatible registers: `craft-artisan`, `consumer-playful` (toned down), `luxury-editorial`.
- Incompatible registers: `cyber-streetwear`, `civic-formal`, `underground-zine`.
