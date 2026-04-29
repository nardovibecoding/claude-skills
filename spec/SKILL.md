---
name: spec
description: Render the current conversation's ship spec in plain English. Bare /spec shows the most-recent spec (the one you just shipped/audited). /spec <slug> targets a specific past spec. /spec --audit appends audit verdict. Triggers - /spec, "show me the spec", "what's the spec", "spec summary".
user-invocable: true
---

<spec>
Render a Phase 1 ship spec in plain English bullets. No jargon, no codes, no scaffolding.

## Step 1: Resolve target

Parse args. Three modes:
- bare `/spec` → render the **most-recent** spec (current conversation's)
- `/spec <slug>` → render that specific slug's spec
- `/spec [<slug>] --audit` → render + audit mode (slug optional; bare + --audit uses most-recent)

## Step 2A: Bare mode → resolve to most-recent spec

```bash
LATEST=$(ls -t ~/.ship/*/goals/01-spec.md 2>/dev/null | head -1)
[ -z "$LATEST" ] && { echo "no ship specs found in ~/.ship/"; exit 0; }
SLUG=$(echo "$LATEST" | sed -E 's|.*/\.ship/([^/]+)/goals/01-spec\.md|\1|')
echo "Latest: $SLUG"
```

Then proceed to Step 2B render with that slug.

If user wants a different one, they pass `/spec <slug>` explicitly. No list shown — keeps the output focused on the one spec they care about.

## Step 2B: Render mode (/spec <slug>)

1. Resolve path: `~/.ship/<slug>/goals/01-spec.md`. If missing:
   ```bash
   ls -d ~/.ship/*<slug>* 2>/dev/null | head -5
   ```
   If no fuzzy matches, fall back to list mode with note "slug '<slug>' not found — pick from recent:".

2. Read the spec file in full.

3. Emit a layman summary. **Hard format:**

```
# <slug>  (last edited <YYYY-MM-DD>)

**What it is:** <one sentence — what's being built or audited>

**Why it exists:** <one sentence — the problem it solves>

**What it does:**
- <plain bullet>
- <plain bullet>
- <plain bullet>
- (3-7 bullets covering the core behavior)

**Constraints / what it won't do:**
- <plain bullet>
- (1-4 bullets — the out-of-scope items, in plain language)

**Status:** <PASS / REJECT / IN PROGRESS — from §7 verdict, plain English>

**Risks worth knowing:**
- <plain bullet, only if §6 has notable items, else omit section>
```

### Translation rules (HARD — these make the output simple)

- **Strip structural jargon.** Never emit: §, EARS, SPREAD, SHRINK, premise inheritance, owning agent, strict-plan, strict-execute, citation markers `[cited ...]`, evidence ID codes (O1/F1/R1), tier labels, ACs as ID lists.
- **Translate domain jargon: rephrase as plain English, keep the original term in parens.** Every technical/domain noun gets rewritten as a verb-phrase or plain noun a non-coder understands, then the original term in parens for precision. Examples:
  - "silent edges" → "places where signals get dropped with no log entry (silent edges)"
  - "dedup loop" → "the step that filters duplicates (dedup loop)"
  - "fast loop / slow-loop" → "the 250ms scan tick (fast loop) / the 5s rebalance tick (slow loop)"
  - "trace event" → "a one-line log entry marking the drop (trace event)"
  - "1-in-100 sampling" → "logging only 1 of every 100 events (1-in-100 sampling)"
  - "risk-gate / risk engine" → "the final approval check (risk gate)"
  - "scoring-error swallow" → "a caught exception that disappears with no log (scoring-error swallow)"
  - "signal-legs" → "individual signals (signal-legs)"
  - "exit-branch lines" → "the lines that end the function early (exit branches)"
  - "head-of-file samples" → "lines from the start of each log file (head samples)"
  - Strategy names (`calibration_arb`, `time_decay`) and file names (`risk.ts`) stay as-is — they're identifiers, not jargon.
- **Sentences ≤15 words.** Active voice. No "shall". No "WHEN ... THEN" — rephrase as "if X happens, it does Y".
- **Drop scaffolding.** §0 SCOPE → "What it is" + "Why it exists". §3 ACCEPTANCE → "What it does". §4 OUT OF SCOPE → "Constraints". §6 RISKS → "Risks worth knowing". §7 VERDICT → "Status".
- **No section headers from source.** The output uses the bold labels above, not §0/§1/etc.
- **Every bullet readable cold.** A new reader with zero context understands each line — the parens give the original term back to the expert reader without blocking the layman one.
- **Concrete > abstract.** Prefer "reads files in ~/.ship/" over "consumes spec artifacts from configured root".
- **Prune ruthlessly.** If a section has no real content, omit it entirely. Better 6 strong bullets than 15 weak ones.

## Step 2C: Audit mode (/spec <slug> --audit)

After Step 2B output, check `~/.ship/<slug>/goals/01-spec-audit.md`. If exists:

1. Read it.
2. Append section:

```
**Audit verdict:** <PASS / REJECT / CONCERNS — plain English>

**Audit findings:**
- <plain bullet — what the audit caught>
- (1-5 bullets, top findings only)
```

If audit file missing: append `**Audit:** not run yet.`

## Step 3: Done

Print only the formatted summary. Do not narrate the steps. Do not paste the original spec text. Do not add commentary about the translation process.

## Failure modes

- bare /spec, no specs in ~/.ship/ → print "no ship specs found in ~/.ship/" and stop
- /spec <slug>, slug missing → list 5 closest fuzzy matches + "pick one with `/spec <slug>`"
- ~/.ship dir missing entirely → "no ship artifacts on this machine yet"
- spec file present but empty/malformed → print "spec exists but unreadable: <path>" and stop

</spec>
