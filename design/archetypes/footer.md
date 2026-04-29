# footer — link columns + legal + newsletter

Site footer. Links by category, legal row, optional newsletter signup.

## When to use

- Bottom of any marketing/landing/blog page.
- Documentation site footers.

## Structural skeleton

```
┌──────────────────────────────────────────┐
│  Logo + tagline       Newsletter signup  │
│  ─────────────        [email] [→]        │
│                                          │
│  Product   Company   Resources   Legal   │  link columns
│  · Item    · About   · Docs      · Tos   │
│  · Item    · Blog    · API       · Priv  │
│  · Item    · Jobs    · Status    · Sec   │
│                                          │
│ ──────────────────────────────────────── │
│ © 2026 Brand     [social] [social] [lang]│  legal row
└──────────────────────────────────────────┘
```

## Required components

- **Brand block**: logo, 1-line tagline.
- **Link columns**: 3-5 columns, 4-6 links each. Categorized: Product / Company / Resources / Legal.
- **Legal row**: copyright, social icons, language switcher.
- **Newsletter** (optional): email input + submit, GDPR consent line.

## Common mistakes

- 12 links per column — visual noise.
- Social icons before content (footer is for departure, not engagement).
- Copyright year hardcoded (use server year or `Date().getFullYear()`).
- Cookie banner conflated with footer.
- "Made with ❤ in SF" — drift unless register allows.

## Density rules

- Vertical padding: 64-96px top, 24-32px bottom.
- Column gap: 32-64px on desktop, 24px tablet.
- Link text: 14-16px, line-height 1.6 for tap targets.
- Legal row: 12-13px, low-contrast.

## Accessibility notes

- `<footer>` semantic landmark.
- Newsletter form: labeled input + describedby for consent.
- Social icons: `aria-label="Twitter"`, not just icon.
- Language switcher: `<select>` with current lang as label, `lang` attr per option.
- Sufficient contrast on legal row.

## Voice match

- `enterprise-trust` footer: contains compliance badges + status link.
- `civic-formal` footer: gov crest + accessibility statement link + last-updated date.
- `craft-artisan` footer: workshop address + opening hours + "by appointment".
