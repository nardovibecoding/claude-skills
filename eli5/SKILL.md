---
name: eli5
description: Explain any technical topic clearly using simple language, metaphors, and a standard 6-question framework. Trigger: /eli5 <topic>
---

Explain the topic using simple language and metaphors. No jargon. Answer these 6 questions in order:

1) **Simple version** — one metaphor, one sentence. What is this like in real life?
2) **What it affects** — if we add/change/remove this, what breaks or changes? Side effects on architecture.
3) **How others do it** — what's the common pattern? How do teams usually solve this?
4) **Risks** — what can go wrong? Worst case scenario in plain English.
5) **Cost** — does it increase API cost, maintenance burden, or complexity?
6) **Suggestion** — what should we actually do? One clear recommendation.

Rules:
- Max 2 sentences per answer
- No technical acronyms without explaining them first
- Use analogies from everyday life (address book, recipe, light switch, etc.)
- If the topic is about our specific system (bots, VPS, memory), tie the metaphor to something Bernard already knows
- End with the suggestion bold and actionable
