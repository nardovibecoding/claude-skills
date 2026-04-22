---
name: legends
description: Toggle Legend personas on/off + super-legend panel (decide/debate/red-team/audit/express/brief). Combines 41 legends into situation-routed panels with per-legend memory of Bernard.
user-invocable: true
---

# Legends — Toggle + Super-Legend Panel

Two systems on one skill:

- **Toggle** — enable/disable the 41 individual persona skills (`/legends on`, `/legends off`, `/legends build`, etc.)
- **Super-Legend Panel** — situation-routed panel of 1-5 legends for decisions, debate, red-teaming, audit (`/legends decide X`, `/legends debate X`, etc.)

---

## Part 1 — Toggle Commands (existing)

- `/legends on` — enable ALL personas
- `/legends off` — disable ALL personas
- `/legends status` — show which are enabled/disabled
- `/legends only <category>` — enable ONLY that category, disable others
- `/legends <category>` — toggle one category (build/money/hustle/contrarian/stage/politics)

### Category mapping (dirs)

- **Build** (7): `steve-jobs-perspective`, `elon-musk-perspective`, `lei-jun-perspective`, `jack-ma-perspective`, `branson-perspective`, `peter-lam-perspective`, `herjavec-perspective`
- **Money** (7): `li-ka-shing-perspective`, `masayoshi-son-perspective`, `dalio-perspective`, `buffett-perspective`, `cho-yan-chiu-perspective`, `webb-perspective`, `icahn-perspective`
- **Hustle** (9): `daliu-perspective`, `alvin-chau-perspective`, `law-siu-fai-perspective`, `richard-li-perspective`, `cecil-chao-perspective`, `albert-yeung-perspective`, `cuban-perspective`, `ricky-wong-perspective`, `edwin-lee-perspective`
- **Contrarian** (5): `chow-hin-perspective`, `muddy-waters-perspective`, `sbf-perspective`, `thiel-perspective`, `leopold-perspective`
- **Stage** (7): `dayo-wong-perspective`, `wyman-wong-perspective`, `lam-jik-perspective`, `stephen-chow-perspective`, `patrick-tse-perspective`, `natalis-chan-perspective`, `eric-tsang-perspective`
- **Politics** (4): `jiang-zemin-perspective`, `trump-perspective`, `stephen-shiu-perspective`, `miles-guo-perspective`
- **Uncategorized** (2): `munger-perspective`, `naval-perspective`

### Enable/Disable commands

```bash
# Enable:
[ -f ~/.claude/skills/$dir/SKILL.md.disabled ] && mv ~/.claude/skills/$dir/SKILL.md.disabled ~/.claude/skills/$dir/SKILL.md

# Disable:
[ -f ~/.claude/skills/$dir/SKILL.md ] && mv ~/.claude/skills/$dir/SKILL.md ~/.claude/skills/$dir/SKILL.md.disabled
```

### Status

```bash
for dir in ~/.claude/skills/*-perspective; do
  name=$(basename "$dir")
  if [ -f "$dir/SKILL.md" ]; then echo "ON  $name"
  elif [ -f "$dir/SKILL.md.disabled" ]; then echo "OFF $name"
  fi
done
```

---

## Part 2 — Super-Legend Panel (semantic routing)

**Primary UX**: `/legends <anything>` — router auto-picks mode from keywords + structure. No mode to remember.

**Power-user override** (rare): append `--decide|--debate|--red-team|--audit|--express|--brief` to force a mode.

### Semantic router rules

When `/legends <Q>` invoked (where Q ≠ toggle keyword), detect mode via priority-ordered checks:

#### Priority 1 — Explicit override
- Q contains `--decide|--debate|--red-team|--audit|--express|--brief` → use that mode

#### Priority 2 — Toggle keywords (fallthrough from Part 1 parser)
- Q starts with `on|off|status|only <category>|build|money|hustle|contrarian|stage|politics` → TOGGLE, not panel

#### Priority 3 — Brief trigger
- Q contains `refresh|brief|update|re-read perspective|legends` refresh → BRIEF mode
- `brief <legend-name>` → brief one
- `brief <project-name>` (match against graph_index.json hub nodes) → brief project legends
- `brief` alone → brief all

#### Priority 4 — Audit trigger (retrospective)
- Q contains `last time|was I right|audit|review|looking back|retrospective|lesson from|how did X go` → AUDIT mode
- Or if Q matches a recent entry in decisions.jsonl verbatim → AUDIT that entry

#### Priority 5 — Red-team trigger (destructive framing)
- Q contains `red team|what could go wrong|attack|kill|fail|bust|blow up|risks|downside|worst case|poke holes|tear apart|scary|what if I'm wrong`
- Or Q structure = "I plan to X" + any danger-signal word → RED-TEAM

#### Priority 6 — Express trigger (trivial/time-sensitive)
- Q is <10 words AND scale=micro (by profile.md thresholds)
- Q contains `quick|fast|tldr|one line|just tell me|gut check|yes or no|now|urgent|30 sec`
- Q is a yes/no structure with obvious small stakes → EXPRESS

#### Priority 7 — Debate trigger (complexity/tension)
- Q contains `debate|tension|both sides|contradictions|weigh|trade off|pros and cons|X vs Y|conflict|full picture|deep dive`
- Q presents ≥2 explicit alternatives ("A or B", "X 定 Y", "yes or no and why") AND stakes are not micro
- Horizon = decades/generations → DEBATE

#### Priority 8 — Default DECIDE
- Everything else → DECIDE mode (3-legend panel, standard)

### Emotional state overlay (always applies)

After mode chosen, scan Q for emotional state (detects Cantonese + English):
- **fear**: `scared|worried|panic|驚|怕|擔心|唔安樂|頂唔順|頭痛|lost sleep`
- **excitement**: `excited|pumped|going all in|一鋪瞓|all-in|this is it|finally|breakthrough`
- **frustration**: `pissed|frustrated|fed up|火滾|嬲|頂唔順|X's sake|WTF|ridiculous`
- **grief**: `死|died|gone|lost|loss|grief|傷心|難過|sad|mourning`

Apply emotional routing (see Part 4) — adds voices, doesn't remove.

### Ambiguity handling (soft default, not blocking)

Don't use hard priority tree alone. Rank modes by confidence:
- Top mode executes
- If top 2 within 15% → inline hint: `(interpreting as {X} — say "{Y}" to switch)`
- Only clarify-block if input is genuinely unparseable (no verb, no subject, pure fragment)

### R1 — Intent taxonomy (natural-input router)

Map phrasings to INTENTS (richer than modes):

| Intent | English triggers | 廣東話 triggers | → Mode |
|---|---|---|---|
| DECIDE-BINARY | should X, ok to X, yes or no, can I | 做唔做, 得唔得, 可唔可以 | decide |
| DECIDE-MULTI | A or B or C, pick one, which | X 定 Y, 邊個好, 揀邊個 | decide (debate if ≥3 options) |
| STRESS-TEST | risks, what could go wrong, worst case, if X fails | 黐線咩, 唔得嘅, 出事點算 | red-team |
| REFLECT-PAST | last time X, was I right, looking back | 上次點樣, 冇錯到, 返去睇 | audit |
| QUICK-CHECK | tldr, yes/no, quick, just tell me | 睇下, 等陣先, 快啲 | express |
| TEACH-ME | why, explain, how does X work | 點解, 教我, 解釋吓 | decide (bias LEARNING tag) |
| REFRESH | update X view, refresh legends | 更新, 睇返 | brief |

### R2 — Context inheritance

Before routing, read last 30 min of convo summaries from `~/.claude/projects/-Users-bernard/memory/convo_*.md`. If Q references ambiguously:
- "kill it" → subject = current project from convo context
- "OK 唔 OK" → OK to do what? inherit from last discussion
- "same thing" → replay recent panel with small variation

Pull last 3 convo_*.md files by mtime. Use their frontmatter titles + summaries as context.

### R3 — Language-aware detection

Scan Q for language mix. Each trigger library (English + 廣東話) runs in parallel. Mixed-language Q ("PM bot kill 定唔 kill") = both streams contribute to confidence score.

### R4 — HyDE on intent (for vague queries)

Q ambiguous or <6 tokens AND no clear intent match:
1. Generate hypothetical clarification: "Bernard probably means: [X]. Context: [Y]."
2. Route against the hypothetical
3. Show Bernard the inferred intent inline: `(inferred: {X} — correct me if off)`

Triggers on: `what next`, `help`, `advice`, `I'm lost`, `點算`, `唔知做乜`, any <6 token Q with no clear verb/subject anchor.

### R5 — Confidence-driven soft default

Mode probabilities sum to 1.0. Top mode fires. If split:
```
decide: 0.52
debate: 0.31  →  tied within 15%, show inline hint
red-team: 0.12
express: 0.05
```

Output: `Panel (interpreting as DECIDE — say "debate" to switch):`

### R6 — PRF on router intent

After intent match, look up matched legends' `triggers` section (from U1 chunking). If their native trigger vocab reinforces the intent match, increase confidence. If they contradict the intent, drop confidence → possibly re-route.

Example: Q = "kill PM bot?" → router picks DECIDE. Top legend = Edwin Lee. Edwin's `triggers` section mentions `蝕得出`, `走位`. Q doesn't use those but vibe matches → confidence holds.

### R7 — Feedback-tuned router weights

`~/.claude/skills/legends/router_weights.json`:
```json
{
  "version": 1,
  "intent_keywords": {
    "DECIDE-BINARY": {"should": 1.0, "ok to": 1.0, "做唔做": 1.0, ...},
    "STRESS-TEST": {"risks": 1.0, "黐線": 1.0, ...},
    ...
  },
  "context_bias": {
    "mid-decision": {"decide": +0.2},
    "post-audit": {"express": +0.15}
  }
}
```

Updated by feedback log: if Bernard corrects mode, adjust weights toward his style. After ~50 corrections, router tuned to him specifically.

### R8 — Session-state awareness

Check last panel in decisions.jsonl (≤2 hours old):
- If Q is <3 words + no new subject → treat as follow-up to previous panel (same legends, express mode)
- If Q introduces new subject but short → decide mode
- If just finished audit → express mode bias for immediate follow-ups

### Old priority 1-8 tree still applies as baseline

Priorities 1-8 (above) provide BASE confidence. R1-R8 provide MULTIPLIERS + context. Fused confidence = priority baseline × intent match × language match × context match.

### Mode token budgets

- Express: 80 tokens
- Decide: 700 tokens
- Debate: 2200 tokens
- Red-team: 1200 tokens
- Audit: 1600 tokens
- Brief (one): 600 tokens
- Brief (all): 20k (background if possible)

### Examples

| User types | Detected mode | Why |
|---|---|---|
| `/legends should I kill PM bot?` | DECIDE | baseline |
| `/legends kill PM bot?` | EXPRESS | <10 words, yes/no |
| `/legends ok to kill PM bot or pivot or pause?` | DEBATE | 3 alternatives |
| `/legends what could go wrong if I kill PM bot?` | RED-TEAM | "could go wrong" |
| `/legends was killing PM bot the right call?` | AUDIT | past tense + "right call" |
| `/legends tldr on PM bot future` | EXPRESS | "tldr" |
| `/legends refresh LKS view` | BRIEF | "refresh" |
| `/legends brief pm-bot` | BRIEF (project) | "brief" + matches project node |
| `/legends I'm scared to drop Claude Code for Codex` | DECIDE + fear overlay | "scared" triggers overlay |
| `/legends going all-in on legend system, am I mad?` | DECIDE + excitement overlay | "all-in" |

---

## Part 3 — Router Logic

When super-legend command invoked, follow this pipeline:

### Step 1 — Load context

Read in this order:
1. `~/.claude/skills/legends/profile.md` — Bernard baseline
2. `~/.claude/skills/legends/matrix.yaml` — fitness matrix
3. `~/.claude/skills/legends/cautionary.md` — failure patterns
4. `~/.claude/skills/legends/gaps.md` — coverage gaps
5. `~/.claude/skills/legends/decisions.jsonl` — last 10 entries for recent-context
6. `~/NardoWorld/meta/graph_index.json` — if question references a project (check for hub node match)

### Step 2 — Diagnose situation

Tag the question with 1-3 tags from: `BUILD EXIT PIVOT TIMING CAPITAL NARRATIVE CRISIS PEOPLE CONTENT POLITICS NEGO ETHICAL LEARNING AESTHETICS LEGACY HEALTH FAMILY`.

**Rules:**
- Max 3 tags. Rank PRIMARY (the core question) + up to 2 SECONDARY
- If >3 tags seem to apply, pick the TIGHTEST primary (what's actually being decided)
- Also derive:
  - **Scale**: micro | small-biz | corporate | civilization
  - **Horizon**: days | weeks | years | decades | generations
  - **Domain**: match to legend's `domain` field (HK-property, AI, content, etc.)
  - **Emotional state**: neutral | fear | excitement | frustration | grief (detect from question phrasing — "I'm scared", "I can't believe", "pissed off", etc.)

### Step 3 — Gap check

Compare tags against `gaps.md`. If hard gap (HEALTH/FAMILY/pure-technical/women-specific/etc.) → acknowledge gap in output, give closest approximation, recommend external expert. Do NOT fake a full panel for gap domains.

### Step 4 — Panel selection (BM25 + RRF hybrid)

Scoring uses **multi-signal RRF fusion**. Each signal independently ranks all 41 legends. Final score = RRF fusion across signals.

#### Signals

**S1 — Matrix fitness** (deterministic anchor)
From matrix.yaml + Q tags + scale/horizon/domain:
- PRIMARY tag match: +5, SECONDARY: +3, baseline: +1
- Domain match: +3, Scale match: +2, Horizon match: +2

**S2 — BM25-like on persona skill**
Q as query, each legend's `<legend>-perspective/SKILL.md*` as doc. Estimate term-frequency overlap (key domain terms, decision-pattern phrases, frame keywords). High overlap = high rank. Catches legends whose actual content matches the Q even when tags don't.

**S3 — BM25-like on perspective file**
If `perspectives/<legend>.md` exists, match Q against it. Legends who've already written about Bernard's related projects/decisions rank higher. Critical for project-specific queries.

**S4 — Graph distance**
If Q mentions a project node in `~/NardoWorld/meta/graph_index.json`, shortest-path-hop distance from project node to each legend node. 1-hop > 2-hop > 3-hop. Unlinked = lowest rank on this signal.

**S5 — Recency rotation** (inverse)
From `decisions.jsonl` last 10 entries. Legends who spoke recently rank LOWER on S5 to force diversity. Untapped legends rank higher.

**S6 — Cautionary pattern force-include** (separate track, not fused)
Detection signals in Q trigger specific legends force-included as warning voices, regardless of other signal ranks. See cautionary.md.

#### RRF fusion

For each legend L:
```
rrf_score(L) = Σ_s (w_s / (k + rank_s(L)))
k = 60 (standard RRF constant)
```

Default weights: `w1=1.0, w2=0.8, w3=1.0, w4=0.6, w5=0.4`

#### Adaptive weighting (per-query)

- Q mentions explicit project node → boost `w4` to 1.5 (graph-anchored)
- Q is domain-novel (low S1 max score across all) → boost `w2, w3` to 1.2 (content-based takes over)
- Perspectives all stale (>30 days) → drop `w3` to 0.3 (don't trust stale takes)
- Q emotionally loaded → emotion overlay in Part 4 adds specific legends regardless of RRF

#### Modifiers (applied AFTER RRF)

- `ethical_flag: true` + Q isn't ETHICAL/red-team → exclude (rrf_score = 0)
- `status: offline-deceased` → keep, flag `[offline — year of death]` in output
- `status: offline-imprisoned` → exclude unless red-team mode
- Cross-contamination diversity: max 2 legends from same framework family per panel

#### Explainability

Panel output must include a line per legend showing WHY picked:
> `LKS: S1=rank3 S2=rank7 S3=rank1 S4=rank2 S5=rank12 → rrf=0.043 [picked by S3+S4]`

Shows Bernard which signal drove the selection. If a selection looks wrong, he knows which signal to question.

### Step 4b — Recall-style upgrades (applied to panel selection)

Mirrors the recall search pipeline upgraded 2026-04-20. Six techniques layered on RRF:

#### U1 — Section chunking (S2/S3 improvement)

Each persona `SKILL.md*` treated as chunked document with named sections:
- `frame` — core philosophy / worldview
- `decision-lens` — evaluation method
- `triggers` — phrases/questions that activate this legend
- `pattern` — their decision pattern signature
- `blindspot` — explicit blindspot
- `voice` — tone markers + vocab

BM25-like matching runs against each section. Legend's S2 rank uses BEST-matching section, not file-wide average. Flag which section matched.

Same for perspective files (S3): `who-he-is`, `building-ranking`, `recent-decisions`, `standing-advice`, `pattern-watch`.

#### U2 — Cross-encoder rerank (top-10 → top-5)

After initial RRF ranks all 41, take top-10. For each:
- Pair Q with that legend's HIGHEST-matching section
- Do careful pairwise match estimation (Claude reasoning, not model call)
- Score: does this legend's specific frame actually answer THIS specific Q?

Top-5 by cross-encoder rerank = final pre-modifier panel. Avoids legends who score high on BM25 due to generic overlap but whose specific section doesn't actually match.

#### U3 — HyDE for vague queries

If Q is `≤6 tokens` or vague-structure-detected:
1. Generate a HYPOTHETICAL IDEAL answer (2-3 sentences) — what would a perfect advisor say?
2. Use that expanded text as the actual query for RRF
3. Match legends against the hypothetical, not the sparse original

Triggers on:
- `what next?`
- `I'm lost`
- `help`
- `what do?`
- `advice?`
- Any Q <6 tokens after stop-word strip

Cost: one extra reasoning pass upfront. Worth it for vague queries.

#### U4 — Pseudo-Relevance Feedback (PRF)

After first RRF pass:
1. Take top-3 ranked legend sections
2. Extract top-3 BM25 terms from those sections (STOP word filter: common English/廣東話 particles)
3. Append those terms to original Q
4. Re-run RRF with expanded query
5. Final panel from second pass

Catches domain-specific vocabulary that Bernard didn't use but legends do (e.g. Q says "cut loss" → PRF adds "蝕得出", "知止", "exit-from-pattern").

PRF runs on Decide/Debate modes. Skipped for Express (too slow) and Red-team (pattern-match dominant).

#### U5 — Weighted RRF (tunable)

Weights stored in `~/.claude/skills/legends/weights.json`:
```json
{
  "version": 1,
  "w_S1_matrix": 1.0,
  "w_S2_persona_content": 0.8,
  "w_S3_perspective": 1.0,
  "w_S4_graph_distance": 0.6,
  "w_S5_recency_rotation": 0.4,
  "mode_overrides": {
    "red-team": {"w_S1_matrix": 0.4, "cautionary_force_multiplier": 2.0},
    "audit": {"w_S5_recency_rotation": -0.5}
  }
}
```

Adaptive per Q (already in Step 4): graph-anchored Q boosts S4, domain-novel Q boosts S2/S3.

Bernard edits this file to tune panel behavior long-term.

#### U6 — Feedback log

Every panel call, decisions.jsonl entry gets feedback fields:
```json
{
  "feedback": {
    "panel_useful": null,     // user marks: true/false/partial
    "best_legend": null,      // which legend call actually helped
    "worst_legend": null,     // which was noise
    "actual_outcome": null,   // what Bernard did + what happened
    "outcome_noted_at": null
  }
}
```

After ~100 entries → run `tune_weights.py` (future) to adjust weights.json based on which signals actually predicted useful panels.

Follow-up prompt after synthesis: `→ Mark this panel useful/partial/noise?` (optional one-tap)

### Step 4c — Modifiers (applied AFTER all RRF + U1-U6)

- `ethical_flag: true` + Q isn't ETHICAL/red-team → exclude (rrf_score = 0)
- `status: offline-deceased` → keep, flag `[offline — year]` in output
- `status: offline-imprisoned` → exclude unless red-team mode
- Cross-contamination diversity: max 2 legends from same framework family per panel

**Cautionary pattern check** (from cautionary.md):
- If Q matches ≥1 pattern detection signals → FORCE-INCLUDE that pattern's legend as warning voice, regardless of fitness score
- If ≥3 detection signals = HIGH confidence; 2 = MEDIUM; 1 = LOW (flagged as possible false positive per B7)
- If multiple patterns trigger, include all, rank by severity: P2 P5 > P1 P13 P14 > P6 P9 P10 P11 P12

**Emotional state routing (G3, balanced):**
- `fear` → ADD 叻哥 (natalis-chan, luck reset) + Dayo Wong (name the pain). Keep rational voices.
- `excitement` → ADD 1 cautionary voice (Munger inversion or LKS 知止). Keep optimists.
- `frustration` → ADD Albert Yeung (爭氣 framing). Keep analytical voices.
- `grief` → ADD 林夕 (impermanence). Reduce panel to 2-3 voices, compassion tone.
- `neutral` → no emotional modifier

**Devil's advocate (C7 fix):**
- After top-5 selected, check: do ≥3 of 5 share the same direction? If yes → swap lowest-fit member for highest-fit legend whose frame OPPOSES the majority lean.

**Cross-contamination diversity (E3 fix):**
- Avoid stacking legends with same lineage root. E.g. don't pick Buffett + Munger + Naval together — they share value-investing + latticework DNA. Pick max 2 from same framework family.

### Step 5 — Final panel

- Express mode: 1 legend
- Decide mode: 3 legends
- Debate mode: 5 legends
- Red-team mode: cautionary-only, 2-4 legends
- Audit mode: 3 legends who weighed in on the original decision (from decisions.jsonl)

---

## Part 4 — Panel Output Rules

### Language + tone (critical)

**Each legend speaks in their native language, in their actual tone.** No translation.

| Cantonese 廣東話 | LKS, 大劉, Wyman, 林夕 (bilingual), Stephen Chow, Dayo Wong, 四哥 Patrick Tse, Eric Tsang, 叻哥 Natalis Chan, Albert Yeung, Ricky Wong, Edwin Lee, 蕭若元, Cecil Chao (bilingual), 曹仁超, 羅兆輝, 周顯 |
| Mandarin 普通話 | Lei Jun, Jack Ma (bilingual), Jiang Zemin (polyglot), Miles Guo |
| English | Jobs, Musk, Buffett, Munger, Dalio, Naval, Thiel, Leopold, Webb, Icahn, Branson, SBF, Cuban, Herjavec, Trump, Muddy Waters, Masa Son (bilingual) |
| Japanese 日本語 | Masa Son (bilingual with English) |

**Mixed panel = multilingual output. Untranslated.**

### Legend voice sourcing

When summoning a legend, READ their persona skill file directly (regardless of enabled/disabled state):
- Active: `~/.claude/skills/<legend>-perspective/SKILL.md`
- Disabled: `~/.claude/skills/<legend>-perspective/SKILL.md.disabled`

Read full file — especially triggers, tone markers, decision patterns. Imitate voice, don't paraphrase generically.

Also READ their perspective file if it exists:
- `~/.claude/skills/legends/perspectives/<legend>.md`

Perspective file = this legend's current view of Bernard. Use it. If file doesn't exist yet, flag `[perspective not yet briefed — run /legends brief <legend>]` at end of their entry.

### Blindspot disclosure (G4)

At end of each legend's turn, add one line:
> *Blindspot on this Q: [specific blindspot from persona skill, with 0-100% applicability estimate]*

Example:
> *Blindspot on this Q: LKS's 知止 can exit generational opportunities too early — 40% applicable here since question is about long-arc IP asset.*

### Cross-legend pattern spotting (G7)

Any panel legend may flag a cautionary pattern they see in Bernard's move, even if pattern isn't in their fitness domain. This is a "free move" — they speak one extra line:
> *Free move: I see you running P9 (comfort zone masquerading as circle). Not my tag but worth saying.*

### Output structure per mode

#### Express mode
```
[legend name] ({language}): "{one-line call in native voice}"
```

#### Decide mode
```
SITUATION: [tags] | scale: [X] | horizon: [X] | domain: [X] | emotion: [X]
PANEL: [3 legends + 1-line why-picked]

─ [Legend A] ({language}):
  {their frame, their call — 3-5 lines in native voice}
  *Blindspot: {X}% applicable*

─ [Legend B] ({language}):
  {...}

─ [Legend C] ({language}):
  {...}

CONVERGENCE: {where they agree}
CONTRADICTION: {where they split — name it, don't hide}
CAUTIONARY (if triggered): [Pattern P#] — {HIGH|MEDIUM|LOW} confidence

─ GENIE SYNTHESIS (Bernard voice, 廣東話+English, caveman):
{1-3 sentence lean with reasoning. Acknowledge split. Name the call.}

DECISION PROMPT: {the question you must answer to resolve this}
```

#### Debate mode
Same as Decide but panel=5, fuller legend turns (6-10 lines each), explicit cross-references ("X rejects Y's premise because...").

#### Red-team mode
```
SITUATION: [tags] | your move: [restate]

─ [Cautionary Legend A] ({language}):
  This is how your move kills you: {specific failure mechanism}
  Detection signals I see: {which ones fired}

─ [Cautionary Legend B]:
  {...}

STACKED PATTERNS (if >1): [P#, P#] — severity ranked
SYNTHESIS: {Bernard voice} — what needs to change, or why the concern is false positive
```

#### Audit mode
```
PAST DECISION: {from decisions.jsonl}
ORIGINAL PANEL: {who spoke}
OUTCOME: {if logged} OR {ask user what happened}

─ [Each original legend]: retrospective — was I right? what did I miss?

LESSON: {pattern update for future — goes to cautionary.md if new}
```

### Token caps (hard limits per mode)

- Express: 80 tokens max
- Decide: 700 tokens max
- Debate: 2200 tokens max
- Red-team: 1200 tokens max
- Audit: 1600 tokens max
- Brief (one legend): 600 tokens max
- Brief (all): 20000 tokens (runs as background task if possible)

---

## Part 5 — Bug-fix Rules (all 12)

- **B1 Tag collision**: cap at 3 tags; force primary rank; if >3 apply, pick tightest
- **B2 Matrix scoring is subjective**: matrix.yaml is editable; user can override. Flag when a panel call relied heavily on matrix weight vs tag match.
- **B3 Legend evolution**: use `era_snapshot` field to pick which version answers. Never mix eras.
- **B4 Dead legends**: flag `[offline — historical advice, {year of death}]` in output
- **B5 False contradiction**: in synthesis step, ask "is this contradiction or same person different moment?" — if the latter, note it as "phase choice, not split"
- **B6 Diagnosis circularity**: after panel selected, self-check — "why not legend X who's also strong on this tag?" Document 1 excluded legend per panel with reason.
- **B7 Cautionary false positive**: confidence levels (HIGH/MEDIUM/LOW); LOW flagged as possible false positive; user can dismiss.
- **B8 Profile over-bias**: if panel skews ≥4/5 HK, force-include 1 non-HK legend from top-10 fitness.
- **B9 Token weight**: enforce caps per mode. If would exceed, shorten each legend's turn proportionally, not truncate last one.
- **B10 Namespace collision**: toggle = `/legends on|off|status|only|<category>`; super-legend = `/legends decide|debate|red-team|audit|express|brief`. Parse first arg: if it's a toggle keyword, toggle; else super-legend with rest as Q.
- **B11 Stateless**: decisions.jsonl IS the memory. Include summary of last 3 relevant entries in every panel call.
- **B12 No-coverage fallback**: if gap detected, don't force panel; respond with "outside legend coverage" + closest approximation + external expert recommendation.

---

## Part 6 — Edge-case Rules (all 10)

- **C1 Q about a legend**: route to that legend + 2 peers who know them (cross-reference tree). Example: "what would Buffett say about Musk?" → Buffett + Munger + Naval.
- **C2 Circular meta**: refuse "trust genie's last answer?" — respond "fresh frame please, or `/legends audit` the specific past call"
- **C3 Legend vs self**: era_snapshot picks the version. Note which era. Never merge.
- **C4 Stacked cautionary**: list all patterns, severity-rank, give composite warning
- **C5 Predator with useful insight**: include only as "frame insight" with visible `ethical_flag`. Never as trusted voice.
- **C6 Already in failure pattern**: detection via profile.md "Known patterns" + decisions.jsonl history. If detected, route to Edwin Lee (exit-from-pattern) + the legend whose frame you broke.
- **C7 Bias confirmation**: devil's-advocate slot (see Panel Selection)
- **C8 Implicit Q**: if Q has no clear tag, ask 1 clarifying question before panel. Don't guess.
- **C9 Trivial bet**: if scale=micro and horizon=days/weeks, force express mode even if user asked for decide/debate. Note override.
- **C10 Time-sensitive**: user can append `--fast` for forced express mode regardless of scale.

---

## Part 7 — Additional Edge Cases (all 10)

- **E1 Unethical Q**: predator legends (ethical_flag) excluded by default. If user explicitly requests red-team, include with flag visible.
- **E2 Wrong Q entirely**: if Q frame seems broken, genie redirects FIRST: "closer Q might be {Y} — proceed with {Y} or confirm {original}?"
- **E3 Cross-contamination**: max 2 legends from same framework family per panel (Buffett+Munger ok; +Naval = too much value-investing DNA)
- **E4 Language mix**: panel output is multilingual, untranslated. Genie synthesis in Bernard style (caveman 廣東話+English)
- **E5 You ARE the pattern**: profile.md "Known patterns" + decisions.jsonl cross-check. If Bernard is running a pattern, genie names it: "you're 70% into Stephen Chow perfectionist-isolation arc"
- **E6 Novel domain breaks all frames**: e.g. pure AI ethics. Use gaps.md fallback + note "half panel doesn't compute on AI-native Q"
- **E7 Meta recursion**: refuse genie-about-genie, suggest direct thinking
- **E8 Disagree with synthesis**: genie holds position + invites re-pose. No sycophancy.
- **E9 Audit log stale**: any decision >6 months old flagged "stale — Bernard may have evolved"
- **E10 Cautionary library rot**: version field in cautionary.md; review quarterly; new patterns added via `/legends audit` finding novel failure modes

---

## Part 8 — Memory System (v2)

### Perspective files

Each legend has `~/.claude/skills/legends/perspectives/<legend>.md` — their evolving view of Bernard (see `perspectives/_template.md`).

### When perspectives refresh

1. **Manual**: `/legends brief` (all) or `/legends brief <legend>` or `/legends brief <project>`
2. **Auto-trigger** (future hooks — see settings.json):
   - After `/s` save with major decision
   - After decisions.jsonl append
   - After hub node in graph_index.json updates
3. **Staleness flag**: perspective file with `last_refresh` >30 days → flagged stale in panel output

### Brief command pipeline

When `/legends brief <target>` runs:

1. Load: profile.md + graph_index.json + hub_nodes.json + decisions.jsonl + recent convo summaries from `~/.claude/projects/-Users-bernard/memory/convo_*.md`
2. For each target legend:
   - Read their persona skill file (voice)
   - Read matrix.yaml row (metadata)
   - Filter all context through their lens
   - Write to `perspectives/<legend>.md` using `_template.md` structure
   - Write in their native language + tone
3. Update `perspectives/<legend>.md` metadata: `last_refresh: {today}`

### Graph integration (v3)

Legend nodes live in `~/NardoWorld/meta/graph_index.json`:
```json
"legends/li-ka-shing": {
  "title": "李嘉誠",
  "category": "legends",
  "links_to": ["projects/nardoworld.md", "projects/pm-bot.md"],
  "linked_from": []
}
```

Edges = "has take on this project." When Bernard mentions a project in convo, genie can query graph for legends with edges to that project → auto-suggest panel members or auto-load their perspectives.

### Graph update

`/legends brief <project>` also updates graph edges: if panel for "PM bot" included LKS + Edwin Lee, both get edges to `projects/pm-bot.md` in graph_index.json.

---

## Part 9 — Decision Logging

Every super-legend panel call appends to `~/.claude/skills/legends/decisions.jsonl`:

```json
{
  "ts": "2026-04-20T14:30:00+08:00",
  "mode": "decide",
  "question": "should I kill PM bot after 14 days low traffic?",
  "tags": {"primary": "EXIT", "secondary": ["TIMING"]},
  "scale": "small-biz",
  "horizon": "weeks",
  "domain": "telegram-bot",
  "emotion": "frustration",
  "panel": ["edwin-lee", "li-ka-shing", "ricky-wong"],
  "cautionary_fired": [],
  "synthesis": "lean EXIT, but test once more with [specific change]",
  "bernard_chose": null,
  "outcome_noted_at": null,
  "outcome": null
}
```

### Later audit

`/legends audit <Q>` finds that entry, asks Bernard what he chose + outcome, updates entry. Over time, decisions.jsonl becomes training data — which legends' advice historically worked for Bernard.

---

## Part 10 — Invocation Pipeline (step-by-step, executable)

When user types `/legends <subcommand> <args>`:

```
1. Parse subcommand:
   - on|off|status|only|build|money|hustle|contrarian|stage|politics → TOGGLE flow
   - decide|debate|red-team|audit|express|brief → PANEL flow
   - else → error + usage

2. TOGGLE flow: use existing enable/disable bash commands from Part 1

3. PANEL flow:
   a. Load profile.md, matrix.yaml, cautionary.md, gaps.md
   b. Load last 10 decisions.jsonl entries
   c. If Q mentions a project name, also load graph_index.json + hub_nodes.json, find linked legends
   d. Diagnose tags (max 3, primary + secondary)
   e. Gap check — if hard gap, go to fallback response
   f. Score all 41 legends via fitness formula
   g. Apply modifiers (ethical_flag, status, recency, cautionary force-include)
   h. Apply emotional routing
   i. Apply cross-contamination diversity cap
   j. Apply devil's advocate swap
   k. Pick top N (1/3/5 by mode)
   l. For each selected: read persona SKILL.md* + perspectives/<legend>.md (if exists)
   m. Generate panel output per mode format, language rules, blindspot disclosure
   n. Genie synthesis in Bernard voice (caveman, 廣東話+English)
   o. Append to decisions.jsonl
   p. Return

4. BRIEF flow: run brief pipeline per Part 8
```

---

## Part 11 — Auto-hooks (v3 integration, future)

To be configured via `update-config` skill:

- **PostToolUse on Write/Edit of `decisions.jsonl`**: trigger `/legends brief <affected legends>` in background
- **UserPromptSubmit detecting cautionary pattern signals in Bernard's normal convo**: surface warning from relevant legend ("that sounds like borrowed-leverage P1 — LKS says...")
- **Stop hook after major conversation**: if decision was made, offer `/legends audit` on it

Document in settings.json. Install via `/update-config`.

---

## Part 12 — Missing Legends (v3 adds)

Flagged gaps to fill:
- At least 1 woman leader (Jensen Huang's Lisa Su, Ginni Rometty, 董明珠 Gree, Anne Wojcicki, etc.)
- Engineer-craftsman (Linus Torvalds, Jeff Dean, Carmack)
- Scientist-researcher (Demis Hassabis, Karikó, Svante Pääbo)
- Military strategist (contemporary; Sun Tzu via text if no modern)
- Athlete (Kobe/MJ/Kipchoge — discipline + peak)
- Spiritual teacher (Thich Nhat Hanh via texts, Pema Chödrön)
- Novelist/storyteller (Murakami, Ted Chiang)

Add via: new `<name>-perspective/` skill + entry in matrix.yaml + category update in Part 1.

---

## Version

- v1 2026-04-20 — base toggle + super-legend router + cautionary + profile + gaps + decisions log + perspectives template + graph integration stubs + memory system spec
- Review: quarterly
- Editable: matrix.yaml, cautionary.md, profile.md, gaps.md

---

## Quick reference

| Command | Effect |
|---|---|
| `/legends on/off/<cat>` | Toggle persona skills |
| `/legends status` | Show toggle state |
| `/legends decide <Q>` | 3-legend panel, one call |
| `/legends debate <Q>` | 5-legend panel, contradictions surfaced |
| `/legends red-team <Q>` | Cautionary legends vs your move |
| `/legends audit <Q>` | Past-decision review |
| `/legends express <Q>` | 1 legend, 1 line |
| `/legends brief` | Refresh all perspectives |
| `/legends brief <legend>` | Refresh one |
| `/legends brief <project>` | Refresh project-linked legends |
