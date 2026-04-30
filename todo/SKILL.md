---
name: todo
description: Snapshot current conversation in ≤3 sentences PLUS list every unanswered question from this session. Use when Bernard calls /todo (or legacy /snap). Outputs snapshot + open-questions list — no preamble, no offers, no follow-up.
user_invocable: true
---

# /todo

When invoked, output two blocks back-to-back:

1. **Snapshot** — context of the current conversation in **at most 3 sentences** (fewer is better).
2. **Open questions** — every unanswered question raised earlier in this session that Bernard has not addressed.

Then stop. No preamble, no offers, no follow-up.

Legacy alias: `/snap` triggers the same skill.

## Snapshot format

```
[topic in 1-5 words] — [what Bernard asked or is doing]. [what was just done or where we are]. [what's next or open].
```

### Snapshot rules

- ≤3 sentences total. Hard cap. If 1 sentence works, use 1.
- No preamble ("Here's a snapshot", "Currently we are…", "To summarize"). Lead with the topic.
- No follow-up offers. Just the snapshot.
- Concrete > abstract. Name the file, command, hook, bot, or task. "`auto_review_before_done.py` degrade decision shipped" beats "we discussed Codex stuff".
- Tense: past for done, present for current state, "next:" prefix for open work.
- Plain prose. No bullet lists, no headers inside the snapshot. Code identifiers in backticks OK.

## Open questions block

Header: `Open:` (single line label, then one bullet per question).

Sources to mine, in priority order:
1. The `⏳ Still open (N unanswered question(s) from earlier)` reminders in UserPromptSubmit hook context.
2. Any AskUserQuestion calls earlier in this session whose answer was not given.
3. Any literal questions you (the assistant) asked Bernard in prior turns that he scrolled past or did not address.

### Open-questions rules

- One bullet per open question. Quote ≤15 words. Strip "want me to" / "should I" if shortening helps.
- Newest first. Cap at 6 bullets — if more, list 6 most recent and append `+N older` on a final line.
- If zero open questions, write `Open: none.` on a single line and stop.
- No commentary. Do not answer the questions, do not pick one, do not ask which to address.

## Output template

With opens:
```
<snapshot prose, ≤3 sentences>

Open:
- <question 1>
- <question 2>
- <question 3>
```

No opens:
```
<snapshot prose, ≤3 sentences>

Open: none.
```

## Examples

Good:
```
Codex migration cleanup — fixed `london_config_guard.py` classification (DROP) across 5 files, shipped p0-manifest + smoke-plan + degrade-decision. Founder folder built at `~/Desktop/Bernard_Survival_Kit/`. next: VibeIsland scan.

Open:
- continue eval-strats wire (step 15)?
- patch xcrawl stale prose now or later?
- which push pipeline first?
```

Good (1 sentence, no opens):
```
Ghostty 1.3.1 installed via brew cask, Desktop alias placed; awaiting first launch.

Open: none.
```

Bad (preamble + offer + answers questions):
```
Here's a snapshot of where we are: we finished installing Ghostty. You had asked about config — I think we should use the dark theme. Want me to set that up?
```

## Output

Just the snapshot + open block. Nothing before, nothing after.
