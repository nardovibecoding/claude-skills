---
name: todo
description: Snapshot current conversation in ≤3 sentences PLUS list every open loop / dangling digression from this session — points where Bernard asked a clarification, got an answer, then never circled back to a decision. Use when Bernard calls /todo (or legacy /snap). No preamble, no offers, no follow-up.
user_invocable: true
---

# /todo

When invoked, output two blocks back-to-back:

1. **Snapshot** — context of the current conversation in **at most 3 sentences** (fewer is better).
2. **Open loops** — every dangling digression: a sub-topic where Bernard asked a clarifying question, got an answer from the assistant, and then pivoted to a new topic without giving a decision / "go" / "do X" / "ok next" on the original point. The original thread is still hanging — Bernard never told the assistant what to do with that information.

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

## Open loops block

Header: `Open loops:` (single line label, then one bullet per loop).

### Detection logic — what counts as an open loop

Scan back through the entire session, oldest to newest, looking for **digressions Bernard never closed**. The pattern:

1. Bernard asked a clarifying question, OR raised a sub-topic, OR said "wait, what about X" / "before that" / "actually" / "also"
2. The assistant **answered** that clarification with information, options, or a recommendation
3. Bernard's next message **pivoted to a different topic** (or kept going with no decision verb on the original) — never said "ok do it" / "go" / "skip" / "yes" / "no" / "later" on the assistant's reply
4. The session moved on; that thread is still hanging

So the loop is: *Bernard asked → assistant answered → Bernard never decided what to do with the answer → topic drifted away*.

Each loop = one decision Bernard owes the original sub-topic. The bullet should remind him **what the answered point was** + **what decision is still owed**.

### Sources to mine, in priority order

1. The `⏳ Still open (N unanswered question(s) from earlier)` reminders in UserPromptSubmit hook context — but these are usually assistant→Bernard questions; treat as one source, not the only one.
2. **Bernard→assistant clarifications** earlier in session where the assistant's answer offered options / facts / a recommendation, and Bernard's next message pivoted instead of deciding.
3. Any AskUserQuestion calls whose answer was not given.
4. Any literal questions the assistant asked Bernard in prior turns that he scrolled past.

### Open-loops rules

- One bullet per loop. Format: `<short topic> — <decision owed>`. ≤20 words.
  - Good: `jcode source patch — decided to file issue instead; build-from-source still pending if upstream silent`
  - Good: `VPN exit choice — Japan vs residential SOCKS5; no decision after researching`
  - Bad (too vague): `jcode stuff`
  - Bad (just the question): `should we patch jcode?`
- Newest first. Cap at 6 bullets — if more, list 6 most recent and append `+N older` on a final line.
- Skip loops Bernard explicitly closed later ("skip", "later", "doesn't matter", "drop it").
- If zero open loops, write `Open loops: none.` on a single line and stop.
- No commentary. Do not answer / decide / pick / ask which to address.

## Output template

With loops:
```
<snapshot prose, ≤3 sentences>

Open loops:
- <topic> — <decision owed>
- <topic> — <decision owed>
- <topic> — <decision owed>
```

No loops:
```
<snapshot prose, ≤3 sentences>

Open loops: none.
```

## Examples

Good (loops detected from real digressions):
```
jcode CF 403 debug — diagnosed VPN-IP reputation as cause, filed issue #80 on github.com/1jehuang/jcode. No reply yet (12h). next: wait for upstream or self-patch.

Open loops:
- patch jcode source — answered (Rust, ~hrs work, IP-rep fix may be moot); no decision after Bernard said "lets go" then pivoted to issue
- cron-check on jcode issue — offered weekly schedule; never answered
- VPN exit alternative — Japan vs residential SOCKS5 raised, no choice made
```

Good (1 sentence, no loops):
```
Ghostty 1.3.1 installed via brew cask, Desktop alias placed; awaiting first launch.

Open loops: none.
```

Bad (preamble + offer + decides for Bernard):
```
Here's a snapshot of where we are: we finished installing Ghostty. You had asked about config — I think dark theme is best. Want me to set that up?
```

Bad (lists literal questions instead of digressions):
```
Open loops:
- want me to file the issue?
- should I check gh later?
```
(These were already answered + acted on. Not loops.)

## Output

Just the snapshot + open-loops block. Nothing before, nothing after.
