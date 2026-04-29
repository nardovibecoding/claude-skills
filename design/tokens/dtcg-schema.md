# DTCG schema — W3C Design Tokens primer

Authoritative spec: https://www.designtokens.org/ (W3C Community Group, Oct 2025 stable). Style Dictionary v4 is the canonical transformer (https://styledictionary.com/).

## Core rules

- Token = JSON object with `$value` (the data) and `$type` (the kind). `$description` optional.
- Group = JSON object holding tokens or sub-groups. NO `$value` at group nodes.
- Reference syntax: `"{group.token}"` resolves at build time. Refs may chain. Cycles forbidden.
- Token names: kebab-case or camelCase. Stable. NO spaces, NO leading digits.
- Hex colors MUST be sRGB. Use OKLch in `$extensions` for wide-gamut targets.

## `$type` annotations (required, lint enforces)

| `$type` | `$value` shape | Example |
|---|---|---|
| `color` | hex string `#rrggbb[aa]` or `{ "colorSpace": "oklch", "components": [L,C,h] }` | `"#0071e3"` |
| `dimension` | `{ "value": 16, "unit": "px" }` (or `rem`/`em`) | spacing, radius |
| `fontFamily` | string OR array of strings (fallback chain) | `["Inter","system-ui","sans-serif"]` |
| `fontWeight` | number 1-1000 OR alias `"regular"`/`"medium"`/`"bold"` | `500` |
| `lineHeight` | number (unitless multiplier) OR dimension | `1.5` |
| `letterSpacing` | dimension (px or em) | `{value:0.12,unit:"px"}` |
| `duration` | `{ "value": 200, "unit": "ms" }` | motion |
| `cubicBezier` | array `[x1,y1,x2,y2]` | easing |
| `shadow` | object `{ color, offsetX, offsetY, blur, spread }` | elevation |
| `border` | object `{ color, width, style }` | strokes |
| `gradient` | array of stops `[{color,position}, ...]` | rare |
| `transition` | composite `{ duration, delay, timingFunction }` | motion presets |
| `typography` | composite `{ fontFamily, fontWeight, fontSize, lineHeight, letterSpacing }` | text styles |

Composite tokens (`shadow`, `border`, `transition`, `typography`) are emitted as flattened native types per renderer.

## Required top-level groups (this skill's contract)

Every project's `tokens.json` MUST contain these groups:

- `color` — surfaces, text, accents, semantic (success/warning/error/info)
- `typography` — at least one composite for body + heading
- `spacing` — scale (4/8/12/16/24/32/48/64 minimum)
- `radius` — scale (sm/md/lg + pill if used)
- `elevation` — shadow tokens (none/sm/md/lg)
- `motion` — duration + easing presets

Optional: `border`, `gradient`, `breakpoint`, `zIndex`.

## Sample 30-line tokens.json

```json
{
  "$schema": "https://designtokens.org/schema.json",
  "color": {
    "brand": {
      "primary":   { "$type": "color", "$value": "#0071e3" },
      "primary-fg":{ "$type": "color", "$value": "#ffffff" }
    },
    "surface": {
      "bg":        { "$type": "color", "$value": "#f5f5f7" },
      "card":      { "$type": "color", "$value": "#ffffff" }
    },
    "text": {
      "primary":   { "$type": "color", "$value": "#1d1d1f" },
      "secondary": { "$type": "color", "$value": "#6e6e73" }
    }
  },
  "spacing": {
    "xs": { "$type":"dimension", "$value":{"value":4,"unit":"px"} },
    "sm": { "$type":"dimension", "$value":{"value":8,"unit":"px"} },
    "md": { "$type":"dimension", "$value":{"value":16,"unit":"px"} },
    "lg": { "$type":"dimension", "$value":{"value":24,"unit":"px"} }
  },
  "radius": {
    "md": { "$type":"dimension", "$value":{"value":8,"unit":"px"} }
  },
  "typography": {
    "body": {
      "$type":"typography",
      "$value": {
        "fontFamily":"{font.sans}",
        "fontWeight":400,
        "fontSize":{"value":16,"unit":"px"},
        "lineHeight":1.5
      }
    }
  },
  "button": {
    "bg":   { "$type":"color", "$value":"{color.brand.primary}" },
    "text": { "$type":"color", "$value":"{color.brand.primary-fg}" }
  }
}
```

## Build pipeline

```
tokens.json --[Style Dictionary v4]--> {
  swiftui: Color extensions + Font + Spacing constants
  html:    CSS custom properties + Tailwind v4 @theme
  ext:     scoped CSS for popup / shadow-DOM
}
```

Style Dictionary config picks platform via `transforms` + `formats`. Custom transforms for OKLch fallback: emit hex for SDR, `color(display-p3 ...)` for wide-gamut renderers.

## Reference resolution rules

1. Refs MUST point at existing tokens. Lint rule `broken-ref` flags missing.
2. Refs MUST NOT cycle. Lint rule `cyclic-ref` flags.
3. Composite refs: a `typography` token may ref `{font.sans}` for `fontFamily` only.
4. Cross-group refs allowed: `button.bg` → `{color.brand.primary}` is canonical.
5. Inline literal values inside non-token files (CSS, Swift, TS) are FORBIDDEN — lint rule `hardcoded-hex-in-renderer-output`.

## Versioning

- Bump major when removing/renaming a token (breaking).
- Bump minor when adding new tokens.
- Bump patch when adjusting `$value` within tolerance (e.g., contrast tweak that still passes WCAG).

## Canonical sources

- W3C DTCG spec: https://tr.designtokens.org/format/
- Style Dictionary v4: https://styledictionary.com/
- Sample real-world tokens: https://github.com/system-ui/theme-specification (legacy reference)
