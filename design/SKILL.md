---
name: design
description: Universal design skill — produces UI for SwiftUI macOS, Chrome extension, web/dashboard from one DTCG token source. Auto-routes by surface signals or explicit brand/direction/register/archetype overrides. Triggers on /design, "design this", "style this", "make a UI for", "build a dashboard/popup/component". Always ends with anti-slop + self-critique gates.
---

# /design — universal design skill

Single source of truth for visual style across **SwiftUI macOS** (VibeIsland), **Chrome extension** (popup/panel), and **web dashboard / React** (PM bot dashboards). One DTCG `tokens.json` per project, three thin renderers.

---

## How autorouting works

On invocation, scan the user prompt + surrounding context. Resolve six axes in order; the first match wins per axis. Never ask if any axis is filled.

### 0. Project alias (highest priority — pins surface)

If the prompt names a known project (vibe-island, pm-bot, dagou, chrome-ext, NardoWorld, big-d, etc.) match against `project-aliases.md` — pins the renderer regardless of cwd. Project alias also supplies a default vibe + archetype if user gave no other axis.

### 1. Vibe (plain-English style — 80 layman names)

If the prompt names a vibe from `vibes/encyclopedia.md` (case-insensitive alias substring): load that entry directly. Vibes override directions+registers (those become legacy designer-jargon fallback). Triggers cover historical movements (art-deco, bauhaus, memphis, rococo), eras (mid-century, 80s synthwave, y2k, frutiger-aero), internet aesthetics (vaporwave, cottagecore, dark-academia, liminal-spaces), film/animation (studio-ghibli, wes-anderson, akira-cyberpunk, film-noir), fashion (techwear, streetwear, old-money, normcore), regional (hong-kong-neon, wabi-sabi, scandinavian-hygge, korean-y2k), subcultures (cyberpunk, steampunk, solarpunk), materials (risograph, pixel-art, glitch, holographic), brand-archetypes (apple-clean, bloomberg-terminal, nintendo-playful, tiffany), and moods (cozy, moody, sharp, misty). See `vibes/encyclopedia.md` for the full 80.

Multi-vibe combine with `+`: `/design art-deco + bloomberg-terminal` merges palettes (deco gold + terminal black bg + amber data) and typography (Avant Garde display + IBM Plex Mono body). See `vibes/improv.md` rules.

### 2. Brand (locks all 4 token families)

If the prompt names a brand from `brands/` (case-insensitive substring match): load `brands/<name>.md` directly. Examples: "make it linear-style", "stripe vibes", "like notion", "feels like tesla", "claude colors".

Available brands (81 total): see `brands/`. Common: apple, linear-app, stripe, notion, figma, vercel, tesla, ferrari, lamborghini, claude, cursor, raycast, supabase, vercel, airbnb, uber, spotify, pinterest, framer, sanity, mistral-ai, cohere, x-ai, posthog, mongodb, hashicorp, nvidia, ibm, intercom, mintlify, resend, sentry, replicate, runwayml, lovable, miro, figma, expo, kraken, coinbase, revolut, wise, toss, kakao, line, mercari, pinkoi, dcard, etc.

Note: Bernard rarely names brands; vibes are usually the better match. Brand match is reserved for explicit "make it stripe-style" requests.

### 3. Direction (5 OKLch palette families — designer-jargon fallback)

If no brand but prompt names a direction: load `directions/<name>.md`. Trigger words:
- **editorial** / "magazine" / "long-form" / "journalism" → `directions/editorial-monocle.md`
- **minimal** / "clean" / "simple" / "default" → `directions/modern-minimal.md`
- **tech utility** / "data dense" / "terminal" / "ide" / "trader" / "dashboard" → `directions/tech-utility.md`
- **brutalist** / "raw" / "harsh" / "industrial" / "grid" → `directions/brutalist.md`
- **soft** / "warm" / "cozy" / "earth tone" / "human" → `directions/soft-warm.md`

### 4. Register (9 cultural locks — designer-jargon fallback)

If prompt names a register, load `registers/<name>.md`. Registers commit to a *culture*, not a palette. A "soft warm × startup-techy" project is allowed; a "soft warm × luxury-editorial" project is also allowed. Locks vibe, not values.

Triggers: "startup-techy", "luxury-editorial", "academic", "consumer-playful", "enterprise-trust", "underground-zine", "civic-formal", "craft-artisan", "cyber-streetwear".

### 4. Archetype (12 layout shapes)

If prompt names a layout type, load `archetypes/<name>.md`. Triggers: "dashboard", "hero", "pricing", "deck/slides", "chart", "table", "glassmorphism / glass", "calendar", "chat ui", "footer", "landing", "popup".

---

## Surface auto-detection (renderer)

Renderer is **never asked**. Detect from project context:

| Signal | Renderer |
|---|---|
| Open `.swift` file, `Package.swift` or `*.xcodeproj` in cwd or recent reads | `renderers/swiftui.md` |
| `manifest.json` with `"manifest_version"` field | `renderers/extension.md` |
| `package.json` with `react`/`next`/`vite`/`tailwindcss` | `renderers/html.md` |
| Default fallback | `renderers/html.md` |

Multiple signals → the more specific wins (SwiftUI > extension > html).

---

## Empty-prompt default routing

If user invokes `/design` with no axes named:

| Surface (auto-detected) | Default direction | Default register |
|---|---|---|
| SwiftUI / VibeIsland | `tech-utility` | `craft-artisan` |
| Chrome extension | `modern-minimal` | `startup-techy` |
| Web dashboard / PM bot | `tech-utility` | `enterprise-trust` |
| Marketing / landing / blog | ASK 1 question (editorial vs minimal vs brutalist) | inferred from direction |

---

## Universal token contract — DTCG (W3C stable, Oct 2025)

Every project gets one file: `<project>/design/tokens.json` in DTCG format. This is the canonical source. The chosen renderer transforms it into native artifacts.

Schema: see `tokens/dtcg-schema.md`. Minimum required token groups: `color`, `typography`, `spacing`, `radius`, `elevation`, `motion`. Use `{group.token}` references for cross-token derivation. Hex must be sRGB. Contrast pairs must pass WCAG AA 4.5:1 (lint enforces).

Companion `DESIGN.md` (human-readable, per `tokens/design-md-schema.md`) lives next to `tokens.json` for prose rationale + Do's/Don'ts.

---

## Execution flow (every /design call)

1. **Resolve axes** — brand OR (direction + register + archetype). Brand locks everything.
2. **Detect surface** — pick renderer.
3. **Emit `tokens.json`** — DTCG-compliant, with refs.
4. **Emit `DESIGN.md`** — prose rationale, Do/Don't.
5. **Run renderer** — produce native artifact (Swift Color extension, CSS vars + Tailwind theme, MV3 popup CSS).
6. **Run lint** — `checks/lint.md` (DTCG rules, contrast, orphan tokens, color-count, font-count).
7. **Run anti-slop** — `checks/anti-slop.md` (accent-twice, density-mood-match, AI-cliche detection).
8. **Run self-critique** — `checks/self-critique.md` (5-dimensional review).
9. **Report** — surface decisions made + lint+slop+critique verdicts.

Steps 6/7/8 are **unconditional**. Never skipped. Never optional.

---

## Override syntax

- `/design <brand>` — lock to brand. e.g. `/design linear-app`, `/design stripe`.
- `/design <direction>` — lock direction. e.g. `/design brutalist`.
- `/design <register>` — lock register. e.g. `/design startup-techy`.
- `/design <archetype>` — emit archetype scaffold. e.g. `/design dashboard`.
- `/design <a> + <b>` — combine. e.g. `/design tech-utility + craft-artisan`.
- `/design refresh` — re-emit `tokens.json` + renderer artifact from existing `DESIGN.md`.
- `/design audit` — run lint + anti-slop + self-critique on existing files only, no emit.
- `/design extract <url>` — extract DTCG tokens from a public site (Playwright-based; uses `tokens/extract.md` recipe).

---

## Hard rules (no exceptions)

1. **One token source.** All renderers consume the same `tokens.json`. No hardcoded hex/font/spacing in any rendered file.
2. **Token-only fills.** Anywhere a value would be a literal, use a token reference. The lint will reject hex literals in renderer output.
3. **Max 2 accent uses per surface.** Anti-slop catches >2.
4. **Max 2 font families per surface.** Lint enforces.
5. **Max 6 base color tokens, max 12 with shades.** Lint enforces. Beyond this is decoration drift.
6. **All spacing on the chosen scale.** No off-scale magic numbers.
7. **All contrast pairs ≥ WCAG AA 4.5:1.** Lint enforces.
8. **SwiftUI HIG audit on Swift output.** Apple HIG conformance per `renderers/swiftui.md`. Liquid Glass material rules apply for iOS 26+ targets.
9. **Chrome MV3 constraint: no CDN/external Tailwind.** Tailwind must be locally bundled. Per `renderers/extension.md`.
10. **DTCG `$type` annotations required.** Each token carries `$type` (color, dimension, fontFamily, etc.) for cross-platform emission.

---

## Files in this skill

```
SKILL.md                     # this file
tokens/
  dtcg-schema.md             # universal token format spec
  design-md-schema.md        # human prose companion
  extract.md                 # site → DTCG token recipe
brands/                      # 81 vendored brand DESIGN.md files
directions/                  # 5 OKLch palette families
  editorial-monocle.md
  modern-minimal.md
  tech-utility.md
  brutalist.md
  soft-warm.md
registers/                   # 9 cultural locks
  startup-techy.md
  luxury-editorial.md
  academic.md
  consumer-playful.md
  enterprise-trust.md
  underground-zine.md
  civic-formal.md
  craft-artisan.md
  cyber-streetwear.md
archetypes/                  # 12 layout shapes
  dashboard.md
  hero.md
  pricing.md
  deck.md
  chart.md
  table.md
  glassmorphism.md
  calendar.md
  chat.md
  footer.md
  landing.md
  popup.md
renderers/
  swiftui.md                 # SwiftUI Color/Font/CornerRadius + HIG audit + Liquid Glass
  html.md                    # CSS vars + Tailwind v4 theme
  extension.md               # MV3 popup, local Tailwind, Shadow DOM
checks/
  lint.md                    # 7 DTCG lint rules + a11y
  anti-slop.md               # accent-twice, density, AI-cliche
  self-critique.md           # 5-dim review
```

---

## Sources

Built from: `google-labs-code/design.md` (token spec), `nexu-io/open-design` (71 brand DESIGN.md, 5 directions, anti-slop), `OpenCoworkAI/open-codesign` (12 archetypes), `Raylinkh/design-register-commit` (9 registers), `kwakseongjae/oh-my-design` (Philosophy Layer brands), DTCG W3C spec (Oct 2025 stable), Style Dictionary v4 (SwiftUI emit pattern), `lightscape-jm/swiftui-hig-audit` (HIG rules), `199-biotechnologies/swiftui-claude-skills` (Liquid Glass), `aficat/design-linter` + `destefanis/design-lint` (lint rules).
