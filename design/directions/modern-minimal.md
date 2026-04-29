# modern-minimal — neutral grays + 1 desaturated accent

Inter/Geist sans, generous whitespace, near-zero decoration. Vibe: Vercel, Linear, Notion, Stripe.

## OKLch palette (12 swatches)

```json
{
  "bg":          { "$type":"color", "$value":"oklch(0.99 0.00 0)"   },  // page
  "surface":     { "$type":"color", "$value":"oklch(0.97 0.005 250)" }, // card
  "surface-2":   { "$type":"color", "$value":"oklch(0.94 0.008 250)" },
  "border":      { "$type":"color", "$value":"oklch(0.90 0.005 250)" },
  "text":        { "$type":"color", "$value":"oklch(0.20 0.01 250)"  },  // primary text
  "text-muted":  { "$type":"color", "$value":"oklch(0.50 0.01 250)"  },
  "text-faint":  { "$type":"color", "$value":"oklch(0.65 0.005 250)" },
  "accent":      { "$type":"color", "$value":"oklch(0.55 0.10 250)"  },  // desaturated blue
  "accent-fg":   { "$type":"color", "$value":"oklch(0.99 0.00 0)"    },
  "accent-soft": { "$type":"color", "$value":"oklch(0.92 0.04 250)"  },
  "success":     { "$type":"color", "$value":"oklch(0.60 0.13 145)"  },
  "danger":      { "$type":"color", "$value":"oklch(0.55 0.18 25)"   }
}
```

## Font stacks

- Sans: `"Inter", "Geist", system-ui, sans-serif`
- Mono (optional): `"Geist Mono", "JetBrains Mono", ui-monospace, monospace`

[default — not from source: Inter is the working default; Geist is preferred when project ships its own fonts.]

## Density rules

- 8pt grid. Spacing scale: 4/8/12/16/24/32/48/64/96.
- Body line-height 1.5. Heading line-height 1.2.
- Card padding: 24-32px. Section padding: 64-96px vertical.
- One accent. Used max twice per surface (anti-slop rule).

## Layout signature

- Centered max-width 1200px container.
- 12-col responsive grid, 24px gutter.
- Border-radius: 8px standard, 12px featured, 6px small.
- Shadow: `0 1px 2px rgba(0,0,0,0.04)` (whisper) for cards. No deep drops.

## When to use

- Default fallback when no other direction fits.
- Marketing pages, product pages, blogs.
- Internal tools, admin dashboards (paired with `tech-utility` for density).
- SaaS landing.

## When NOT to use

- Anywhere needing emotional warmth (use `soft-warm`).
- Editorial long-form (use `editorial-monocle`).
- Trader dashboards or terminal-feel UI (use `tech-utility`).
- High-contrast/raw aesthetic (use `brutalist`).

## Pairing

- Compatible registers: `startup-techy`, `enterprise-trust`, `civic-formal`.
- Incompatible registers: `underground-zine`, `cyber-streetwear`.
