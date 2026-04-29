# vibes/improv — fallback when no preset matches

When the prompt names a vibe that isn't in `encyclopedia.md` (and isn't a brand/direction/register/archetype either): do NOT silently default. Improvise.

## Procedure

1. **Extract concept words.** Pull every adjective, era, place, brand-shorthand, and texture word from the prompt. e.g. "make it feel like 1930s Shanghai jazz club with art deco gold but also kind of cyberpunk neon" → words: 1930s, Shanghai, jazz club, art deco, gold, cyberpunk, neon.

2. **Map to closest 1-3 encyclopedia entries.** Search aliases. e.g. above → `art-deco` (1930s, gold, deco) + `cyberpunk` (neon) + flavor of `hong-kong-neon` (Asian metropolis). Cite the matches with file:line in your output.

3. **Hybridize tokens.**
   - Palette: take primary color from highest-weight match, take 1-2 accents from secondaries. Don't average — pick distinctly. Above example: deco gold + black bg (deco) + neon magenta accent (cyberpunk) + neon cyan signage (HK neon).
   - Typography: display from primary, body from primary, accent from secondary. Above: Avant Garde Gothic display (deco) + IBM Plex Mono body (cyberpunk-flavored) + occasional katakana stripe (HK).
   - Shape: pick from primary; allow 1 secondary motif. Above: deco stepped pyramids + neon edge-glow as secondary.
   - Density: use primary's density rule. Above: airy with concentrated ornament (deco wins over cyberpunk's "dense saturated" — single primary).

4. **Anti-slop check on the hybrid.**
   - Are forbidden moves from primary respected? (deco forbids "rounded soft corners" — make sure cyberpunk doesn't sneak rounded.)
   - Is the accent count still ≤2 per surface?
   - Does the hybrid have a clear identity, or did averaging make it muddy?

5. **Self-document.** In the emitted `DESIGN.md`, write a `Vibe derivation` section listing the matched vibes + which tokens came from where. Bernard should be able to see exactly what you reasoned.

## Refusal triggers

- **Empty match**: zero alias hits, no recognizable era/movement word. Don't guess. Ask: "I don't recognize this vibe. Closest matches I know: <list 5>. Pick one or describe a reference image."
- **Conflicting forbidden moves**: e.g. `wabi-sabi + maximalism` (one demands negative space, the other demands every-corner-active). Surface the conflict; ask which dominates.
- **Single-word ambiguous**: "nice", "cool", "modern" — too vague. Ask for one reference (brand, movie, era, image).

## Examples

| Prompt | Improv reasoning |
|---|---|
| "art deco feel for VibeIsland dashboard" | match: `art-deco` (full); archetype: `dashboard`; surface: SwiftUI (project alias). Use deco palette + Avant Garde display + IBM Plex Mono body for trader-dense dashboard density. |
| "Studio Ghibli but for a Chrome extension" | match: `studio-ghibli` (full); surface: extension (manifest detection). Constraint: extensions are small popups — Ghibli's "lush nature" doesn't fit 400px popup. Use Ghibli's cream/sky palette + soft contour but keep MV3 density tight. Flag the surface-vibe tension in DESIGN.md. |
| "1990s Hong Kong cybercafe" | match: `hong-kong-neon` (HK) + `cyberpunk` (cybercafe) + flavor of `grunge-90s` (90s). Hybrid: HK neon palette + cyberpunk mono typography + grunge texture overlay (CRT scan lines). |
| "make it royal" | empty match. Closest: `baroque-rococo`, `art-deco`, `old-money-quiet-luxury`, `dark-academia`, `gothic`. Ask Bernard which sense of "royal" — gilt opulence (rococo), restrained heritage (old money), or gothic dignity. |

## Hybrid budget

Don't merge >3 vibes. Past 3, the result is mush. If 4+ words match, force-rank by prompt prominence and drop the weakest.
