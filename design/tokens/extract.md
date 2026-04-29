# Site → DTCG token extraction recipe

Goal: scrape a public site, harvest computed CSS, emit a starter `tokens.json` for `/design extract <url>`.

## Tooling

- Playwright (headless Chromium) — primary scraper. Renders JS, gets computed styles.
- `culori` (npm) — color space conversion (hex → OKLch).
- `style-dictionary` v4 — final emit.

## Pipeline

```
URL → Playwright fetch → DOM walk → computed style harvest → cluster → token emit
```

## Step 1 — load page in Playwright

```js
import { chromium } from 'playwright';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(url, { waitUntil: 'networkidle' });
```

Wait for fonts: `await page.evaluate(() => document.fonts.ready)`.

## Step 2 — harvest computed styles

```js
const samples = await page.$$eval('*', els => els.map(el => {
  const cs = getComputedStyle(el);
  return {
    color: cs.color,
    background: cs.backgroundColor,
    fontFamily: cs.fontFamily,
    fontWeight: cs.fontWeight,
    fontSize: cs.fontSize,
    lineHeight: cs.lineHeight,
    borderRadius: cs.borderRadius,
    padding: cs.padding,
    boxShadow: cs.boxShadow
  };
}));
```

Filter: skip transparent / `rgba(0,0,0,0)` / display:none.

## Step 3 — cluster colors

- Convert all rgba → hex (drop alpha).
- Frequency count. Top N (N=12) become palette candidates.
- K-means cluster in OKLch space (k=6) to find brand/surface/text/accent groups.
- Assign role heuristics:
  - lightest L → `surface.bg`
  - darkest L with contrast≥4.5 vs lightest → `text.primary`
  - highest C (chroma) saturated → `brand.primary`
  - mid-L low-C → `text.secondary`

## Step 4 — typography extraction

- Group by `fontFamily`. Pick top 2 (sans + serif/mono).
- For each family, find size scale: cluster `fontSize` values, snap to 4px grid.
- Weights: take observed set, snap to {400, 500, 600, 700}.

## Step 5 — spacing + radius

- Pad/margin values: cluster, snap to 4px grid → spacing scale.
- `borderRadius` values: cluster, deduplicate → radius scale.

## Step 6 — emit DTCG

Write `tokens.json` per `dtcg-schema.md`. Tag every extracted token with `$extensions.source: { url, selector }` for audit.

```json
{
  "color": {
    "brand": {
      "primary": {
        "$type": "color",
        "$value": "#0071e3",
        "$extensions": {
          "design.extract.source": {
            "url": "https://apple.com",
            "selector": "button.primary",
            "computed": "rgb(0,113,227)",
            "frequency": 47
          }
        }
      }
    }
  }
}
```

## Step 7 — emit DESIGN.md skeleton

Frontmatter only (machine fields). Section bodies prefixed with `[GAP — extract from screenshots]` for human pass.

## Constraints

- Robots.txt MUST be respected. If disallowed, abort with error.
- User-Agent: identify as `claude-design-extract/1.0`.
- Single page per call — recursion is opt-in.
- Cache page HTML for 24h to avoid re-hitting.

## Known limitations

- Dynamic theme switchers (dark/light toggles) require 2 passes.
- CSS-in-JS hashes obscure semantic class names — role assignment falls back to position heuristics.
- Custom fonts not loaded by `document.fonts.ready` will register as fallback. Verify against `<link rel="stylesheet">` for `@font-face` declarations.

## Validation gate

After extract, run `checks/lint.md` immediately. Extracted token count >12 base colors → reject and ask user to merge similar shades. Extracted fonts >2 → reject.

## Reference implementation pointer

Pattern based on `nexu-io/open-design` extraction recipes. No bundled code in this skill — agent writes the script per project per call. Location convention: `<project>/scripts/extract-tokens.mjs`.
