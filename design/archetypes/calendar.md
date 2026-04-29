# calendar — month/week/day views

Time-grid layout. Event cells, today indicator, view switcher.

## When to use

- Booking / scheduling apps.
- Meeting / event display.
- Habit / log tracking with date dimension.

## Structural skeleton

```
┌────────────────────────────────────────────┐
│ ‹ April 2026 ›    [Day][Week][Month]       │  toolbar
├──┬───┬───┬───┬───┬───┬───┬─────────────────┤
│  │ M │ T │ W │ T │ F │ S │ S               │  weekday header
├──┼───┼───┼───┼───┼───┼───┼───┤
│ 1│   │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │
├──┼───┼───┼───┼───┼───┼───┼───┤
│ 2│ 7 │ 8 │ 9 │10 │11 │12 │13 │             │  today highlighted
│  │   │evt│   │evt│   │   │   │
└──┴───┴───┴───┴───┴───┴───┴───┘
```

## Required components

- **Toolbar**: month/year nav (‹ ›), view-switcher pills (Day/Week/Month), "Today" button, "+ New event" CTA.
- **Weekday header**: 7 columns, abbreviated names, week-start respects locale.
- **Date cells**: day number top-left, event chips below, today highlight.
- **Event chips**: color-coded by category, time + title, click opens detail.

## Common mistakes

- Week starts inconsistent with locale (Mon vs Sun).
- Today indicator unclear (relies on color alone).
- Event chips overflow without "+N more".
- No keyboard navigation (arrows should move date focus).
- Time zones implied but not shown.

## Density rules

- Month view cell: 96-120px height on desktop, 80px tablet, 56px mobile.
- Week view: 24-hour grid, hour rows 48-60px tall.
- Event chip min height: 24px, padding 4-8px.
- Today border: 2-3px accent, OR full-cell tint at 10-15% accent opacity.

## Accessibility notes

- `<time datetime="2026-04-29">` semantic dates.
- Today: visual highlight + `aria-current="date"`.
- Events: announce title + start time + duration.
- Keyboard: arrows navigate cells, enter opens day, esc closes detail.
- Locale-aware: week start, date format, time zone display.

## Sample DTCG

```json
{
  "calendar": {
    "cell-h":         { "$type":"dimension", "$value":{"value":108,"unit":"px"} },
    "today-bg":       { "$type":"color",     "$value":"{color.accent-soft}" },
    "today-border":   { "$type":"color",     "$value":"{color.accent}" },
    "event-chip-h":   { "$type":"dimension", "$value":{"value":24,"unit":"px"} }
  }
}
```
