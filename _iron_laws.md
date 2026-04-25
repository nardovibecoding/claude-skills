# Iron Laws (shared preamble for /ship + /debug)

Source: obra/superpowers (MIT). Verbatim quotes; both skills MUST pin these.

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```
From `obra/superpowers/skills/systematic-debugging` — applies to /debug Bug/Drift/Performance/Flaky modes AND any /ship phase that proposes a code change to address an existing failure.

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```
From `obra/superpowers/skills/verification-before-completion` — applies to /debug Step 15 VERDICT-VERIFY AND every /ship phase close.

## Enforcement

If either law is violated:
- /debug output is invalid — re-run the relevant phase before claiming a verdict
- /ship phase artifact is rejected — phase does not close until evidence cited

Pin both laws at the top of `~/.claude/skills/debug/SKILL.md` and `~/.claude/skills/ship/SKILL.md` so they appear in every invocation's context.

Cross-reference:
- `~/.claude/CLAUDE.md` Realization Check (compiles ≠ works) is the operational expression of the second law.
- `~/.claude/CLAUDE.md` Causal-claim gate is the operational expression of the first law.
