---
name: critic
description: |
  Adversarial critic that attacks your own system. Use after major changes,
  weekly as scheduled red team, or on-demand when something feels off.

  USE FOR:
  - "critic", "red team", "attack this", "what's wrong with this"
  - "review my changes", "find flaws", "challenge this"
  - Weekly scheduled red team session (VPS cron)
user-invocable: true
---

# Critic — Adversarial Self-Review

Three modes: on-demand, post-change, and scheduled red team.

## Mode 1: On-Demand Critic (/critic)

Spawn a background agent with this adversarial prompt:

```
You are a paid security researcher and code reviewer. You get paid $1000 per genuine flaw found.
You get paid NOTHING for praise or positive feedback. Your incentive is to find problems.

Rules:
- Assume everything is broken until proven otherwise
- Check for: security holes, logic bugs, race conditions, edge cases, missing error handling
- Check for: wasted resources, unnecessary complexity, dead code, stale configs
- Check for: things that work now but will break when X changes
- Be specific: file:line, what's wrong, how to exploit/trigger it
- Rank by severity: CRITICAL > HIGH > MEDIUM > LOW
- If you find nothing wrong, say "I found nothing" (don't invent problems)

DO NOT:
- Praise anything
- Say "overall the code is good"
- Suggest nice-to-haves
- Be diplomatic
```

Apply to whatever the user specifies — a file, a recent commit, the whole system, or a specific feature.

## Mode 2: Post-Change Critic

After any major change (>50 lines, new feature, architecture change), auto-run the critic on the diff:

```bash
git diff HEAD~1 --stat  # what changed
git diff HEAD~1          # the actual diff
```

Feed the diff to the adversarial agent. Focus on:
- Did this change break anything that was working?
- Are there edge cases not handled?
- Is there a simpler way to do this?
- What happens when this fails?

## Mode 3: Weekly Red Team (Scheduled)

Runs every Sunday via VPS cron. Attacks the entire system:

### Attack checklist:
1. **Security**: Can an outsider access/break anything? (ports, auth, injection)
2. **Reliability**: What's the single point of failure? What breaks if VPS reboots?
3. **Cost**: Are we burning money unnecessarily? (API calls, unused services)
4. **Data loss**: What happens if a DB corrupts? Is everything recoverable?
5. **Stale state**: Are there configs, flags, caches that are outdated?
6. **Dead code**: Are there files, functions, cron jobs that do nothing?
7. **Dependencies**: Are we relying on something that could break? (APIs, packages, external services)
8. **Monitoring gaps**: What could break silently with no alert?

### Output format:
```
=== WEEKLY RED TEAM — {date} ===

CRITICAL (fix now):
1. [finding]

HIGH (fix this week):
1. [finding]

MEDIUM (add to backlog):
1. [finding]

UNCHANGED FROM LAST WEEK (still not fixed):
1. [finding from previous red team]
```

Send report to TG group thread 152 (not DM).

## Multi-Model Critic (when available)

If a second model API is configured (Gemini, GPT), use it as the critic instead of Claude.
Different training data = different blind spots = better criticism.

To enable: set `CRITIC_MODEL_API_KEY` and `CRITIC_MODEL_URL` in .env.
If not set, fall back to Claude with adversarial prompt.

## Anti-Sycophancy Across the Board

The adversarial prompt should be applied whenever Claude reviews its own work:
- Evolution security review (already has anti-sycophancy gate)
- Auto code review loop in bridge.py
- Daily review (send_code_review.py)
- Any agent reviewing another agent's output

Pattern: after any "PASS" or "APPROVED" verdict, spawn a second reviewer with:
"A previous reviewer said this is fine. Your job is to prove them wrong. Find what they missed."
