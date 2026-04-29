# chart — single chart focused screen

One chart dominates. Line/bar/area/scatter. Legend, tooltip, axis.

## When to use

- Drill-in detail view from a dashboard KPI.
- Standalone analytics view.
- Embedded chart in editorial/report.

## Structural skeleton

```
┌──────────────────────────────────────┐
│ Chart Title                          │
│ Subtitle / context                   │
│                                      │
│ [time range][filters]    [download]  │
│                                      │
│                                      │
│         ╱╲      ╱╲                   │
│       ╱    ╲  ╱    ╲___              │  chart canvas
│  ___╱       ╲╱                       │
│                                      │
│ │  │  │  │  │  │  │  │              │  x-axis
│  ───── series A   ───── series B     │  legend
│                                      │
│ caption / source                     │
└──────────────────────────────────────┘
```

## Required components

- **Title + subtitle**: 24-32px title, 14-16px subtitle.
- **Controls strip**: time range pills, filter chips, action menu.
- **Canvas**: chart fills 60-70% of viewport.
- **Axes**: labeled, tick marks readable, units stated.
- **Legend**: below chart preferred. Color swatch + label.
- **Tooltip**: on hover, shows exact values + delta.
- **Caption**: data source + last-updated timestamp.

## Common mistakes

- 3D charts (always wrong).
- Pie chart with >5 slices.
- Y-axis not starting at zero (when zero is meaningful).
- Tiny tick labels.
- Color encoding inaccessible.
- No source citation.

## Density rules

- Chart canvas min height: 320px on desktop, 240px mobile.
- Padding around canvas: 24-40px.
- Gridlines: hairline, low-contrast (10-15% of text color).

## Accessibility notes

- Chart container `role="img"` with `aria-label` summarizing key insight.
- Provide `<table>` data fallback toggleable below chart.
- Color-blind safe palette (Tableau 10 or Wong palette).
- Series differentiated by shape/dash pattern, not color alone.
- Tooltip keyboard-accessible (focus on data points).

## Tooling pointer

Chart libraries: D3 (custom), Recharts (React), Visx (React+D3), ECharts (vanilla), Chart.js. Pick by stack. Token-driven colors via CSS vars or chart theme prop.
