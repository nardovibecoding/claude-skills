# hero — landing top-of-page

Primary attention magnet. Headline + subhead + CTA + optional visual.

## When to use

- Top of any landing/marketing page.
- Product launch microsite.
- Logged-out home page.

## Structural skeleton

```
┌──────────────────────────────────────────────┐
│            (logo / nav)                      │
│                                              │
│   HEADLINE  (1-2 lines, oversized)           │
│   subhead description (1-2 sentences)        │
│                                              │
│   [ Primary CTA ]   secondary link           │
│                                              │
│              ┌────────────────┐              │
│              │ visual / video │              │
│              └────────────────┘              │
└──────────────────────────────────────────────┘
```

## Required components

- **Headline**: 48-96px, weight 500-700, line-height 1.0-1.2.
- **Subhead**: 18-24px, weight 400, line-height 1.4-1.5, max 65ch.
- **Primary CTA**: button, accent fill, ≥44px touch target.
- **Secondary action** (optional): link or ghost button next to primary.
- **Hero visual** (optional): product screenshot, looping video, illustration. Aspect 16:9 or 4:3.

## Common mistakes

- Headline >12 words — drift to long-form.
- Two competing primary CTAs — pick one.
- Stock photo of "team smiling" — instant slop.
- Animated gradient background distracting from headline.
- Headline that says nothing concrete ("Reimagine X").

## Density rules

- Hero vertical: 80-100vh on desktop, 60vh mobile.
- Headline-subhead-CTA spacing: 24/16/32 (rhythm: heading→sub close, sub→cta loose).
- Centered or left-aligned. NEVER right-aligned.

## Accessibility notes

- Headline as `<h1>`. One per page.
- CTA button has accessible name (no icon-only buttons here).
- Hero video: muted, autoplay, loop, with `aria-hidden="true"` if decorative.
- Color contrast on text-over-image: text-shadow or scrim overlay required.
- Reduce motion: `@media (prefers-reduced-motion)` disables hero video.

## Sample DTCG

```json
{
  "hero": {
    "headline-size": { "$type":"dimension", "$value":{"value":72,"unit":"px"} },
    "subhead-size":  { "$type":"dimension", "$value":{"value":20,"unit":"px"} },
    "cta-padding":   { "$type":"dimension", "$value":{"value":16,"unit":"px"} },
    "vertical":      { "$type":"dimension", "$value":{"value":80,"unit":"vh"} }
  }
}
```

## Voice match

- `startup-techy`: "The AI runtime for production." + "Open the docs →"
- `luxury-editorial`: "A study in restraint." + "Discover Volume IV"
- `civic-formal`: "Apply for a passport." + "Start now"
