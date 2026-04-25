# Debug rounds log — common template

## When to use

Any bug that requires N>1 debug attempts on the same symptom. Each attempt = one round. The log lives at `.ship/<slug>/experiments/rounds.md` and is the canonical record of what was actually varied between rounds vs what was claimed to be varied.

A round entry not present here cannot be cited as evidence in any subsequent strict-plan §0.5 Premise Inheritance audit. The round is treated as `[unverified]` until logged.

## Why this exists

Source: pm-london wedge, 2026-04-25. Five rounds of "basketAtomicity = trigger" debugging, each round inherited the previous round's premise without re-checking that only the named variable had changed. Round 3's deploy flipped the flag AND landed 52 LOC of main.ts changes in the same commit (dc41bec). The "flag = trigger" conclusion survived 5 rounds because nobody logged what each round actually varied — the discipline lived in chat memory and decayed.

## File location

`.ship/<slug>/experiments/rounds.md` — append-only. New entries below prior entries. Do not edit past rows.

## Entry template

One block per round. Fill all fields; `unknown` is allowed but every `unknown` forces this round's verdict to `[unisolated]`.

```
### Round <N> — <YYYY-MM-DD HH:MM ZZZ> — <short-name>

claimed-vars-changed-vs-prior:
  - <variable>: <prior value> → <new value>
  - ...
  or: "first round — no prior baseline"

deploy state at test:
  host:               <hostname>
  service:            <systemd unit>
  git SHA:            <full 40-char SHA from `ssh <host> "cd <cwd> && git rev-parse HEAD"`>
  config file path:   <full path>
  config md5:         <md5 of config at test time>
  relevant flags:     <flag1=val, flag2=val>
  build artifacts:    <dist/ mtime, last `tsc` exit, package version>

actual-vars-changed-vs-prior (from `git diff <prev round SHA>..<this round SHA> -- <relevant paths>`):
  - <file:line range>: <what changed>
  - ...
  or: "no diff — same SHA, only config changed"
  or: "first round — no prior to diff against"

confound check:
  - claimed vars match actual vars? YES / NO
  - if NO, list extra vars that changed: <var, file:line, why it might affect outcome>
  - if SHA changed but only config-flag was claimed: list every code path touched by the diff that could plausibly affect this bug

observed outcome:
  - symptom:          <e.g. "wedge at 10:29 min, 95% futex">
  - duration to onset: <time>
  - fingerprint:      <strace/ps/journalctl tail signature, ≤10 lines>
  - link to observations.md entry: <timestamp anchor>

verdict:
  - [isolation-verified]   = exactly the claimed var changed, all other listed vars proven stable
  - [unisolated]           = ≥1 extra var changed; round is not a clean experiment
  - [first-round]          = baseline; cannot be isolation-verified by definition

permitted causal claims from this round:
  - if [isolation-verified] AND prior round exists: "<claimed var> caused <delta in symptom>"
  - if [unisolated]: "<symptom> observed under <bundle of var changes>"; NO causal claim
  - if [first-round]: descriptive only; NO comparative claim

next-round plan (if symptom persists):
  - var to vary:        <one variable>
  - vars to hold:       <explicit list, must be checkable via SHA + config diff>
  - falsification:      <observation that would refute current hypothesis>
```

## Rules

1. One entry per round. Round = one deployed code+config state tested against the same bug.
2. `git SHA` is mandatory. `unknown` is forbidden — if SHA cannot be retrieved, the round did not happen on a known artifact and cannot count as evidence.
3. `actual-vars-changed-vs-prior` MUST be computed from `git diff` + `diff` of config files. Self-report ("I only changed the flag") does not satisfy this field.
4. Verdict is mechanical: if `claimed-vars-changed-vs-prior` ≠ `actual-vars-changed-vs-prior`, verdict is `[unisolated]`. No discretion.
5. When entering Round N+1, the entry MUST cite Round N by anchor and explicitly diff against it.
6. A `[unisolated]` round does not invalidate the round itself — but no causal conclusion drawn from comparing to it can be cited downstream.
7. If 3+ consecutive `[unisolated]` rounds, escalate to a `/ship audit` — current debug method is producing noise, not signal.

## Cross-references

- `~/.claude/CLAUDE.md` → Multi-round debug confound check HARD RULE
- `~/.claude/rules/ship.md` → Debug-round isolation discipline
- `~/.claude/skills/ship/phases/common/observations.md` → live observations (rounds reference observation entries)
- `~/.claude/agents/strict-plan.md` → §0.5 Premise Inheritance (consumes this log)
- `~/NardoWorld/lessons/multi-round-debug-confound-2026-04-25.md` → origin story
