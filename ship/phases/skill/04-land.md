# /ship Phase 4 LAND — SKILL route

For shipping a skill at `~/.claude/skills/<name>/`. The skeleton-skill failure mode (e.g. `/upskill` v1 — SOP steps 1-6 are stubs that echo `[stub]` and exit 0) is what this route exists to prevent.

## OUTPUT CONTRACT

Write artifact to `.ship/<slug>/04-land.md` (≤300 lines). Return summary ≤15 lines.

## Steps

### 1. Universal pre-checks (load `phases/common/realization-checks.md`)

Run RC-1 (stub markers) + RC-7 (hook-output blocklist) + RC-2 (SPEC drift between SKILL.md and references/) before any skill-specific work. ANY hit BLOCKS phase close.

### 2. Skill-tool invocation test

Invoke the skill via the Skill tool with a minimal valid argument. Capture full output.

```
Skill(skill="<name>", args="<minimal-test-input>")
```

ASSERTIONS:
- Output does NOT contain `[stub]`, `step <N>: <name>` placeholder format, `not implemented`, `skeleton`
- Output contains expected artifact references (e.g. file paths the SKILL.md claims to produce)
- Skill exits without uncaught exception

If invocation fails or returns stub-shaped output → BLOCK phase close. Verdict: `not_wired`.

### 3. SOP-step coverage

Parse SKILL.md for the declared SOP/step list (numbered list under "## Execution order" or "## SOP" headings). For each declared step N:
- Locate the implementation (script, reference doc, or inline code in SKILL.md)
- Verify it does meaningful work (not `print("[stub] step N")`)
- BLOCK if any step is a stub

Pattern check:
```bash
grep -nE '\[stub\] step|stub.*step|step.*stub|return None  # step' \
    ~/.claude/skills/<name>/SKILL.md \
    ~/.claude/skills/<name>/scripts/*.sh \
    ~/.claude/skills/<name>/references/*.md
```

Any hit = SOP-step coverage failure.

### 4. Artifact creation verification

If the SKILL.md claims to write a file (e.g. `.ship/<slug>/goals/01-spec.md`, `~/inbox/_summaries/`, etc.), invoke the skill with a test arg and ASSERT the file is actually written.

Each "writes X" claim in SKILL.md → one assertion. Missing artifact = BLOCK.

### 5. Pattern compliance (hooks-related skills only)

If the skill installs/manages hooks, verify each hook file has:
- `@bigd-hook-meta` block
- `_safe_hook` wrapper or equivalent
- Copyright header
- `_semantic_router.should_fire()` gate (if PostToolUse-shaped)

Non-compliant hooks degrade Phase 4 to NEEDS_FIX.

### 6. Verdict

- All RC-1/2/7 + steps 2-4 PASS → `wired` (close OK)
- Step 5 fails (pattern non-compliance) → `partial` (allowed close with `--ack-pattern-debt` flag + ledger entry)
- Step 2/3/4 fails → `not_wired` (BLOCK close)

## Override path

`.ship/<slug>/state/04-skill-override.md` with:
- Skill name + current verdict
- Why steps cannot pass now (e.g. "v1 ships only step 1; steps 2-7 in subsequent slices, declared in SPEC")
- Bernard ack string (auto-mode CANNOT approve)

Source: 2026-04-27 — discovered `/upskill` was marked shipped at v1 with SOP steps 1-6 as `[stub]` echoes. New SKILL route exists to refuse closure on this failure mode.

## Owning Agent

`strict-execute` for the skill build. Hands off to `strict-review` (T+24h via 05-monitor) for re-verification after deploy.

## SPREAD/SHRINK pass

Standard SPREAD/SHRINK per `phases/common/refresh.md`.

## RC-11 Discipline Detection gate (HARD — added 2026-05-02)

Same as bot/04-land.md §"RC-11 Discipline Detection gate" — runs `~/.claude/scripts/discipline-detector-runner.py` against the slice's §Discipline Impact disciplines block. Block close on FAIL/UNRUNNABLE; receipt-append gated on PASS. For SKILL slices the runner default is `--scope=full` (harness has no git) unless `--paths=<...>` is supplied.

## Reference

Inherit base phase template from `phases/bot/04-land.md` for ledger-writing protocol, override format, OUTPUT CONTRACT enforcement. Skill-specific differences are documented above.
