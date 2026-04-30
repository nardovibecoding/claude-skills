# @nardovibecoding Voice Baseline

Canonical voice profile for Bernard's public persona (@nardovibecoding on X). Referenced by Mode 3 (Voice Injection) of content-humanizer. Source of truth — if this diverges from `~/.claude/skills/x-tweet/references/voice-rules.md`, that file wins (merge back here on sync).

## Tone

"Casually sharing what you've been up to" — like texting a friend about your week. Not flexing, not humble, not performing surprise. Just stating what happened.

## Frame

Claude Code is the hero. Bernard is the tour guide.
- "Claude Code set this up" > "I built this"
- "Told it what I wanted and it shipped" > "I shipped"
- Bernard's value = vision, taste, standards. CC's value = execution.

## Voice Rules (10)

1. Talk like texting a friend, not writing a bio.
2. State results matter-of-factly, don't react to them.
3. "Built a few things" > "shipped 8 tools" > "can't believe I shipped 8 tools".
4. No fake surprise, no fake modesty.
5. The casualness IS the confidence.
6. Credit Claude Code specifically — Bernard is the operator, CC is the engine.
7. "Been using X and honestly can't go back" for tool recs.
8. React to own work like a user, not a builder.
9. Share what was learned, not what was achieved.
10. When showing a win, pair it with what went wrong first.

## Hook Quality

First line decides everything. Lead with the broken state — what was wrong before — not the solution. Reader needs to feel the problem before they care about the fix.

- ❌ "Built a knowledge system that matures over time."
- ✅ "I had 150 memory files and 218 wiki articles. They couldn't talk to each other."

Always name the destination — what actually changes as a result.

- ❌ "Built a promotion pipeline for my wiki."
- ✅ "A pattern I correct today is in my agent's system prompt by next week. Automatically."

If the story has multiple layers (A → B → C), show the full chain. Cutting it short makes the payoff feel small.

## External hooks (credibility borrowing)

If a notable person/post validates the angle, use it in the first or second line — not buried at the end.

- ❌ "Built X. [3 paragraphs later] Karpathy talked about this."
- ✅ "Karpathy described a pattern I'd been building for months. Here's what he didn't mention."

## Formatting rules

- Normal capitalization (not all lowercase, not ALL CAPS)
- Periods at end of sentences. **No exclamation marks.**
- **No em-dash overuse** (one per tweet max; prefer sentence split)
- **No `..` double-dot** (use `...` for pauses or restructure)
- Line breaks between ideas (Twitter renders as visual breaks)
- No bullet lists in tweets (save for threads — but threads are disabled per current rule)

## Word choices (replace list)

| Don't say | Say instead |
|---|---|
| shipped | made, built, put together |
| leverage | use |
| robust | solid, works well |
| comprehensive | covers a lot |
| game-changer | actually useful |
| just a side project | been working on this |
| zero manual intervention | runs on its own |
| I'm just a beginner | I don't have a coding background |
| can't believe this worked | this actually works |
| no coding background at all | I don't code, CC does |

## Fact-check before publishing

Numbers, model counts, file counts, dates — verify from source, never from memory.
- ❌ "five models vote on it" (written from recall)
- ✅ check the actual script, then write "four models vote, a fifth arbitrates"

## Credit by full name

Credit tool creators with their full name, not just the tool name.
- ❌ "built on Graphify"
- ✅ "built on Graphify by Safi Shamsi"

Reason: full attribution earns goodwill, may earn a retweet, signals community awareness.

---

**Usage in Mode 3 (Voice Injection):** read this file first, then apply rules above to the draft. If the draft is for `@nardovibecoding` (X/Twitter), this IS the voice baseline — do not ask user for another example.
