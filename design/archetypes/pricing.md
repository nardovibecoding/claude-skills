# pricing — 3-tier card row + comparison + FAQ

Standard SaaS pricing layout: tiers, comparison table, FAQ.

## When to use

- SaaS pricing page.
- API plan selection.
- Subscription product upgrades.

## Structural skeleton

```
┌──────────────────────────────────────┐
│ Section heading + subhead            │
│                                      │
│ ┌──────┐ ┌──────┐ ┌──────┐           │
│ │ Free │ │ Pro  │ │ Team │  3 tiers  │
│ │ $0   │ │ $20  │ │ $99  │           │
│ │      │ │ ★    │ │      │  highlight│
│ │ feat │ │ feat │ │ feat │  middle   │
│ │ feat │ │ feat │ │ feat │           │
│ │ [CTA]│ │ [CTA]│ │ [CTA]│           │
│ └──────┘ └──────┘ └──────┘           │
│                                      │
│ Comparison table (full feature grid) │
│                                      │
│ FAQ (5-8 Q's)                        │
└──────────────────────────────────────┘
```

## Required components

- **Tier cards** (3, sometimes 4): name + price + 3-7 features + CTA per card.
- **Highlight tier**: middle card visually marked as "recommended". Subtle border / scale-up / accent badge.
- **Toggle** (optional): Monthly / Annual switch with savings indicator ("Save 20%").
- **Comparison table**: full feature grid, ✓/✗ marks, mobile-collapsing.
- **FAQ**: 5-8 questions, accordion style.
- **Enterprise contact** (optional): "Need more? Contact sales →".

## Common mistakes

- 4+ tiers — analysis paralysis.
- Hiding price ("Contact us" for everything) — distrust.
- Misleading "Save X%" math.
- Comparison table too dense to scan.
- Annual price shown without monthly equivalent.

## Density rules

- Tier card width: 280-360px.
- Card padding: 24-32px.
- Price font: 48-64px, weight 600-700.
- Feature list: 16px body, ✓ icon left, line-height 1.6.

## Accessibility notes

- Highlight tier: not by color alone — also use border, badge, or label.
- Currency clearly stated ("USD" or "$" with locale).
- Comparison table: `<th scope>` for both row + col headers.
- FAQ: `<details>`/`<summary>` or aria-expanded button.
- CTA buttons: distinct accessible names ("Subscribe to Pro", not "Get Started" ×3).

## Sample DTCG

```json
{
  "pricing": {
    "tier-card-w":   { "$type":"dimension", "$value":{"value":320,"unit":"px"} },
    "price-size":    { "$type":"dimension", "$value":{"value":56,"unit":"px"} },
    "highlight-bg":  { "$type":"color",     "$value":"{color.accent-soft}" }
  }
}
```
