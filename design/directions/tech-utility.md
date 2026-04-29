# tech-utility — dark default, dense data, mono accents

Trader/IDE/terminal feel. 8pt grid, tight density. Inter + JetBrains Mono. Vibe: Bloomberg Terminal, Linear, Cursor, Raycast, GitHub Dark, Sentry.

## OKLch palette (12 swatches)

```json
{
  "bg":          { "$type":"color", "$value":"oklch(0.15 0.005 250)" },  // page (deep slate)
  "surface":     { "$type":"color", "$value":"oklch(0.18 0.008 250)" },  // panel
  "surface-2":   { "$type":"color", "$value":"oklch(0.22 0.010 250)" },  // raised panel
  "border":      { "$type":"color", "$value":"oklch(0.28 0.010 250)" },  // hairline
  "text":        { "$type":"color", "$value":"oklch(0.94 0.005 250)" },  // primary fg
  "text-muted":  { "$type":"color", "$value":"oklch(0.65 0.010 250)" },
  "text-faint":  { "$type":"color", "$value":"oklch(0.45 0.010 250)" },
  "accent":      { "$type":"color", "$value":"oklch(0.72 0.18 220)"  },  // electric cyan
  "accent-fg":   { "$type":"color", "$value":"oklch(0.10 0.005 250)" },
  "success":     { "$type":"color", "$value":"oklch(0.72 0.18 145)"  },  // green
  "warn":        { "$type":"color", "$value":"oklch(0.78 0.16 85)"   },  // amber
  "danger":      { "$type":"color", "$value":"oklch(0.65 0.22 25)"   }   // red
}
```

## Font stacks

- Sans: `"Inter", system-ui, sans-serif` (UI labels, body)
- Mono: `"JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace` (numbers, code, KPIs)

## Density rules

- 8pt grid. Spacing scale: 4/8/12/16/24/32. NEVER >32 in panel contexts.
- Body line-height 1.4. Tabular nums on (`font-variant-numeric: tabular-nums`).
- Row height tables: 28-32px. Compact mode 24px.
- Card padding: 12-16px. NOT 24+.
- Section padding: 24-32px (NOT 64+ — would break dashboard density).

## Layout signature

- Full-bleed grid, sidebar nav 240px, main content fills remainder.
- Panels: 1px border + flat background. NO shadows in core panels.
- Border-radius: 4-6px (sharp, utilitarian). NEVER pill except for pills.
- Numbers right-aligned, monospace, tabular nums.
- Status dots: 6-8px, accent-tinted.

## When to use

- Trader UIs (PM bot dashboards, Bloomberg-style).
- IDE / dev tools / observability dashboards.
- Admin / data-heavy internal tools.
- Anywhere dark default + dense data is the goal.
- VibeIsland (SwiftUI macOS) — default direction.

## When NOT to use

- Marketing / landing pages (use `modern-minimal`).
- Editorial content (use `editorial-monocle`).
- Consumer / playful surfaces (use `soft-warm` or `consumer-playful` register).
- Print-style or low-density UI.

## Pairing

- Compatible registers: `startup-techy`, `enterprise-trust`, `craft-artisan` (for high-end IDE feel).
- Incompatible registers: `consumer-playful`, `civic-formal`, `luxury-editorial`.
