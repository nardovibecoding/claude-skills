---
name: snap
description: Snapshot current conversation context in ≤3 sentences. Use when Bernard calls /snap (e.g. after tab-hopping and losing context). Outputs ONLY the snapshot — no preamble, no offers, no follow-up.
user_invocable: true
---

# /snap

When invoked, output a context snapshot of the current conversation in **at most 3 sentences** (fewer is better). One snapshot, then stop.

## Format

```
[topic in 1-5 words] — [what Bernard asked or is doing]. [what was just done or where we are]. [what's next or open].
```

## Rules

- **≤3 sentences total.** Hard cap. If you can do it in 1, do it in 1.
- **No preamble.** Skip "Here's a snapshot", "Currently we are…", "To summarize". Lead with the topic.
- **No follow-up offers.** Don't ask "want me to continue?" or "should we proceed?". Just the snapshot.
- **Concrete > abstract.** Name the file, command, hook, bot, or task. "auto_review_before_done.py degrade decision shipped" beats "we discussed Codex stuff".
- **Tense:** past for what's done, present for current state, "next:" prefix for open work.
- **No bullet lists, no headers, no markdown formatting** — plain prose. Code identifiers in backticks OK.
- **Open questions:** if there's an unanswered earlier question, end with `next: <question>` referencing it.

## Examples

Good:
> Codex migration cleanup — fixed `london_config_guard.py` classification (DROP) across 5 files, shipped p0-manifest + smoke-plan + degrade-decision + scope-cap. Founder folder built at `~/Desktop/Bernard_Survival_Kit/`. next: VibeIsland scan or `/debug bug "mac+london findings missing from daily bigd bundle"`.

Good (1 sentence):
> Ghostty 1.3.1 installed via brew cask, Desktop alias placed; awaiting first launch + optional starter config.

Bad (preamble + offer):
> Here's a quick snapshot of where we are: we just finished installing Ghostty and made an alias on your Desktop. Would you like me to also create a starter config?

## Output

Just the snapshot. Nothing before, nothing after.
