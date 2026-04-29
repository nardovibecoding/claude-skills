# brutalist — pure black/white + 1 raw color

No rounded corners. system-ui or default browser fonts. Exposed grid. Vibe: Are.na, Bloomberg Terminal raw, Craigslist refined, Yale School of Art, balenciaga.com.

## OKLch palette (12 swatches)

```json
{
  "bg":          { "$type":"color", "$value":"oklch(1.00 0.00 0)"   },  // pure white
  "ink":         { "$type":"color", "$value":"oklch(0.10 0.00 0)"   },  // pure-ish black
  "paper":       { "$type":"color", "$value":"oklch(0.96 0.00 0)"   },  // off-white panel
  "border":      { "$type":"color", "$value":"oklch(0.10 0.00 0)"   },  // 2px black borders
  "text":        { "$type":"color", "$value":"oklch(0.10 0.00 0)"   },
  "text-muted":  { "$type":"color", "$value":"oklch(0.40 0.00 0)"   },
  "accent":      { "$type":"color", "$value":"oklch(0.65 0.28 30)"  },  // raw red/orange
  "accent-2":    { "$type":"color", "$value":"oklch(0.85 0.20 100)" },  // raw yellow (use rarely)
  "rule":        { "$type":"color", "$value":"oklch(0.10 0.00 0)"   },
  "highlight":   { "$type":"color", "$value":"oklch(0.65 0.28 30)"  },  // accent reused
  "inverse-bg":  { "$type":"color", "$value":"oklch(0.10 0.00 0)"   },
  "inverse-fg":  { "$type":"color", "$value":"oklch(1.00 0.00 0)"   }
}
```

## Font stacks

- Primary: `system-ui, -apple-system, sans-serif` (intentional default)
- Optional display: `"Times New Roman", serif` (forced default-feel)
- Mono accent: `"Courier New", monospace`

[default — not from source: brutalist intentionally avoids licensed type. Default OS fonts ARE the aesthetic.]

## Density rules

- Border-radius: `0`. Always. Pills forbidden.
- Borders: 1-2px solid black. EVERYWHERE there's a panel edge.
- Spacing: irregular. Mix 8/12/24/48 — purposeful asymmetry.
- Body line-height 1.4. Headings 1.0-1.1 (compressed).
- ALL CAPS labels OK. Underline-on-hover for links. No subtle decorations.

## Layout signature

- Visible grid lines (1px black between cells).
- Asymmetric layouts encouraged — 3/9 split, 7/5 split, NOT 6/6.
- Headers: `text-decoration: underline` allowed.
- Buttons: rectangular, 2px black border, no hover lift, just color invert.
- Images: hard edges, no rounding, no shadows.
- Type can be oversized + oversized — 200px headlines OK.

## When to use

- Portfolio sites (designer/dev personal).
- Indie publications, art schools, gallery sites.
- Statement marketing pages (limited deploy).
- Anywhere "anti-design" is the design.

## When NOT to use

- Consumer products (will read as broken).
- Enterprise / SaaS (incompatible with trust signaling).
- Dashboards / data-heavy UI.
- Mobile-primary surfaces (asymmetry breaks at 360px).
- Anywhere needing >2 colors.

## Pairing

- Compatible registers: `underground-zine`, `cyber-streetwear`, `academic` (when paired with serif).
- Incompatible registers: `enterprise-trust`, `consumer-playful`, `civic-formal`, `craft-artisan`.
