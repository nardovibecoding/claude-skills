---
name: snap
description: Legacy alias for /todo. Snapshot conversation + open loops + assistant promises.
user_invocable: true
---

# /snap → /todo

Legacy alias. The actual skill is `/todo` — invoke it directly. See `~/.claude/skills/todo/SKILL.md`.

When `/snap` is invoked, behave exactly as `/todo`:

1. **Snapshot** — current conversation in ≤3 sentences.
2. **Open loops** — every dangling sub-topic Bernard never closed.
3. **Assistant promises** — things the assistant said it would do later and never did (only if any exist).
4. **Resolution mode** — immediately drive 1-by-1 via AskUserQuestion (one loop per question). Skip if `list-only` / "just list" / "no questions" in invocation, or zero loops.

No preamble, no offers, no chit-chat between blocks.
