# popup — modal/drawer/popover

Small surface, max-width 480px. Modal overlay, side drawer, or popover from an anchor.

## When to use

- Confirmation dialogs, edit forms, login flows.
- Browser extension popup (MV3, separate dimensions).
- Tooltip-larger-than-tooltip surfaces.
- Quick-action panels (Raycast-style).

## Structural skeleton

### Modal
```
        ┌──────────────────────────┐
░░░░░░░░│ Title                  ✕ │░░░░░░░░  scrim 60% behind
░░░░░░░░├──────────────────────────┤░░░░░░░░
░░░░░░░░│ Body content             │░░░░░░░░
░░░░░░░░│                          │░░░░░░░░  max-w 480px
░░░░░░░░├──────────────────────────┤░░░░░░░░
░░░░░░░░│        [Cancel] [Confirm]│░░░░░░░░
░░░░░░░░└──────────────────────────┘░░░░░░░░
```

### Drawer (side)
```
                       ┌──────────┐
                       │ ✕  Title │
                       │          │
                       │ Body     │
                       │ Body     │
                       │          │  width 320-420px
                       │          │
                       │ [Save]   │
                       └──────────┘
```

### Popover (anchored)
```
[anchor btn ▾]
   │
   ▼
┌─────────────┐
│ option 1    │
│ option 2    │
│ option 3    │
└─────────────┘
```

## Required components

- **Surface**: max-width 480px (modal), 320-420px (drawer), 240-320px (popover).
- **Close affordance**: ✕ icon top-right (modal/drawer), click-outside (popover).
- **Title** (modal/drawer): clear context.
- **Body**: form, content, options.
- **Footer actions** (modal): primary + cancel, right-aligned.

## Common mistakes

- Modal without escape-to-close.
- No initial focus set inside modal — keyboard users lost.
- Stacked modals (modal-on-modal) — bad UX.
- Drawer that doesn't push or overlay clearly — ambiguous.
- Popover anchor moves while open — popover detaches.

## Density rules

- Modal padding: 24-32px.
- Drawer padding: 24px.
- Popover padding: 8-12px.
- Border-radius: 12-16px.
- Backdrop scrim: rgba(0,0,0,0.4-0.6).

## Accessibility notes

- `role="dialog"` (modal), `aria-modal="true"`.
- Focus trapped inside modal; restored to trigger on close.
- Escape key closes (unless destructive action pending).
- Title connected via `aria-labelledby`.
- Popover: `aria-expanded` on trigger, `role="menu"` if it's a menu.
- Reduce-motion: skip slide/fade animations.

## Sample DTCG

```json
{
  "popup": {
    "modal-max-w":   { "$type":"dimension", "$value":{"value":480,"unit":"px"} },
    "drawer-w":      { "$type":"dimension", "$value":{"value":380,"unit":"px"} },
    "scrim":         { "$type":"color",     "$value":"rgba(0,0,0,0.5)" }
  }
}
```
