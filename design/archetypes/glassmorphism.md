# glassmorphism — translucent panels, blur, gradient bg

Apple-style. Translucent surfaces over rich backgrounds. iOS 26 Liquid Glass.

## When to use

- iOS / macOS apps targeting iOS 26+ Liquid Glass.
- Marketing surfaces with rich background imagery.
- VibeIsland (limited — performance cost on macOS).
- Hero overlays where the bg image is the star.

## Structural skeleton

```
┌──────────────────────────────────────────┐
│ ░░░░░░░░░░ rich gradient/photo bg ░░░░░░ │
│ ░░░░ ┌──────────────────────┐ ░░░░░░░░░░ │
│ ░░░░ │  ▓▓ glass panel ▓▓   │ ░░░░░░░░░░ │  blur 20-40px
│ ░░░░ │  ▓ headline + body ▓ │ ░░░░░░░░░░ │  bg rgba 60-80% opacity
│ ░░░░ │  ▓ [CTA]            ▓│ ░░░░░░░░░░ │  border 1px white 20%
│ ░░░░ └──────────────────────┘ ░░░░░░░░░░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────┘
```

## Required components

- **Rich background**: gradient mesh, photo, or animated bg.
- **Glass panel**: backdrop-filter blur + semi-transparent fill.
- **Subtle border**: 1px inset with low-alpha white.
- **Inner shadow** (optional): subtle highlight on top edge.

## Common mistakes

- Glass on flat background — pointless (the blur does nothing).
- Multiple stacked glass panels — visual chaos.
- Glass with insufficient contrast — text becomes unreadable.
- Glass everywhere — defeats the purpose (single signature use).
- Forgetting `@supports (backdrop-filter)` fallback.

## Density rules

- Panel padding: 24-40px (generous).
- Border-radius: 16-32px.
- Backdrop blur: 20-40px (less on slow devices).
- Background opacity: 0.6-0.8 (more transparent = more "glass").

## Accessibility notes

- Contrast ratio against blurred bg MUST still pass WCAG AA. Test against worst-case bg.
- `backdrop-filter` not universally supported — provide solid fallback via `@supports`.
- Reduce motion: disable any moving bg animation.
- High contrast mode: switch to solid panel.

## CSS sample

```css
.glass {
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(24px) saturate(140%);
  -webkit-backdrop-filter: blur(24px) saturate(140%);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 24px;
}
@supports not (backdrop-filter: blur(1px)) {
  .glass { background: rgba(255,255,255,0.92); }
}
```

## SwiftUI hint

iOS 26: `.glassEffect(.regular)` on view modifier. Don't hand-roll `.background(.ultraThinMaterial)` if the system effect is available.
