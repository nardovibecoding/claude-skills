# deck — slide deck, 16:9 frames

Presentation slides. 16:9 aspect. Title + content patterns.

## When to use

- Pitch decks, internal presentations.
- Tutorial slide flows.
- Roadmap reviews, OKR reviews.

## Structural skeleton

```
┌─────────────────────────────┐  16:9 (1920×1080 or 1280×720)
│ ▢ slide-N                   │  slide number top-right
│                             │
│   TITLE                     │  64-96px
│   subtitle                  │  24-32px
│                             │
│   ▢ ▢ ▢                     │  content (bullets / chart / image)
│                             │
│   footer · brand · date     │  12-14px
└─────────────────────────────┘
```

## Required components

- **Frame**: fixed 16:9 aspect, max 1920×1080.
- **Title slide**: brand mark, deck title, author + date, single accent color block.
- **Section divider**: number + section name, full-bleed accent.
- **Content slide patterns**: title-only, title+bullets, title+chart, title+image, title+quote.
- **End slide**: thanks / contact / Q&A.

## Common mistakes

- More than 6 bullet points per slide.
- Mixing chart styles across deck.
- Tiny body text (<24px on a 1920 frame).
- Animation transitions per element.
- Slide number absent — kills navigation in Q&A.

## Density rules

- Body text minimum 24px on 1920×1080 frame.
- Title minimum 60px.
- Margins: 80-120px outer, 40px between elements.
- Max 60-70 chars per line.

## Accessibility notes

- Reading order matches visual order (top-left → bottom-right).
- High contrast (≥7:1) for projection in lit rooms.
- Don't rely on color alone for chart series — pattern fills + labels.
- Provide PDF export with selectable text.

## Tooling

- For HTML decks: emit Reveal.js or Slidev compatible markdown.
- For pptx: use the `pptx` skill for actual file emission.
- Use shared DTCG `tokens.json` for accent + type so deck matches product.
