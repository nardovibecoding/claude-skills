# dashboard — multi-panel data shape

Multi-panel data layout. Tables, charts, filters, sidebar nav. Optimized for sustained focus.

## When to use

- Trader UI / PM bot dashboards.
- Admin consoles, observability, analytics, internal tools.
- IDE-like workspaces (Linear-style).
- Any surface where users return daily for data.

## Structural skeleton

```
┌──────────────────────────────────────────────────┐
│ TOP BAR  workspace ▾   search        ⌘K  user    │ 48-56px
├──────┬───────────────────────────────────────────┤
│ NAV  │ TITLE + CONTROLS                          │ 240px sidebar
│      ├─────────────┬─────────────┬───────────────┤
│ ▢    │ KPI 1       │ KPI 2       │ KPI 3         │ KPI row
│ ▢    ├─────────────┴─────────────┴───────────────┤
│ ▢    │ MAIN CHART (60% height)                   │
│ ▢    ├─────────────────────────┬─────────────────┤
│      │ TABLE / list (60% w)    │ side panel      │
│      │                         │ (filters/detail)│
│      └─────────────────────────┴─────────────────┘
```

## Required components

- **Top bar**: workspace switcher, global search (`⌘K`), user menu.
- **Sidebar nav**: collapsible, max 240px, icon+label, active-state highlight.
- **KPI row**: 3-5 cards, each with metric + delta + sparkline.
- **Main chart**: dominant visual, tooltip on hover, time-range selector.
- **Data table**: sortable columns, sticky header, row hover, action menu per row.
- **Side panel** (optional): filter drawer, row detail, recent activity.

## Common mistakes

- Using >5 KPIs in the row — visual noise.
- Card padding too generous (24+) — breaks dashboard density.
- Hero-style imagery in dashboard — doesn't belong.
- Animation on every state change — fatiguing.
- Sidebar nav >280px — eats main content.

## Density rules (paired direction matters)

- With `tech-utility`: row height 28-32px, card padding 12-16px, no shadows.
- With `modern-minimal`: row height 36-44px, card padding 16-24px, whisper shadow.
- KPI font size: 24-32px for value, 12-14px for label.

## Accessibility notes

- Tables: `<table>` semantics, `<th scope>`, sortable announce via aria-sort.
- Charts: text alternative + data table fallback.
- Color encoding: NEVER alone — pair with shape, label, or icon.
- Keyboard: `tab` cycles cards, `enter` opens detail, `escape` closes panel.
- Focus visible on all interactives.

## Sample DTCG additions for this archetype

```json
{
  "dashboard": {
    "row-height":     { "$type":"dimension", "$value":{"value":32,"unit":"px"} },
    "kpi-padding":    { "$type":"dimension", "$value":{"value":16,"unit":"px"} },
    "sidebar-width":  { "$type":"dimension", "$value":{"value":240,"unit":"px"} },
    "topbar-height":  { "$type":"dimension", "$value":{"value":52,"unit":"px"} }
  }
}
```
