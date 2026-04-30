# /debug Critic mode (Group D — adversarial 3-agent review)

On-demand only. Never auto-fires. Replaces standalone `/critic` skill (retired 2026-04-30).

The verb is invoked via `python3 ~/.claude/skills/debug/bin/debug.py critic <target>`. The Python dispatcher prepares a context bundle and prints `READY: <path-to-context.json>`. This phase file then drives the 3-agent orchestration in-session — `debug.py` itself contains zero LLM calls.

---

## Iron Laws

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Plus the Critic-specific invariants:

- **Isolation invariant.** Each downstream agent sees ONLY the structured JSON output from the prior agent — never the prior agent's reasoning, scratchpad, or original brief. Reviewer's chain-of-thought is invisible to Critic. Critic's rationale is the only thing Lead sees from Critic.
- **Briefs-before-spawn invariant.** Each `agent-N-brief.md` is written to disk BEFORE the Agent() call fires. This is the falsification artifact. If a brief is missing on disk, the Phase 4 isolation grep cannot run, so the run is not closeable.
- **No-LLM-in-debug.py invariant.** The dispatcher (`bin/debug.py:cmd_critic`) writes context bundles only. All LLM calls happen inside this phase, in-session.

---

## §0 PRECONDITIONS

This phase begins after `python3 debug.py critic <target>` has been invoked successfully. You should have a `READY: <abs-path>` line in your terminal output. If not — re-run the dispatcher first.

Required state at entry:

- `<context-path>` exists and parses as JSON
- The bundle contains: `run_id`, `target`, `target_kind`, `target_files`, `lenses_active`, `lens_skips`, `quick_mode`, `lenses_doc_path`, `brief_template_path`
- `target_files` is a non-empty list
- `lenses_active` is a non-empty list

If any precondition fails: stop. Tag `[GAP — bundle malformed]` in the chat reply, do NOT continue to ledger write.

---

## §1 ORCHESTRATION — 3-step ordered

Read the context bundle once. From it derive:

```
context = json.load(<context-path>)
run_id = context["run_id"]
state_dir = ~/.ship/debug-critic-verb/state/<run_id>/
template = read(context["brief_template_path"])
lenses_doc = read(context["lenses_doc_path"])
```

The template file `_lib/critic_brief_template.md` has three sections delimited by `<!-- BEGIN <NAME>_BRIEF -->` / `<!-- END <NAME>_BRIEF -->`. Extract each section by name. Do NOT paste the whole template into any agent — extract the matching section per agent only.

### Step 1 — Reviewer agent (always runs)

1. Render `lens_list` from `lenses_doc.lenses` filtered to ids in `context["lenses_active"]`. Format each lens as one bullet:
   ```
   - <id> (<display>): <prompt_fragment>
   ```
2. Substitute the Reviewer template's `{{lens_list}}` slot with the bullets.
3. Substitute `{{target_files_json}}` with `json.dumps(context["target_files"], indent=2)`.
4. Save the fully-rendered Reviewer brief to `<state_dir>/agent-1-brief.md`. **WRITE BEFORE SPAWN — this is the falsification artifact.**
5. Spawn the Reviewer via the Agent tool:
   - `subagent_type: general-purpose`
   - `model: sonnet` (CLAUDE.md §Agent model default)
   - `prompt: <rendered Reviewer brief>`
6. The Reviewer returns a JSON array. Parse it. Save to `<state_dir>/agent-1-output.json`.
7. If Reviewer returns `[]` (no findings) AND `quick_mode == false`: still proceed to Step 2 (Critic may flag a missed concern); but tag the run as low-yield.
8. If `quick_mode == true`: skip Step 2 + Step 3, jump to §2 with the Reviewer findings as final.

### Step 2 — Critic agent (skipped in --quick)

1. Read `<state_dir>/agent-1-output.json`.
2. Substitute the Critic template's `{{reviewer_findings_json}}` slot with the Reviewer JSON.
3. **Critic brief must contain ONLY the Critic template + the JSON. NO Reviewer brief content. NO file_contents. NO lens prompt fragments.** This is the isolation invariant.
4. Save the rendered Critic brief to `<state_dir>/agent-2-brief.md` BEFORE spawn.
5. Spawn the Critic agent (general-purpose, sonnet).
6. Save returned JSON to `<state_dir>/agent-2-output.json`.

### Step 3 — Lead agent (skipped in --quick)

1. Read both `agent-1-output.json` and `agent-2-output.json`.
2. Substitute the Lead template's `{{reviewer_findings_json}}` and `{{critic_verdicts_json}}` slots.
3. **Lead brief contains ONLY the two JSON inputs. NO file_contents. NO prior agents' prose.** Isolation invariant.
4. Save to `<state_dir>/agent-3-brief.md` BEFORE spawn.
5. Spawn Lead agent (general-purpose, sonnet).
6. Save returned JSON to `<state_dir>/agent-3-output.json`.

### Checkpoint enforcement (R8 mitigation)

Before §3 ledger write, assert ONE of:

- `quick_mode == true` AND `agent-1-output.json` exists AND `agent-{2,3}-output.json` do NOT exist, OR
- `quick_mode == false` AND `agent-{1,2,3}-output.json` ALL exist.

Mismatch → refuse ledger write. Print `PREMISE_FAILURE: orchestration incomplete` and stop.

---

## §2 OUTPUT FORMAT — terminal markdown table

Render the final findings table from the latest agent output (Lead in full mode; Reviewer in quick mode). Three sections per SPEC §4.5 IA:

```
## /debug critic — <target>

run_id: <run_id>     mode: <quick|full>     ts: <utc-iso>

### Confirmed findings

| Severity | Category | Location | Finding | Fix hint |
|---|---|---|---|---|
| CRITICAL | Security | path/to/file.py:34 | <finding> | <fix-hint> |
...

### Low-confidence findings

(Disputed — not enough evidence to confirm or dismiss.)

| Severity | Category | Location | Finding | Fix hint |
...

### Dismissed findings

<details>
<summary>N dismissed findings (Critic + Lead both dismissed)</summary>

- <finding text> — <dismiss reason>
- ...

</details>
```

**Sort:** within each section, severity desc (CRITICAL → HIGH → MEDIUM → LOW), then alphabetical by Category, then by Location.

**Severity:** full word, never abbreviated.

**Category:** display name from lens (e.g. "Error handling", not "error-handling" id, not "L3").

**Location:** `file:line` exactly, or "System-level" when finding is architectural.

In quick mode, all findings land in "Confirmed findings" (no Critic/Lead to dispute). The "Low-confidence" and "Dismissed" sections render as `(none — quick mode)`.

---

## §3 LEDGER WRITE

Top-level enum verdict computed from final findings:

- `findings_present` — ≥1 finding survives in Confirmed or Low-confidence
- `clean` — Reviewer returned `[]`, OR all findings landed in Dismissed
- `inconclusive` — orchestration completed but final agent output failed to parse / had schema errors

Compute `findings_count = {critical, high, medium, low}` from the `final_verdict in {confirmed, low-confidence}` subset.

Write a sibling JSON to `~/NardoWorld/critic-findings/<R-NNNN>.json` with:

```json
{
  "entry_id": "R-NNNN",
  "run_id": "<run_id>",
  "target": "<target>",
  "target_kind": "<kind>",
  "quick_mode": <bool>,
  "verdict": "findings_present | clean | inconclusive",
  "findings_count": {"critical": N, "high": N, "medium": N, "low": N},
  "final_findings": [...],         // full final array from Lead (or Reviewer in quick)
  "agent_briefs": {
    "reviewer": "<state_dir>/agent-1-brief.md",
    "critic":   "<state_dir>/agent-2-brief.md",
    "lead":     "<state_dir>/agent-3-brief.md"
  },
  "agent_outputs": {
    "reviewer": "<state_dir>/agent-1-output.json",
    "critic":   "<state_dir>/agent-2-output.json",
    "lead":     "<state_dir>/agent-3-output.json"
  }
}
```

Then append to `~/NardoWorld/realize-debt.md` via `_disc.atomic_ledger_append()`. Body template:

```
## R-NNNN <utc-iso>  /debug critic

- target: <target>
- target_kind: <file|directory|diff|host-feature>
- mode: critic
- quick_mode: <true|false>
- verdict: <findings_present|clean|inconclusive>
- findings_count: {critical: N, high: N, medium: N, low: N}
- findings_detail: ~/NardoWorld/critic-findings/<R-NNNN>.json
- run_id: <run_id>
- source_briefs: <state_dir>/{agent-1,agent-2,agent-3}-brief.md

```

(`mkdir -p ~/NardoWorld/critic-findings/` on first run if needed.)

Schema is backward-compatible per Phase 1 R4: top-level fields are flat key:value lines. Readers that don't know `findings_detail` simply ignore it.

---

## §4 RETURN

Print the §2 markdown table to chat. Then print one summary line:

```
Ledger: <R-NNNN>  ·  verdict: <enum>  ·  findings: critical=N high=N medium=N low=N  ·  detail: <path>
```

Done.

---

## §5 ROUTE-TRACE NOTES (read for Phase 4 LAND)

The Phase 4 LAND deliverable `~/.ship/debug-critic-verb/experiments/route-trace.md` must trace at least 2 representative prompts through every router rule. The skeleton at that path lists the prompts and the router files to inspect. Do NOT close Phase 4 without filling in:

- `[cited CLAUDE.md:<line>]` for the `/debug routing` row that maps the trigger phrase to `/debug critic`
- `[cited debug/SKILL.md:<line>]` for both the Triggers block and the routing-table row
- `[cited debug.py:<line>]` for the `if verb == "critic"` dispatch case
- `[cited phases/critic.md:<line>]` for the §0 PRECONDITIONS gate

Plus the isolation falsification grep:

```bash
# Reviewer scratchpad fingerprint should NOT appear in agent-2-brief or agent-3-brief.
grep -E "(Let me|Looking at|First[, ]I'll|My first|I think|I'll start)" \
     ~/.ship/debug-critic-verb/state/<run-id>/agent-2-brief.md \
     ~/.ship/debug-critic-verb/state/<run-id>/agent-3-brief.md
# Expected: no hits. Hit = isolation broken, phase rejected.
```

---

## §6 NOTES ON ISOLATION (why this works)

The isolation mechanism is option B from Phase 1 audit Attack 2: each downstream agent is spawned with a fresh Agent() call whose brief is built from JSON, never from the prior agent's chat. The harness boundary IS the isolation — we are not relying on the orchestrator's discipline to scrub context.

Concretely:
- The Critic brief contains the Reviewer's findings JSON, but never the Reviewer's brief, never the file_contents, never any reasoning prose.
- The Lead brief contains both the Reviewer's findings JSON and the Critic's verdicts JSON, but again no prose, no file_contents.

If a future maintainer is tempted to "add the file content for context" to the Critic or Lead brief — DON'T. That breaks isolation. The Reviewer is the only agent that sees source code.

---

## §7 LENS REGISTRY POINTER

<!-- LENS_REGISTRY -->
The canonical lens taxonomy lives at `~/.claude/skills/debug/_lib/critic_lenses.json`. Edit there; the Reviewer brief regenerates from it at runtime. Daily lint should `jq -e '.lenses | length >= 8'` on this file. Do NOT duplicate the lens list in this phase document.
