# Observations log — common template

## When to use

Any time the main assistant (or a subagent) wants to cite a live observation as evidence during a debug thread — top/ps output, strace snapshot, journalctl tail, "bot just wedged", "it's stable now", "this restart broke it" — the observation lands here FIRST, before any causal claim in chat.

An observation not logged here cannot be cited in a `§3 Verdict` (strict-plan) or `§1.5 Causal Chain Link` (strict-execute). Enforced by phase owning-agents.

## File location

`.ship/<slug>/experiments/observations.md` — append-only. Do not edit past entries; new entries only.

## Entry template

Every entry is one block. Fill all fields; `unknown` is an allowed value but forces the observation's isolation label to `[single-point]`.

```
### <YYYY-MM-DD HH:MM ZZZ> — <short-name>

observer:       main-assistant | strict-plan | strict-execute | strict-review | strict-explore | human
trigger:        <what prompted capturing this observation — user asked, scheduled check, alarm, crash>

state snapshot:
  host:         <hostname>
  service:      <systemd unit>
  git SHA:      <7-char SHA from `ssh <host> "cd <cwd> && git rev-parse --short HEAD"`>
  config hash:  <md5 of relevant config file + path>
  elapsed:      <process ELAPSED from ps / systemctl ActiveEnterTimestamp>
  key data-file sizes: <path: size + mtime>
  relevant flags: <flag1=val, flag2=val>

raw output:     <paste verbatim, truncate >30 lines with [... N lines omitted]>

variables changed since last observation (same thread):
  - <variable>: <prior value> → <new value>   [claimed / incidental / unknown]
  or: "first observation — no prior baseline"

isolation label:  [single-point] | [N-comparison, N=<n>] | [isolation-verified]
  - [single-point]       = one snapshot, cannot support causal claims
  - [N-comparison]       = ≥2 snapshots with different claimed variables
  - [isolation-verified] = N-comparison where only the claimed variable differs, others cited

permitted claims from this entry:
  - describes <observed behavior>
  - correlates with <other logged observation if applicable>
  NOT permitted: "X caused Y", "X is falsified", "rules out Z" unless isolation-verified

downgrades applied:
  - <claim I originally wanted to make> → <weaker honest phrasing>
  example: "wedge reproduces at flag=false → flag is innocent"
           → "wedge observed at flag=false on one 15-min boot; consistent with flag-insensitive wedge, not isolated from Fix #6–#10 + signal-trace size + WS-MOA path"
```

## Rules

1. One entry per observation capture. Do not batch.
2. Timestamps from the observing host's clock, not chat time.
3. If `git SHA` or `elapsed` is genuinely unavailable (e.g. remote host unreachable), write `unknown` and auto-downgrade to `[single-point]`.
4. "variables changed" = diff against the LAST entry in this file. If no prior entry, state "first observation".
5. Isolation label is self-assessed by the observer. Human can override with a correction entry (new block, cite prior by timestamp).
6. `[single-point]` observations accumulate — when N single-points at different states across the same thread reach an N-comparison, write a new entry labeled `[N-comparison, N=X]` that cites the prior timestamps.
7. Downgrades section is MANDATORY whenever the observer had a causal conclusion in mind. If no conclusion was being drawn, write `n/a — descriptive observation only`.

## Why this exists

Source: pm-london wedge, 2026-04-25. After the ship skill added `§0.5 Premise Inheritance`, `§2.6 Causal Chain`, `§2.7 Premise Audit`, `§X.9 Open Gaps` — the main assistant STILL concluded "wedge reproduces at flag=false → premise falsified" from one 15-min snapshot with ≥3 unisolated variables. The structured phase templates only run when subagents are invoked. In-chat inference by the main assistant bypasses them. This template routes every live observation through the same discipline the agents follow, so the weak link (conversational me) is forced to commit to an isolation label before citing the observation in any causal claim.

## Cross-references

- `~/.claude/CLAUDE.md` → Causal-claim gate HARD RULE (the 3-question gate)
- `~/.claude/rules/ship.md` → Debug-round isolation discipline
- `~/.claude/agents/strict-plan.md` → §0.5 Premise Inheritance
- `~/NardoWorld/lessons/multi-round-debug-confound-2026-04-25.md` → origin story
