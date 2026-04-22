# Anti-Patterns — What to Never Do

## Voice Anti-Patterns

- "I shipped X tools in Y days" — direct flex
- "Zero manual intervention" — sounds like a sales pitch
- "All built by one person" — subtle flex
- "I don't build apps, I build systems" — arrogant positioning
- "X is dead/wrong" without genuine reasoning — empty provocation
- "Just a beginner" — undermines credibility
- "Still not sure how this happened" — fake surprise
- "Can't believe this actually worked" — performative disbelief
- Any sentence with exclamation marks
- Any ALL CAPS words for emphasis
- "Game-changer", "mind-blowing", "insane" — hype words
- Starting with "So..." or "Okay so..." — filler
- "Let me tell you about..." — preamble
- "Here's the thing:" — AI pattern

## Framing Anti-Patterns

- **Incomplete chain** — describing a system with 3 layers but only showing 2. If the story ends at "memory → wiki" when the real payoff is "memory → wiki → system prompt → agent behavior changes," the tweet undersells the point.
- **Solution without destination** — "built a promotion pipeline" means nothing without "so now corrections from last Tuesday are in the agent's behavior today."
- **External hook too late** — mentioning Karpathy / notable validator in tweet 4 of 5 instead of tweet 1. Use it to open the frame, not close it.
- **Boring open** — starting with what you built instead of what was broken. The broken state is the hook.
- **Buried payoff** — the most powerful insight is the last tweet or the last paragraph. In tweets, that line IS the hook. If you have a line like "it shows me what I apparently believe, based on what I keep doing" — that's tweet 1, not the conclusion.
- **Vague payoff** — "the system now works better" instead of a specific, concrete result the reader can picture.

## Content Anti-Patterns

- Posting outside 8-10am or 6-8pm EST without good reason
- Including links without X Premium (zero engagement)
- More than 2 hashtags per tweet
- Threads longer than 5 tweets
- Retweeting yourself
- Following-for-follows
- Scheduling more than 3 tweets per day
- Posting the same template twice in one week
- Replying "thanks!" to comments (add value or don't reply)

## Screenshot Safety (CRITICAL)

Before attaching any image, scan for:
- [ ] File paths (`/Users/`, `/home/`, `~/`)
- [ ] API keys, tokens, passwords (any string > 20 chars that looks random)
- [ ] IP addresses (xxx.xxx.xxx.xxx)
- [ ] Chat IDs, user IDs, phone numbers
- [ ] Repo names that aren't public
- [ ] .env file contents
- [ ] Error messages with stack traces
- [ ] CLAUDE.md rules (reveals system architecture)
- [ ] MCP server configs, ports
- [ ] Git remote URLs for private repos
- [ ] Telegram usernames, group names
- [ ] Email addresses

**Rule**: If in doubt, don't include the screenshot. Use a demo project or crop to output only.

**Safe to show**: public GitHub repos, generic terminal output, tool installation commands, code snippets from public repos.

## Privacy Reframing

When converting private activity to public tweets:
- File names → describe the function ("my bot", "the security scanner")
- Specific numbers from private systems → round or range ("hundreds", "a few thousand")
- Internal tool names → generic descriptions ("model routing" not "route_to_minimax()")
- Error details → the lesson learned, not the error itself
- Architecture → high-level concept, not implementation
