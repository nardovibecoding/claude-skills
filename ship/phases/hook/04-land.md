# /ship Phase 4 LAND — HOOK route

For shipping a hook at `~/.claude/hooks/<name>.py` (or `.js`, `.sh`). The "hook file exists but isn't actually wired" failure mode is what this route exists to prevent.

## OUTPUT CONTRACT

Write artifact to `.ship/<slug>/04-land.md` (≤200 lines). Return summary ≤15 lines.

## Steps

### 1. Universal pre-checks (load `phases/common/realization-checks.md`)

Run RC-1 (stub markers) + RC-7 (hook-output blocklist) + RC-4 (sync-hook allowlist if applicable) before hook-specific work.

### 2. settings.json wiring check

Verify the hook is registered in `~/.claude/settings.json` (or project's `.claude/settings.json` for project-scoped hooks):

```bash
HOOK_NAME=<name>
python3 -c "
import json, sys
s = json.load(open('$HOME/.claude/settings.json'))
hooks = s.get('hooks', {})
found = False
for event, entries in hooks.items():
    for e in entries:
        for h in e.get('hooks', []):
            if '$HOOK_NAME' in h.get('command', ''):
                print(f'WIRED: {event} -> {h[\"command\"]}')
                found = True
sys.exit(0 if found else 1)
"
```

If not wired → BLOCK with verdict `not_wired`. The hook file existing on disk is NOT proof of wiring.

### 3. Test-event firing

Trigger an event the hook claims to handle. For PreToolUse hooks, simulate via the hook's expected stdin format:

```bash
# Example for a PreToolUse: Bash hook
echo '{"tool_name":"Bash","tool_input":{"command":"echo test"},"prompt":""}' | \
    python3 ~/.claude/hooks/<name>.py
```

ASSERT:
- Hook exits 0 (or expected non-zero with explicit message)
- Hook produces expected output shape (block / allow / pass-through)
- Hook does NOT crash, hang, or write outside its declared paths

### 4. Pattern compliance (per `~/.claude/rules/agents.md` hook section)

Required pattern for new hooks:
- `@bigd-hook-meta` block at top (name, fires_on, relevant_intents, irrelevant_intents, cost_score, always_fire)
- Copyright header
- Imports `hook_base` shared lib (when applicable)
- Wrapped via `_safe_hook` decorator OR uses `run_hook(check, action, name)`
- Gated by `_semantic_router.should_fire()` for PostToolUse hooks (cost discipline)

Non-compliant hooks degrade Phase 4 to NEEDS_FIX.

### 5. Hook-chain order check (if PreToolUse)

When adding a PreToolUse hook, verify the existing chain order isn't broken. Other hooks may depend on order (e.g. `guard_safety` must fire before `auto_test_after_edit`).

```bash
# List PreToolUse hooks in firing order
python3 -c "
import json
s = json.load(open('$HOME/.claude/settings.json'))
for entry in s['hooks'].get('PreToolUse', []):
    for h in entry.get('hooks', []):
        print(h['command'])
"
```

Compare against expected order from `~/.claude/rules/<scope>.md`. WARN on mismatch.

### 6. Verdict

- Steps 1-3 PASS + step 4 compliant → `wired`
- Step 4 non-compliant only → `partial` (close OK with `--ack-pattern-debt`)
- Step 1, 2, or 3 fails → `not_wired` (BLOCK)

## Override path

`.ship/<slug>/state/04-hook-override.md` with reason + Bernard ack.

## Owning Agent

`strict-execute` writes; `strict-review` re-verifies at T+24h.

## SPREAD/SHRINK

Standard per `phases/common/refresh.md`.

## Reference

Inherit base ledger-writing protocol from `phases/bot/04-land.md`. Hook-specific differences above.
