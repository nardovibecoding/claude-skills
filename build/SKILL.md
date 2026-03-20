---
name: build
description: |
  Full lifecycle build skill — spawn agent, verify output, deploy.
  Use when user says "build X", "create X", "implement X", "make X",
  or any multi-step coding task that should be delegated to an agent.
user-invocable: true
---

# Build — Agent-based Development with Verification

Delegate coding tasks to background agents with automatic verification and deployment.

## When to Use

- User asks to build, create, implement, or make something
- Task involves writing >30 lines of code
- Task spans multiple files
- Task requires research + implementation

## Process

### Step 1: Spawn Agent

Launch a background agent with a detailed prompt including:
- Exact requirements from user
- Which files to read first
- What to build/modify
- Coding standards (existing patterns, style)
- Security considerations

### Step 2: Monitor Completion

When agent completes, check the result:
- If agent hit rate limit: read the output file, assess progress, spawn continuation agent with context
- If agent completed: proceed to verification

### Step 3: Verify Output

Run automatic checks on all changed files:

**Syntax check** (Python):
```bash
for f in $(git diff --name-only --diff-filter=AM -- '*.py'); do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>&1
done
```

**Lint check** (if ruff installed):
```bash
ruff check $(git diff --name-only --diff-filter=AM -- '*.py') 2>/dev/null
```

**Import check** — verify no broken imports:
```bash
for f in $(git diff --name-only --diff-filter=AM -- '*.py'); do
  python3 -c "import importlib.util; spec = importlib.util.spec_from_file_location('mod', '$f')" 2>&1
done
```

**Diff summary** — show what changed:
```bash
git diff --stat
```

### Step 4: Handle Failures

If syntax check fails:
1. Read the error
2. Fix it directly (don't spawn another agent for a syntax fix)
3. Re-verify

If agent hit rate limit mid-work:
1. Read the agent's output file to see what was done
2. Check git diff to see actual changes made
3. Spawn a NEW agent with: "Continue this work. Here's what was done so far: [summary]. Remaining: [what's left]"

### Step 5: Deploy

If all checks pass:
```bash
cd ~/telegram-claude-bot && git add -A && git commit -m "description" && git push origin main
ssh bernard@157.180.28.14 "cd ~/telegram-claude-bot && git pull --ff-only && sudo systemctl restart telegram-bots"
```

If skills were changed:
```bash
cd ~/.claude/skills && git add -A && git commit -m "description" && git push origin main
```

### Step 6: Report

Show user:
- What was built (1-2 lines)
- Files changed (git diff --stat)
- Verification results (all pass / failures)
- Deployment status
- "Could be even better:" recommendation

## Rate Limit Recovery

When an agent returns "You've hit your limit":
1. Do NOT give up
2. Read the agent's output file: `tail -50 /path/to/output`
3. Check what was actually written: `git diff --stat`
4. If >80% done: fix remaining issues directly
5. If <80% done: spawn continuation agent with progress summary

## Important Rules

- ALWAYS spawn agents in background (run_in_background: true)
- ALWAYS verify syntax before committing
- NEVER commit broken code
- If task is trivial (<10 lines): just do it directly, don't spawn agent
- If multiple independent subtasks: spawn multiple agents in parallel
- After completion: check if memory needs updating (new feature, architecture change, etc.)
