---
name: todo
description: Snapshot current conversation in ≤3 sentences PLUS list every open loop / dangling digression — points where Bernard asked something, got an answer, then pivoted without deciding. Also surfaces assistant-side promises never fulfilled. Use when Bernard calls /todo (or legacy /snap). No preamble, no offers, no follow-up.
user_invocable: true
---

# /todo

When invoked, output three blocks back-to-back:

1. **Snapshot** — context of the current conversation in **at most 3 sentences** (fewer is better).
2. **Open loops** — every dangling sub-topic Bernard never closed.
3. **Assistant promises** (only if any exist) — things the assistant said it would do later and never did.

Then stop. No preamble, no offers, no follow-up.

Legacy alias: `/snap` triggers the same skill.

---

## Session boundary

"This session" = since the current conversation started (oldest assistant or user turn visible to me right now). NOT since the last `/s`, NOT prior tab-hops. If this is turn 1 or 2 with no real topic yet, see "Empty/early state" below.

---

## Snapshot

### Format

```
[topic in 1-5 words] — [what Bernard asked or is doing]. [what was just done or where we are]. [where we are now].
```

### Rules

- ≤3 sentences total. Hard cap. If 1 sentence works, use 1.
- No preamble ("Here's a snapshot", "Currently we are…", "To summarize"). Lead with the topic.
- No follow-up offers. Just the snapshot.
- Concrete > abstract. Name the file, command, hook, bot, or task. "`auto_review_before_done.py` degrade decision shipped" beats "we discussed Codex stuff".
- Tense: past for done, present for current state.
- **No `next:` clause in snapshot.** That used to be where open items lived; now they belong in the Open loops block. Snapshot describes state only.
- Plain prose. No bullet lists, no headers inside the snapshot. Code identifiers in backticks OK.

### Empty/early state

If there is nothing real to summarize (turn 1–2, no concrete work yet, just greetings or skill setup):

```
Just started — no concrete topic yet.

Open loops: none.
```

Don't pad to 3 sentences. Don't invent a topic.

---

## Open loops

### What counts as an open loop

A digression Bernard never closed. The pattern:

1. Bernard asked a clarifying question, OR raised a sub-topic, OR said "wait, what about X" / "before that" / "actually" / "also" / "btw"
2. The assistant **answered** that clarification with information, options, or a recommendation
3. Bernard's next message **pivoted to a different topic, OR continued working without ever returning a decision** on the assistant's answer
4. The session moved on; that thread is still hanging

Net: *Bernard asked → assistant answered → Bernard never decided what to do with the answer → drift*.

### THE PRIMARY SIGNAL (most important)

**Any question Bernard typed that got answered, where Bernard then did NOT reply on that point.** This is the highest-value class. Always surface these. Even if Bernard's next message looked like he was continuing — if he never said "ok / go / yes / no / skip / later / drop it / not now / done" on that specific point, the loop is open.

### Sources to mine, in priority order

1. **Bernard→assistant questions** earlier in session where the assistant gave an answer (info / options / recommendation) and Bernard never replied on that point. **Top priority — these are what Bernard most wants reminded of.**
2. Any AskUserQuestion calls whose answer was not given.
3. Literal questions the assistant asked Bernard in prior turns that he scrolled past.
4. The `⏳ Still open` reminders in UserPromptSubmit hook context. **Supplementary — do not depend on this. The conversation transcript itself is the source of truth.** If the hook is missing or differs, still produce loops from sources 1–3.

### Implicit closure — when a loop is NOT open

A loop is closed (skip it) if any of these happened after the assistant answered:

- Bernard explicitly: "skip", "later", "drop it", "doesn't matter", "not now", "ok", "go", "yes", "no", "done", "fine".
- Bernard kept working on the same sub-topic with momentum (asked a follow-up that depends on the answer being accepted; e.g. assistant said "use grep" and Bernard's next was "ok now grep for X" — implicit yes).
- The assistant already executed the action without waiting for explicit go-ahead, AND Bernard didn't push back (action stands; loop closed).
- A later turn produced a definitive outcome that supersedes the question (e.g. asked "is X broken?", later evidence showed it's fine; loop closed).

If unsure → keep as open loop. Bias toward over-surfacing rather than dropping.

### Recency tags

Each loop bullet ends with a `(~Nm ago)` or `(~Nh ago)` tag, computed from the assistant turn that answered the question. Use `[clock]` UserPromptSubmit timestamps as the time source — never guess, never compute mentally.

- `(~Nm ago)` for under 60 minutes
- `(~Nh ago)` for ≥ 1 hour
- `[fresh]` for under 5 minutes — possibly still in flight, surface anyway but tag

If timestamps are unavailable, omit the tag rather than fake it.

### Bullet format

```
- <short topic> — <what was answered> ; <what decision is owed> (~Nm ago)
```

- ≤25 words per bullet (recency tag not counted).
- Good: `jcode source patch — answered Rust build is hours of work, IP-rep may make it moot; decide self-patch vs wait (~12m ago)`
- Good: `VPN exit choice — Japan vs residential SOCKS5 trade-offs given; pick one (~2h ago)`
- Bad (too vague): `jcode stuff`
- Bad (just the question): `should we patch jcode?`
- Newest first. Cap at 6 bullets. If more, list 6 most recent and append `+N older` on a final line.
- Dedupe: if the same loop was asked across multiple turns (Bernard re-asked, assistant re-answered), one bullet only — use the most recent timestamp.

### Output when none

```
Open loops: none.
```

(Single line, then stop.)

---

## Assistant promises (optional block)

Symmetric to open loops, but for things the assistant said "I'll also X" / "let me Y next" / "I'll check Z after this" and never did.

Only emit this block if there's at least one. If zero, omit entirely (do NOT print "Assistant promises: none").

### Bullet format

```
- <what assistant promised> — <not done> (~Nm ago)
```

Cap at 4 bullets, newest first.

---

## Persistence

Every successful `/todo` invocation appends one JSONL line to `~/.claude/state/todo-ledger.jsonl`:

```json
{"ts":"2026-04-30T08:23:00Z","chat_id":"<from chatid skill or env>","loops":[{"topic":"...","owed":"...","age_min":12}],"promises":[...]}
```

If the directory doesn't exist, create it. If chat_id is unavailable, omit the field.

This gives Bernard a cross-session ledger if he wants it. The skill output to chat is unchanged — file write is silent.

---

## Output template

With loops + promises:
```
<snapshot prose, ≤3 sentences>

Open loops:
- <bullet> (~Nm ago)
- <bullet> (~Nh ago)

Assistant promises:
- <bullet> (~Nm ago)
```

With loops only:
```
<snapshot prose, ≤3 sentences>

Open loops:
- <bullet> (~Nm ago)
```

No loops, no promises:
```
<snapshot prose, ≤3 sentences>

Open loops: none.
```

---

## Examples

Good (real digressions, recency tags):
```
jcode CF 403 debug — diagnosed VPN-IP reputation as cause, filed issue #80 on github.com/1jehuang/jcode. No upstream reply yet (~12h).

Open loops:
- patch jcode source — answered Rust + hours of work, IP-rep may moot; decide self-patch vs wait [fresh]
- cron-check on issue #80 — weekly schedule offered; never answered (~30m ago)
- VPN exit alternative — Japan vs residential SOCKS5 raised; pick one (~2h ago)
```

Good (early state):
```
Just started — no concrete topic yet.

Open loops: none.
```

Good (1 sentence, no loops, with assistant promise):
```
Ghostty 1.3.1 installed via brew cask, Desktop alias placed.

Assistant promises:
- send config-tweaking writeup after first launch — not done (~5m ago)
```

Bad (preamble + offer + decides for Bernard):
```
Here's a snapshot of where we are: we finished installing Ghostty. You had asked about config — I think dark theme is best. Want me to set that up?
```

Bad (literal questions instead of digressions):
```
Open loops:
- want me to file the issue?
- should I check gh later?
```
(These were answered + acted on already. Not loops.)

Bad (mental-math timestamps):
```
- VPN exit choice (~3.5h ago, roughly)
```
(Vague. Either compute from `[clock]` stamps or omit.)

---

## Output

Just the snapshot + open-loops block (+ assistant-promises block if any). Nothing before, nothing after.
