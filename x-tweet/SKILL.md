---
name: x-tweet
description: "Generate, draft, and post tweets for @nardovibecoding via X API. Vibecoding journey with Claude Code. Casual-confident tone. Auto-humanizer, engagement optimization, content calendar, trending hashtag search, draft queue, performance tracking. Single tweets only, 280 char max — NO THREADS."
triggers:
  - "tweet"
  - "post to x"
  - "write a tweet"
  - "x post"
  - "/tweet"
anti-triggers:
  - "read tweet"
  - "check twitter mentions"
  - "x api setup"
produces: "Published tweet on @nardovibecoding with engagement-optimized voice, hashtags, and self-reply"
---

# x-tweet

Generate and post tweets for @nardovibecoding. All tweets go through voice rules + humanizer before posting.

## Humanizer phase (HARD RULE — no skip)
Every draft passes through content-humanizer between Generate (step 3) and Anti-pattern check (step 4). Non-negotiable. Phase-close requires the draft to carry `humanized: true` metadata before posting. If the user requests "post this exact text", run humanizer once, show diff, ask for approval — never bypass entirely. Source: humanizer was step 3 in flow but unenforced; promoted to gated phase 2026-04-30 so we don't forget.

## Modes

| Command | What it does |
|---|---|
| `/tweet [topic]` | Draft from topic, humanize, approve, post |
| `/tweet suggest` | Read git log, suggest tweet-worthy topics (privacy-filtered) |
| `/tweet hot` | Search X for trending vibecoding/CC topics, suggest angles |
| `/tweet draft [topic]` | Generate and save to queue, don't post |
| `/tweet queue` | View saved drafts, pick one to post |
| `/tweet stats` | Pull metrics on recent tweets, identify patterns |
| `/tweet engage` | Check replies, flag big accounts, suggest responses |

## Flow (all modes)

1. **Calendar check** — read [content-calendar.md](references/content-calendar.md), suggest today's type
2. **Arc + angle selection** — pick narrative structure from [arc-types.md](references/arc-types.md), layer a framing lens from [angle-bank.md](references/angle-bank.md)
3. **Generate** — apply [voice-rules.md](references/voice-rules.md) and [templates.md](references/templates.md)
3. **Humanizer pass** — run content-humanizer, remove all AI patterns
4. **Anti-pattern check** — scan against [anti-patterns.md](references/anti-patterns.md)
5. **Hashtag** — read [hashtag-strategy.md](references/hashtag-strategy.md), search X for trending tags, pick 1-2
6. **Time check** — warn if outside peak windows (see [engagement-data.md](references/engagement-data.md))
7. **Screenshot safety** — if image attached, scan for paths/keys/IPs/chat IDs before posting
8. **Show draft** — present for approval, NEVER auto-post
9. **Post** — via X API using `scripts/post_tweet.py`
10. **Self-reply** — generate follow-up (no links until Premium), post as reply
11. **Alert** — notify TG topic thread that tweet was posted
12. **Remind** — "check replies in 3 hours"

## Voice (summary — full rules in references)

- **Tone**: casually sharing what you've been up to. Not flex, not humble.
- **Frame**: Claude Code is the hero, you're the tour guide
- **Caps**: normal capitalization
- **Punctuation**: periods, no exclamation marks
- **Length**: under 110 chars for one-liners, under 200 for standard, 280 max
- **No links** until X Premium arrives — use "link in bio" instead

## Privacy Rules (CRITICAL)

Git log and build activity are SOURCE MATERIAL ONLY. Never expose:
- File paths, function names, repo names, commit hashes
- API keys, tokens, IPs, chat IDs, usernames
- CLAUDE.md rules, MCP configs, internal architecture
- Error messages with stack traces

Reframe private → public:
- "fixed auth bug in admin_bot.py" → "Fixed a bug where my bot was using the wrong persona"
- "added model routing for MiniMax/Haiku" → "Built a system that picks the right AI model for each message"

## Posting

- **API**: X API v2 (free tier, 500 posts/month)
- **Keys**: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` from `.env`
- **Script**: `scripts/post_tweet.py`
- **Reading/searching**: twikit (cookie auth from `.env`)

## Alerts

Post notifications sent to TG:
- `chat_id`: `-1003827304557`
- `message_thread_id`: `313`

## Content Sourcing

When `/tweet suggest`:
1. Read git log from repos (last 7 days)
2. Extract: new features, bug fixes, new skills, architecture changes
3. Privacy-filter all details
4. Reframe as 3-5 public-safe tweet angles
5. Match to today's content calendar slot

When `/tweet hot`:
1. Search X via twikit for: vibecoding, claude code, AI coding, agentic engineering
2. Find trending hashtags in the space
3. Identify gaps — what's trending but uncovered
4. Suggest 3 angles based on findings

## Draft Queue

- Stored in `data/drafts.json`
- Format: `{id, text, created, type, hashtags, suggested_time}`
- `/tweet queue` shows all, pick one to post
- Auto-clean drafts older than 14 days
