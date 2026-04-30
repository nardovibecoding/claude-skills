---
name: tweet
description: |
  Unified tweet pipeline — extract narrative (story) → humanize draft → post to X. Single tweets only, 280 char max — NO THREADS. Casual-confident vibecoding tone for @nardovibecoding.
  Triggers: "/tweet", "/tweet [topic]", "/tweet story", "/tweet humanize <text>", "/tweet suggest", "/tweet hot", "/tweet draft", "/tweet queue", "/tweet stats", "/tweet engage", "tweet", "post to x", "write a tweet", "x post", "/story" (legacy), "extract story", "narrative for x", "sounds like AI", "make it human", "add personality", "fix AI writing", "inject voice".
  Anti-triggers: "read tweet", "check twitter mentions", "x api setup".
  NOT FOR: threads (single tweet only), reading X mentions, X API setup.
  Produces: published tweet on @nardovibecoding with humanized voice + topic-matched hashtags + optional self-reply OR a session-narrative long-form article ready to paste into X.
user-invocable: true
---

<tweet>

Unified pipeline for @nardovibecoding posts. Verb dispatch covers full pipeline (topic → draft → humanize → post) and standalone primitives (story extraction, humanize-only).

## Verb dispatcher

| Verb / form | Mode | Reference / script |
|---|---|---|
| `/tweet [topic]` | Full pipeline: angle → draft → humanize → post | `references/voice-rules.md`, `references/anti-patterns.md`, `references/templates.md`, `references/humanizer-modes.md`, `scripts/post_tweet.py` |
| `/tweet story` (or legacy `/story`) | Extract session narrative → long-form article (paste into X manually) | `references/story-extraction.md` (folded from retired `story` skill, 2026-04-30) |
| `/tweet humanize <text>` | Standalone humanizer pass | `references/humanizer-modes.md` (folded from retired `content-humanizer` skill, 2026-04-30), `references/humanizer/nardovibecoding-voice.md`, `references/humanizer/ai-tells-checklist.md`, `references/humanizer/voice-techniques.md`, `scripts/humanizer_scorer.py` |
| `/tweet suggest` | Read git log + session, propose tweet-worthy topics (privacy-filtered) | `references/angle-bank.md` |
| `/tweet hot` | Search X for trending vibecoding/CC topics, suggest angles | `references/hashtag-strategy.md` |
| `/tweet draft` | Save draft to `data/drafts.json` for later review | `data/drafts.json` |
| `/tweet queue` | Show pending drafts | `data/drafts.json` |
| `/tweet stats` | Engagement performance for past tweets | `scripts/tweet_stats.py` |
| `/tweet engage` | Reply to mentions / DMs (read-only by default) | `references/engagement-data.md` |

## Humanizer phase (HARD RULE — no skip)

Every draft passes through the humanizer between Generate and Anti-pattern check. Non-negotiable. Phase-close requires the draft to carry `humanized: true` metadata before posting. If the user requests "post this exact text", run humanizer once, show diff, ask for approval — never bypass entirely.

The humanizer body lives in `references/humanizer-modes.md` plus the voice baseline files in `references/humanizer/`. Voice hierarchy:
1. Target = `@nardovibecoding` / X / Bernard's public persona → load `references/humanizer/nardovibecoding-voice.md`. That IS the voice baseline. Do not ask for another example.
2. Otherwise ask ONE question: "Before I rewrite this, give me an example of content you've written or read that felt right."

## Story extraction phase

When `/tweet story` fires, the goal is to extract the 0→1 narrative from THIS coding session and produce a long-form article suitable for an X long-tweet (≤4000 chars on Premium). The tone is reflective + universal — not a build log.

Sources, in order:
1. **Conversation context** — full exchange in memory. Primary source.
2. **Librarian log** — `~/NardoWorld/meta/librarian-log.md` today's entries.
3. **Transcript JSONL** (only if compacted) — `tail -300` on the path from `/tmp/claude_statusline.json` → `transcript_path`.

Find-the-angle rules + bad-vs-good examples + voice rules: `references/story-extraction.md`.

## Auto-detect hooks (preserved across merge)

The merge (2026-04-30) preserves two hook touchpoints:
- `~/.claude/hooks/story_detector.py` (Stop hook) — detects when a session has shipped 0→1 work and writes a JSON signal to disk for later `/tweet story` consumption. Hook does NOT invoke the skill body — it only writes the signal. Hook unchanged across merge.
- `~/.claude/hooks/gmail_humanizer.py` (PostToolUse hook on Gmail draft) — surfaces a reminder text "Run /tweet humanize on the draft body before sending." Hook only emits the reminder; no skill body import. Reminder text updated 2026-04-30 to reference `/tweet humanize` (was `content-humanizer`).

## Naming + retired skills

Merged 2026-04-30 (skill-consolidation step 21): combined `x-tweet` + `story` + `content-humanizer` into `/tweet` with verb dispatch. All three source skills retired.

| old skill | post-merge fate |
|---|---|
| `x-tweet` | retired — natural-language triggers ("tweet", "post to x") still route here via `/tweet` skill description |
| `story` | retired — `/tweet story` covers; legacy `/story` triggers also route here |
| `content-humanizer` | retired — `/tweet humanize <text>` covers; gmail_humanizer hook reminder updated to point at `/tweet humanize` |

## Cross-cutting safety rules

- **NO THREADS.** Single tweet only, 280 char max. If a topic doesn't fit, write a long-form article via `/tweet story` and paste manually as long-tweet on Premium — but never script-post a thread.
- **Humanizer is non-negotiable.** Every post passes through. `humanized: true` metadata gates the post.
- **Privacy filter on `/tweet suggest`.** Git log scan strips paths/emails/secrets before showing topics.
- **Engagement is read-only by default.** `/tweet engage` shows mentions/replies; only writes when user explicitly approves a reply draft.

## When to skip this skill

- Reading mentions/DMs (no merge surface; X has its own UI).
- Multi-tweet threads (use a different tool — this skill refuses).
- Setting up X API credentials (one-time setup, see `references/voice-rules.md` for credential rotation only).

</tweet>
