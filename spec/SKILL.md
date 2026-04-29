---
name: spec
description: Render any ship artifact (spec, audit, plan, execution log, land report, monitor, refresh sweep) in plain English bullets. Bare /spec shows the most-recent artifact. /spec <slug> targets a specific run. /spec <slug> --phase=<name> picks a phase. Triggers - /spec, "show me the spec", "show me the audit", "what's the plan", "render the report", "spec summary".
user-invocable: true
---

<spec>
Render any ship-pipeline artifact in plain English bullets. No jargon, no codes, no scaffolding.

Supported artifact types (in order of phase progression):

| key | path glob | what it is |
|---|---|---|
| spec | `~/.ship/<slug>/goals/01-spec.md` | Phase 1 — what's being built/audited and why |
| audit | `~/.ship/<slug>/goals/01-spec-audit.md` OR `~/.ship/<slug>/audit.md` (legacy flat) | adversarial audit verdict + findings |
| plan | `~/.ship/<slug>/goals/02-plan.md` | Phase 2 — architecture + slice plan |
| exec | `~/.ship/<slug>/experiments/03-execution-log.md` | Phase 3 — what got coded, per slice |
| land | `~/.ship/<slug>/state/04-land.md` | Phase 4 — deploy + verify report |
| monitor | `~/.ship/<slug>/reports/05-monitor.md` | Phase 5 — post-deploy watch findings |
| refresh | `~/.ship/_refresh_*.md` | sweep report across many slugs |

## Step 1: Resolve target

Parse args:
- bare `/spec` → most-recent artifact across all slugs (any phase)
- `/spec <slug>` → most-recent artifact for that slug
- `/spec <slug> --phase=<key>` → that specific phase (key from table above)
- `/spec <slug> --audit` → spec + audit appended (legacy convenience flag)
- `/spec --refresh` → most-recent `_refresh_*.md` sweep report
- `/spec <slug> --all` → render every existing phase artifact for that slug, in phase order, each layman-summarized

## Step 2A: Bare mode → most-recent ARTIFACT (any phase)

```bash
LATEST=$(ls -t ~/.ship/*/goals/01-spec.md \
            ~/.ship/*/goals/01-spec-audit.md \
            ~/.ship/*/goals/02-plan.md \
            ~/.ship/*/experiments/03-execution-log.md \
            ~/.ship/*/state/04-land.md \
            ~/.ship/*/reports/05-monitor.md \
            ~/.ship/*/audit.md \
            2>/dev/null | head -1)
[ -z "$LATEST" ] && { echo "no ship artifacts found in ~/.ship/"; exit 0; }
SLUG=$(echo "$LATEST" | sed -E 's|.*/\.ship/([^/]+)/.*|\1|; s|.*/\.ship/([^/]+)\.md|\1|')
echo "Latest: $SLUG ($(basename "$LATEST"))"
```

Then render that artifact via Step 2B with phase auto-detected from path.

## Step 2B: Render mode

1. **Resolve artifact path.** If `--phase=<key>` given, use that key's glob. Else for `<slug>` alone: pick the most-recent artifact among all phases for that slug (same `ls -t` over the 7 paths, scoped to `~/.ship/<slug>/`).

2. **Slug fuzzy match.** If `~/.ship/<slug>/` missing:
   ```bash
   ls -d ~/.ship/*<slug>* 2>/dev/null | head -5
   ```
   Empty → fall back to "slug not found — pick from recent" with most-recent 5 slugs.

3. **Read the artifact in full.**

4. **Detect artifact type from path** (spec/audit/plan/exec/land/monitor/refresh).

5. **Emit a layman summary using the matching template below.** All templates obey the same translation rules (next section).

### Templates per artifact type

**spec** (Phase 1):
```
# <slug>  (spec, last edited <YYYY-MM-DD>)
**What it is:** <one sentence>
**Why it exists:** <one sentence>
**What it does:** 3-7 bullets translating §2/§3
**Constraints:** 1-4 bullets from §4 OUT OF SCOPE
**Status:** PASS / REJECT / IN PROGRESS (from §7)
**Risks worth knowing:** 1-3 bullets from §6 (omit section if empty)
```

**audit** (Phase 1 adversarial OR legacy flat audit.md):
```
# <slug>  (audit, last edited <YYYY-MM-DD>)
**Verdict:** PASS / REJECT / TUNE / REBUILD_V2 / KILL / KEEP_AS_IS / CONCERNS (plain English)
**What this audit covered:** one sentence
**Top findings:** 3-5 bullets — what the audit caught, in plain language
**Recommended action:** one sentence (e.g. "tune the X regex", "rewrite Y from scratch", "leave alone")
**Iron laws check:** one bullet on root-cause + verification status (omit if not present in source)
```

**plan** (Phase 2):
```
# <slug>  (plan, last edited <YYYY-MM-DD>)
**Goal:** one sentence — what gets built
**Architecture:** 2-4 bullets — the major pieces and how they fit
**Slices:** numbered list of slices with one-line goal each (e.g. "S1: wire the trigger", "S2: add the gate")
**Order + dependencies:** 1-2 bullets — what blocks what
**Risks:** 1-3 bullets (omit if empty)
```

**exec** (Phase 3 execution log):
```
# <slug>  (execution log, last edited <YYYY-MM-DD>)
**Slices done:** numbered list — each with what was changed and where
**Files touched:** flat list of paths
**Verification proof:** 1-3 bullets — what evidence shows it works (logs, output, test pass)
**Open issues found mid-execute:** 0-3 bullets (omit section if none)
```

**land** (Phase 4):
```
# <slug>  (land report, last edited <YYYY-MM-DD>)
**Status:** SHIPPED / FAILED / PARTIAL
**What landed:** 2-5 bullets — the visible outcome
**Realization check:** 1-4 bullets — build pass, registered, feature visible, route-trace
**Files in production:** flat list
**Remaining work:** 0-3 bullets (omit if none)
```

**monitor** (Phase 5):
```
# <slug>  (monitor report, last edited <YYYY-MM-DD>)
**Re-verify outcome:** STILL HOLDS / DRIFTED / BROKEN
**What changed since deploy:** 1-3 bullets
**Lessons captured:** 1-3 bullets in plain English (no jargon)
**Next action:** one sentence — close the loop or re-open
```

**refresh** (sweep report):
```
# refresh sweep <YYYY-MM-DD>
**Coverage:** N artifacts reviewed
**Tally:** LANDED=N, PARTIAL=N, OPEN=N, DELETED=N (plain English summary)
**Top open priorities:** 3-5 bullets — slug + 1-line reason
**Recommended next step:** one sentence
```

### Translation rules (HARD — apply to ALL templates)

- **Strip structural jargon.** Never emit: §, EARS, SPREAD, SHRINK, premise inheritance, owning agent, strict-plan, strict-execute, citation markers `[cited ...]`, evidence ID codes (O1/F1/R1), tier labels, AC ID lists, phase numbers.
- **Translate domain jargon: plain English first, original term in parens.** Examples:
  - "silent edges" → "places where signals get dropped (silent edges)"
  - "dedup loop" → "the step that filters duplicates (dedup loop)"
  - "fast loop / slow-loop" → "the 250ms scan tick (fast loop) / the 5s rebalance tick (slow loop)"
  - "trace event" → "a one-line log entry marking the drop (trace event)"
  - "1-in-100 sampling" → "logging only 1 of every 100 events (1-in-100 sampling)"
  - "risk-gate / risk engine" → "the final approval check (risk gate)"
  - "scoring-error swallow" → "a caught exception that disappears with no log"
  - "signal-legs" → "individual signals (signal-legs)"
  - "exit-branch lines" → "lines that end the function early (exit branches)"
  - "head-of-file samples" → "lines from the start of each log file (head samples)"
  - Strategy/file/identifier names (`calibration_arb`, `risk.ts`, `pm-london`) stay as-is.
- **Sentences ≤15 words.** Active voice. No "shall". No "WHEN ... THEN" — rephrase as "if X then Y".
- **Drop scaffolding.** Source section codes (§0/§1/§2.5) never appear in output; map them to the bold template labels.
- **Every bullet readable cold.** A new reader with zero context understands each line.
- **Prune ruthlessly.** Empty section = omit entirely. Better 4 strong bullets than 12 weak ones.

## Step 2C: Combo flags

- **--audit** (works with spec): emit spec template, then append audit template body (skip duplicate slug header).
- **--all**: render every existing artifact for the slug in phase order (spec → audit → plan → exec → land → monitor), each with its own template. Add a `---` divider between phases.

## Step 3: Done

Print only the formatted summary. Do not narrate the steps. Do not paste the original artifact text. Do not add commentary about the translation process.

## Failure modes

- bare /spec, no artifacts → "no ship artifacts found in ~/.ship/" and stop
- slug missing → list 5 closest fuzzy matches with note "slug not found — pick one"
- phase requested but file missing → "no <phase> artifact for <slug> yet (slug has: <list of phases that DO exist>)"
- artifact file empty/malformed → "<phase> file exists but unreadable: <path>" and stop

</spec>
