# Bus v1 → v2 Migration Playbook

- **Date:** 2026-04-30
- **Ship slug:** bus-channel-redesign
- **Spec:** `~/.ship/bus-channel-redesign/goals/01-spec.md`
- **Audit:** `~/.ship/bus-channel-redesign/goals/01-spec-audit.md`
- **Plan:** `~/.ship/bus-channel-redesign/goals/02-plan.md`
- **Execution log:** `~/.ship/bus-channel-redesign/experiments/03-execution-log.md`

---

## TL;DR

- Transport: hook polling `/tmp/claude_bus*` -> MCP channels push from `~/.claude/bus/*`.
- Slash trigger: `/bus *` -> `/radio *` (`/bus *` kept as alias).
- Marker: global `~/.cache/claude_bus_active.json` -> per-session sentinel `~/.claude/bus/opted-in/<sid>`.
- Required flag: every claude invocation now needs `--channels plugin:bus@local` (your `claude` alias adds it as of 2026-04-30 ~14:45 HKT).
- Verbs unchanged in spirit: `join`, `stop`/`leave`/`off`/`quit`, `tell`, `ask`, `reply`, `all`, `consensus`.

---

## What changed (v1 vs v2)

| dimension       | v1 (legacy)                                 | v2 (this ship)                                              |
|-----------------|---------------------------------------------|-------------------------------------------------------------|
| trigger         | `/bus join`                                 | `/radio join` (`/bus join` aliased)                         |
| transport       | hook polling jsonl in `/tmp`                | MCP channel push from Bun plugin                            |
| marker          | global file `~/.cache/claude_bus_active.json` | per-session sentinel `~/.claude/bus/opted-in/<sid>`        |
| name pick       | shell race on tmpfile                       | `flock`-style `mkdir` lock + jsonl registry                 |
| send            | python script appends jsonl                 | TypeScript CLI `bun src/cli/send.ts ...`                    |
| modes           | implicit                                    | explicit envelope `mode: notify|ask|reply|consensus`        |
| dormancy        | constant tail in shell                      | plugin idle until sentinel present, then push               |
| hook            | `bus_reminder.py` PreCompact polling        | hook decommissioned in S8 (`bus_reminder.py.disabled`, settings.json scrubbed) |

---

## Verb cheatsheet (post-migration)

- `/radio join` — pick name (A,B,C,...), write sentinel, plugin starts pushing.
- `/radio stop` — remove sentinel, SIGTERM plugin (aliases: `leave`, `off`, `quit`).
- `/radio tell <name> "msg"` — targeted notify (no reply expected).
- `/radio ask <name> "msg"` — targeted question (peer auto-replies).
- `/radio reply <name> <msg_id> "msg"` — answer a specific ask.
- `/radio all "msg"` — broadcast to every joined session.
- `/radio consensus <question>` — run multi-round vote.
- Aliases: every `/bus *` works; inline `@A msg` and `@all msg` still work.

---

## In-flight v1 sessions at cutover

- A pre-cutover session that ran `/bus join` is still polling its v1 hook until you `/bus stop` it OR the v1 hook moves to `.disabled` (S8).
- After S8 ships, NEW `/bus join` invocations no longer get hook injection — but CLI `tell`/`all` writes still land in the spool.
- Recommended path: `/bus stop` in any active session, exit, open a fresh terminal, run `/radio join`.

---

## Manual setup status

1. Done — alias appender ran via `bash ~/.claude/skills/bus/scripts/install_alias.sh` (2026-04-30 ~14:45 HKT). Confirmed in `~/.zshrc:77` (`--channels plugin:bus@local` injected; pre-edit backup at `~/.zshrc.bak.1777532508`).
2. Done — session_id probe ran (`~/.claude/skills/bus/scripts/probe_session_id.sh`); `CLAUDE_SESSION_ID` not exported by harness, PID-walk-up locked in as resolution path.
3. Pending — v1 hook decommission (S8). `~/.claude/hooks/bus_reminder.py` still active; `settings.json` still references it (line ~590). Pre-S8 settings backup already staged at `~/.claude/settings.json.bak.s8.1777537760`.
4. Pending — open new claude sessions to fully exercise v2. Pre-alias sessions can use the CLI but will not receive channel push.

---

## What to do for each new session

1. Open a new terminal (alias auto-loads `--channels plugin:bus@local`).
2. Run `/radio join` — picks A/B/C..., writes `~/.claude/bus/opted-in/<sid>`.
3. Plugin tails `~/.claude/bus/all.jsonl` and `~/.claude/bus/inbox/<sid>.jsonl`, pushes envelopes.
4. When done: `/radio stop` (or `leave` / `off` / `quit`).

---

## Mode envelope cheatsheet

| envelope mode + kind            | expected behavior on receive                                       |
|---------------------------------|--------------------------------------------------------------------|
| `mode=notify`                   | one-line ack, no further action                                    |
| `mode=ask`                      | answer fully, then auto-call `reply` via CLI                       |
| `mode=consensus kind=question`  | cast exactly one vote per round                                    |
| `mode=consensus kind=verdict`   | display result only, no further action                             |
| `mode=reply`                    | display only, do NOT chain another reply (anti-loop)               |

---

## File map (post-migration)

```
~/.claude/bus/
├── all.jsonl              # broadcast spool (created on first send)
├── inbox/<sid>.jsonl      # per-session targeted spool
├── opted-in/<sid>         # opt-in sentinel
├── plugin-pid/<sid>       # plugin pid (for /radio stop SIGTERM)
├── registry.jsonl         # name registry (A,B,C... + sid + ts)
└── registry.lock          # mkdir-as-lock for atomic name pick

~/.claude/skills/bus/
├── SKILL.md               # v2 (lead with /radio)
├── SKILL.md.v1-backup     # v1 preserved
├── MIGRATION.md           # this file
├── scripts/
│   ├── install_alias.sh
│   ├── probe_session_id.sh
│   ├── join.sh
│   ├── leave.sh
│   ├── consensus.sh
│   ├── resolve_name.sh
│   ├── _lock_lib.sh
│   ├── name_pick_test.sh
│   ├── test_reply_e2e.sh
│   └── test_consensus_e2e.sh
└── plugin/                # Bun MCP plugin
    ├── server.ts
    ├── package.json
    ├── tsconfig.json
    ├── .claude-plugin/plugin.json
    ├── .mcp.json
    ├── src/{writer,types,session,sentinel,spool,dedupe}.ts
    ├── src/cli/send.ts
    └── test/{writer,session,spool,cli,consensus}.test.ts
```

---

## Rollback plan (if v2 turns out broken)

- Restore v1 hook: `mv ~/.claude/hooks/bus_reminder.py.disabled ~/.claude/hooks/bus_reminder.py` (only needed once S8 has disabled it; today the .py is still live).
- Restore settings.json: `cp ~/.claude/settings.json.bak.s8.1777537760 ~/.claude/settings.json` (pre-S8 snapshot).
- Restore SKILL.md: `cp ~/.claude/skills/bus/SKILL.md.v1-backup ~/.claude/skills/bus/SKILL.md`.
- Remove `--channels` flag from `~/.zshrc:77` (or restore from `~/.zshrc.bak.1777532508`, the S0 snapshot).
- Drop transient state: `rm -rf ~/.claude/bus/{inbox,opted-in,plugin-pid}` (keep `registry.jsonl` as historical).

---

## Open issues / known gaps

- OI-S2-2: `bin: "./server.ts"` declared but discovery uses `.mcp.json`'s `bun run start`. Both kept for fakechat parity.
- OI-S2-3: `--channels plugin:bus@local` channel-name match verified manually only; no automated assert.
- OI-S3-1: post-startup `/radio join` requires session restart (plugin reads sentinel only at boot).
- OI-S3-3: tail starts at EOF — no backlog replay on plugin start.
- OI-S3-4: `from_session_id` is trusted; acceptable for single-user local-only bus.
- OI-S5-1 (registry): `_bus_resolve_sid` walks 16 ancestors; deep wrapper chains may exhaust.
- OI-S5-1 (envelope): no typed `round`/`kind` in envelope yet; protocol carried in payload.
- OI-S5-2 (registry): stale-lock breaker fires at 30s; lawful holder stalls beyond that risk eviction.
- OI-S5-3: `leave.sh` broadcast precedes lock acquisition; `send.ts` hang would skip the broadcast.
- OI-S5-4: `BUS_FORCE_SID` test override honored unconditionally; gate behind `BUS_TEST_MODE=1` for hardening.
- OI-S5-5: 50-concurrent stress was specced, only 20 was run; plenty of headroom in practice.
- OI-S7-1: consensus polls every 2s; up to 2s latency before first vote counted.
- OI-S7-2: `consensus.sh` uses `bun --eval` with string interpolation; double-quotes inside the question break the JS string. Escape or rewrite as TS helper.
- OI-S7-3: verdict envelopes use `round: 0` (outside spec's 1-3); writer.ts allows it explicitly for `kind=verdict`.
- Reply-depth field absent — anti-loop relies on model discipline alone.

---

## References

- Spec: `~/.ship/bus-channel-redesign/goals/01-spec.md`
- Spec audit: `~/.ship/bus-channel-redesign/goals/01-spec-audit.md`
- Plan: `~/.ship/bus-channel-redesign/goals/02-plan.md`
- Execution log: `~/.ship/bus-channel-redesign/experiments/03-execution-log.md`
- Skill (v2): `~/.claude/skills/bus/SKILL.md`
- Skill (v1 archive): `~/.claude/skills/bus/SKILL.md.v1-backup`
