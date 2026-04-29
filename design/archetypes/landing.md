# landing — full marketing page

Hero + features + social proof + CTA + footer. Composite archetype.

## When to use

- Product launch page.
- Marketing home, logged-out home.
- Microsite per feature.

## Structural skeleton

```
┌──────────────┐
│ NAV          │  64-72px sticky
├──────────────┤
│ HERO         │  see archetypes/hero.md
├──────────────┤
│ TRUSTED BY   │  customer logo strip (mono)
├──────────────┤
│ FEATURES     │  3-col or alternating left-right blocks
├──────────────┤
│ SOCIAL PROOF │  testimonials / case-study cards
├──────────────┤
│ CTA BAND     │  big call-to-action block
├──────────────┤
│ FOOTER       │  see archetypes/footer.md
└──────────────┘
```

## Required components

- **Nav**: logo, primary nav links (3-5), secondary CTA.
- **Hero**: per `archetypes/hero.md`.
- **Trusted by** (optional): logos at 50% opacity, monochrome.
- **Features**: 3-6 features. Either 3-col grid or alternating image+text rows.
- **Social proof**: testimonial cards OR case-study previews OR review aggregate.
- **CTA band**: full-bleed accent section, single headline + button.
- **Footer**: per `archetypes/footer.md`.

## Common mistakes

- Too many sections (>8). Cuts attention.
- Multiple competing CTAs scattered.
- "Features" written as feature names, not benefits.
- Auto-playing background video that loops loud.
- Customer logos that are obviously placeholder ("Acme Corp").

## Density rules

- Section vertical padding: 96-160px (generous, breathes).
- Max content width: 1200px centered.
- Feature card: 320-360px wide, image+title+1-line description.
- CTA band: full-bleed, 80-120px vertical.

## Accessibility notes

- Single `<h1>` (the hero).
- `<h2>` per section.
- Skip-to-content link (focus reveals).
- Sticky nav announces correctly to screen readers.
- All images have alt text or `alt=""` if decorative.
- Lazy-load below-fold images.

## Voice match

- `startup-techy`: hero → "log in / sign up" + minimal nav + dark default.
- `enterprise-trust`: trusted-by logos prominent + compliance section above footer.
- `consumer-playful`: 3-col features with rounded cards + testimonial carousel + bottom CTA "Try it free".
