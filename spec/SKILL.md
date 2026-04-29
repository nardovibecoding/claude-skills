---
name: spec
description: Render a ship-audit spec in plain English. Bare /spec lists recent ship slugs; /spec <slug> shows that slug's spec as 6-15 layman bullets; /spec <slug> --audit appends audit verdict. Triggers - /spec, "show me the spec for X", "what's the spec for X", "spec summary X".
user-invocable: true
---

<spec>
Render a Phase 1 ship spec in plain English bullets. No jargon, no codes, no scaffolding.

## Step 1: Resolve target

Parse args. Three modes:
- bare `/spec` → list mode
- `/spec <slug>` → render mode
- `/spec <slug> --audit` → render + audit mode

## Step 2A: List mode (bare /spec)

```bash
ls -t ~/.ship/*/goals/01-spec.md 2>/dev/null | head -10 | while read f; do
  slug=$(echo "$f" | sed -E 's|.*/\.ship/([^/]+)/goals/01-spec\.md|\1|')
  scope=$(awk '/^## §0/{flag=1; next} /^## /{flag=0} flag && NF' "$f" | head -2 | tr '\n' ' ' | cut -c1-100)
  mtime=$(stat -f '%Sm' -t '%Y-%m-%d' "$f")
  echo "$mtime  $slug — $scope"
done
```

Output as bullet list. Tell user: "Pick one with `/spec <slug>`."

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

- **Strip jargon.** Never emit: §, EARS, SPREAD, SHRINK, premise inheritance, owning agent, strict-plan, strict-execute, citation markers `[cited ...]`, evidence ID codes (O1/F1/R1), tier labels, ACs as ID lists.
- **Translate technical terms.** "user-invocable skill" → "slash command", "frontmatter" → "metadata header", "EARS criteria" → omit (rephrase as plain bullets), "premise" → "assumption".
- **Sentences ≤15 words.** Active voice. No "shall". No "WHEN ... THEN" — rephrase as "if X happens, it does Y".
- **Drop scaffolding.** §0 SCOPE → "What it is" + "Why it exists". §3 ACCEPTANCE → "What it does". §4 OUT OF SCOPE → "Constraints". §6 RISKS → "Risks worth knowing". §7 VERDICT → "Status".
- **No section headers from source.** The output uses the bold labels above, not §0/§1/etc.
- **Every bullet readable cold.** A new reader with zero context understands each line.
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

- spec file missing → list 5 closest fuzzy matches + "pick one with `/spec <slug>`"
- ~/.ship dir missing → "no ship artifacts on this machine yet"
- spec file present but empty/malformed → print "spec exists but unreadable: <path>" and stop

</spec>
