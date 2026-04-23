---
name: eli5
description: Explain any technical topic clearly using simple language, metaphors, and a 6-question framework. Triggers "/eli5 <topic>" (full explanation) or "/1s <topic>" (single-sentence explanation). Scope: that one topic only — does NOT change tone for rest of session. Revert signals "stop caveman" / "normal mode" also revert eli5 if somehow sticky.
---

# eli5 — Explain like I'm 5

Two variants:
- `/eli5 <topic>` — full 6-question explanation (below)
- `/1s <topic>` — one simple sentence, no jargon, no framework

## Scope rule

eli5 applies ONLY to this single answer. Do NOT carry the "simple language" voice into the rest of the session. If the user follows up with a different topic, revert to normal tone. Signals to force-revert: "stop caveman", "normal mode".

## /1s variant (one sentence)

User said `/1s <topic>` → answer with exactly ONE plain-English sentence. No bullets, no framework, no metaphor stack, just the clearest possible one-liner a non-technical person would get. Max ~25 words.

## /eli5 variant (6-question framework)

Explain the topic using simple language and metaphors. No jargon. Answer these 6 questions in order:

1) **Simple version** — one metaphor, one sentence. What is this like in real life?
2) **What it affects** — if we add/change/remove this, what breaks or changes? Side effects on architecture.
3) **How others do it** — what's the common pattern? How do teams usually solve this?
4) **Risks** — what can go wrong? Worst case scenario in plain English.
5) **Trade-offs** — cost, complexity, maintenance burden — what does adopting this buy vs sacrifice?
6) **Suggestion** — what should we actually do? One clear recommendation.

Rules:
- Max 2 sentences per answer
- No technical acronyms without explaining them first
- Use analogies from everyday life (address book, recipe, light switch, etc.)
- If the topic is about our specific system (bots, VPS, memory), tie the metaphor to something Bernard already knows
- End with the suggestion **bold** and actionable
