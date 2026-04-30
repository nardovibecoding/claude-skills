---
name: voice-and-hook
description: |
  Copywriting rubric for README openings. Turns generic "this is a tool that does X"
  into problem-statement hooks that make a scrolling dev actually stop.

  USE FOR:
  - Every new README's top 15 lines (tagline + opening paragraph + first bold claim)
  - Upgrading existing READMEs that underperform
  - Always run alongside readme-playbook.md + publish-workflow.md

allowed-tools:
  - Read
  - Write
  - Edit
---

# Voice & Hook — README Opening Rubric

The top 15 lines decide whether anyone scrolls. Most OSS READMEs waste them on "This is a project that..." opening. Here's how to not be that.

---

## The Hook Formula

Every great README opens with three moves in this order:

```
1. PAIN           — a specific, familiar pain the reader has had this week
2. CONSEQUENCE    — what it costs them (time, money, sanity)
3. PROMISE        — what this tool does about it, in one bold line
```

Three lines max. Zero filler.

### Examples

**Bad (generic, product-first):**
> This is a tool that helps you manage sessions in Claude Code by providing hooks and skills for saving conversation state.

**Good (pain-first, opinionated):**
> You just `/clear`'d. That conversation is gone — the design you debugged for two hours, the plan you finally agreed on, the context Claude had just built up. Gone.
>
> **Never again.**
>
> `/s` saves. `/crash` recovers. Deferred-save catches the ones you forgot. Zero API calls.

Notice:
- Opens with the exact moment the reader has felt this week
- Names the specific loss (time invested, context built, agreement reached)
- Cuts to the promise with a single bold line
- Uses the reader's vocabulary (`/clear`, not "terminate session")

---

## Hook archetypes (rotate across your portfolio)

The pain-consequence-promise formula is the *spine*. The *angle* you take is the variable. Three archetypes are approved — pick ONE per repo. Spread across the three so your portfolio doesn't read like the same hook copy-pasted with different nouns.

### Archetype F — Question-led

Open with a sharp question the reader can't answer. The question IS the pain. Then twist the silence into the promise.

> "What's silently broken on your VPS right now? You don't know. That's the problem. **Six daemons, one daily report, every morning.**"

Rules:
- The question must be answerable only by *not knowing* (epistemic gap, not trivia)
- ≤2 sentences before the bold close
- Works best for: monitoring, observability, audit, status tools

### Archetype G — Antagonist-named

Name the enemy. Make it specific, almost personified. Then deploy the tool against it.

> "Sprawl wins by inches. One stale package this week. One drifted config next. One silently dead cron the week after. **Six scouts. One report. Sprawl loses.**"

Rules:
- The antagonist must be a force, not a competitor product
- Examples: drift, sprawl, silence, leakage, debt, chaos, entropy
- Three concrete crimes minimum, then the counterstrike
- Works best for: enforcement, ops, hygiene, defense tools

### Archetype I — Sensory scene

Drop the reader inside the failure. Specific time, specific number, specific consequence. They smell it before they read the fix.

> "It's 14:03. Three of your timers just fired. Two collided. Today's bundle froze at 8 of 18 entries. You'll notice next Sunday. **One chain. One timer. Six producers.** Fix."

Rules:
- One concrete moment (clock time, weekday, log line) in the first sentence
- One numeric loss (entries, percent, hours) in the second
- The reader must be able to picture themselves in the scene
- Works best for: failure-mode tools, diagnostics, post-mortem-driven tools

### Picking the archetype

| project type | default archetype | why |
|---|---|---|
| monitoring / audit / status | F (Question-led) | the pain IS the unknown |
| enforcement / hygiene / defense | G (Antagonist-named) | needs a villain to react to |
| diagnostics / failure-mode / debug | I (Sensory scene) | the failure IS the pitch |
| anything else | pick the one your portfolio uses LEAST | rotation > repetition |

After 3 repos, audit the portfolio. If 2+ use the same archetype, the next one switches. This is brand-level discipline, not per-repo.

---

## Voice principles

These apply across every line in the README, not just the hook.

### 1. Short sentences. Fragments welcome.
Long sentences in a README = reader bails. Variable rhythm beats academic prose every time.

### 2. Second person. Direct address.
"You just lost your session" > "Users may experience session loss."

### 3. Name the pain specifically.
- Weak: "Managing conversation state is hard."
- Strong: "You `/clear`'d by accident and lost 90 minutes of context."

### 4. Bold the one claim you want them to remember.
Not every third line. One per section, max. Use sparingly.

### 5. Kill corporate jargon.
Ban list: `leverage, utilize, seamless, robust, streamline, optimize, enable`. These are AI-generated tells. Every one of them has a plainer word.

### 6. Skip throat-clearing.
- Cut: "In today's fast-moving AI landscape..."
- Cut: "It is important to note that..."
- Cut: "This project aims to..."

Start where the story starts.

### 7. Show, don't tell.
- Tell: "Installation is easy."
- Show: `curl -fsSL https://... | bash`

### 8. One tool = one promise.
If you can't summarize the pitch in ten words, the project is scoped wrong or the README is.

---

## Anti-patterns (AI-generated tells)

Dead giveaways that a README was written by AI with no editing pass:

- "Revolutionize your workflow"
- "Powerful yet lightweight"
- "Harness the power of"
- "Comprehensive solution for..."
- "Game-changing"
- Every heading starts with a gerund: "Empowering X", "Streamlining Y"
- Three-adjective noun phrases: "fast, flexible, and extensible"
- Closing section titled "Conclusion" or "Summary"
- "Feel free to contribute!"

If you wrote any of these, rewrite. The reader's internal spam filter is already trained on them.

---

## Opening structure template

Use this as a scaffold, then rewrite each piece in your own voice:

```markdown
# <Project Name>

**<10-word bold promise. Problem-led, not product-led.>**

<3-5 line paragraph opening with the specific pain, naming the stakes, landing on the "here's what this does" turn. No "this project provides..." phrasing.>

<Optional: one-liner install so the reader can try it before finishing the README.>

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/<repo>/main/install.sh | bash
```

<One sentence: what you get after the install. What's now different.>
```

### Real example (session continuity)

```markdown
# Claude Session Continuity

**Your Claude Code conversations don't have to disappear.**

You know the moment. You `/clear` by reflex, or close a terminal window with a pending plan inside, or the laptop dies mid-session — and 90 minutes of context is gone. The tool remembers nothing. You start over.

This fixes that. Three commands, two hooks, zero API calls.

```bash
curl -fsSL https://raw.githubusercontent.com/nardovibecoding/claudecode-session-continuity/main/install.sh | bash
```

After: `/s` saves the current session. `/crash` recovers any session that ended without `/s`. Deferred-save auto-triggers when you `/clear` or close — so accidental loss just works.
```

Notice: the pain is named specifically. The promise is bold and short. The install is *above* the detailed explanation so the reader can try it on impulse.

---

## Install instructions — default to one-liner

Every tool that can be installed with one line, should be. This is the homebrew/rustup/ollama standard and readers expect it.

### Required pattern

```markdown
```bash
curl -fsSL https://raw.githubusercontent.com/<user>/<repo>/main/install.sh | bash
```
```

### Install script requirements

The `install.sh` must work both locally (cloned + `./install.sh`) and via curl-pipe (`BASH_SOURCE[0]` empty or siblings missing). Detect which mode you're in at the top:

```bash
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [ -n "$SCRIPT_PATH" ] && [ -d "$(dirname "$SCRIPT_PATH")/hooks" ]; then
  REPO_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
else
  git clone --depth 1 "$REPO_URL" "$CACHE_DIR"
  REPO_DIR="$CACHE_DIR"
fi
```

See `publish-workflow.md` §2 for the full idempotent installer template.

### When you can't do one-liner

Only skip if:
- The tool requires interactive config (API keys) that must be collected before install
- The tool is a library, not an installable binary (in which case show the `pip install` or `npm install` line instead)

---

## Writing process

For any new README:

1. Write the three-line hook FIRST, before any other section. Rewrite it three times.
2. Read it out loud. If you sound like a product brochure, rewrite.
3. Delete every gerund-heading and adjective-stack.
4. Have one friend who is NOT in the project read the first 15 lines. Ask: "would you try this?" If they hesitate, the hook is broken.
5. Only after the opening works: write the rest using `readme-playbook.md` structure.

---

## Quick checklist before publish

- [ ] Opens with specific pain, not "this is a tool that..."
- [ ] One bold claim in the first 15 lines
- [ ] One-liner install visible above the fold
- [ ] Zero banned corporate words (leverage/utilize/seamless/robust/streamline)
- [ ] Second person throughout
- [ ] First working command within 3 scrolls
- [ ] At least one sentence that reads like a person, not a marketing deck
