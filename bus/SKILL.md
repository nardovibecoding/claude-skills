---
name: bus
description: "Cross-session message bus on Channels MCP push. Sessions opt-in via /radio join (writes sentinel), broadcast via /radio all, target via /radio tell <name>, ask-and-wait via /radio ask <name>. Auto-name A→Z, 60s liveness, 3-round consensus mode (75%/60s/cap). Mode envelope (notify|ask|consensus|reply) controls whether recipient model responds or silently acks. Triggers: /radio (primary), /bus (legacy alias). Channels: plugin:bus@local must be loaded (--channels flag in claude alias)."
user_invocable: true
---

# /radio (internal: bus) — cross-session message bus v2

## What it does

Lets multiple Claude Code sessions on this machine talk. One session opts in (`/radio join`), the plugin (`plugin:bus@local`) tails a shared spool and pushes new messages into the session as channel events. No polling, no monitor tasks, no /tmp registry — replaces v1 entirely.

## Verbs

| verb | mode | what it does | example |
| --- | --- | --- | --- |
| `/radio join` | — | write sentinel; pick name A→Z; start heartbeat | `/radio join` |
| `/radio stop` (also `off`/`leave`/`quit`) | — | SIGTERM plugin tails; remove sentinel; broadcast leave | `/radio stop` |
| `/radio tell <name> "msg"` | notify | targeted message; recipient acks ≤1 line | `/radio tell B "fyi"` |
| `/radio ask <name> "msg"` | ask | recipient responds fully; reply auto-relayed back | `/radio ask B "status?"` |
| `/radio all "msg"` | notify | broadcast to every joined peer | `/radio all "shipped X"` |
| `/radio consensus <q>` | consensus | 3-round vote, 75% threshold, 60s/round | `/radio consensus "pg or mysql?"` |
| `@A msg` | notify | syntax alias for `/radio tell A "msg"` | `@A heads up` |
| `@all msg` | notify | syntax alias for `/radio all "msg"` | `@all going AFK` |

## /bus legacy

`/bus <verb>` still works — every verb above accepts `/bus` as a synonym. When the user typed `/bus`, emit one line at the top of the response:

```
→ /radio (legacy /bus alias active)
```

Then run the same handler. Do not deprecate-warn beyond that one line.

## Mode behavior (model-side rules)

When a channel push arrives, the meta block carries `mode`. The model running this session reads SKILL.md (this file) and applies the rule for the inbound mode:

- **`mode=notify`** — display the message; respond with ≤1 line ack ("noted from B") and **do not take action**. No bash, no tools, no follow-up question. The sender chose `tell`/`all` precisely so the recipient does NOT chain work.
- **`mode=ask`** — treat as if the user just asked the question. Respond fully. After the response, auto-relay back to sender via `/radio reply` (use `BUS_IN_REPLY_TO=<msg_id>` and target=sender's `from_session_id`).
- **`mode=consensus`** — follow the 3-round consensus protocol below. One vote per round; hard cap 3; 75% threshold.
- **`mode=reply`** — display the reply; update context. **Do not chain a counter-reply** unless new information genuinely requires it (anti-loop).

## Anti-loop discipline

- Plain acks ("ok", "got it", "thanks") arrive as `mode=notify` — display, never reply.
- Never reply to your own auto-relayed reply.
- Sender of a `mode=ask` waits for one `mode=reply`; do not re-ask.

## Auto-announce reflex (mandatory while joined)

While the sentinel `~/.claude/bus/opted-in/<sessionId>` exists, broadcast on these events without waiting for the user — silence here makes the bus useless:

1. **Milestone shipped** — bg agent returns SHIPPED, or you finish a logical unit
2. **Pivot** — strategy change discovered mid-work
3. **Blocker** — stuck on something another session might resolve
4. **Shared-surface touch** — about to edit files another session also touches
5. **Decision made** — user-confirmed judgment that affects another session's plan
6. **About to do destructive op** — before rm/force-push/migration

Format: `/radio all "<1-line>"` with leading kind tag, e.g. `/radio all "[milestone] S4 landed"`.

## Step 0 — Pre-flight (every /radio invocation)

```bash
# 0a. Resolve claude ancestor PID + verify --channels plugin:bus@local.
P=$(ps -p $$ -o ppid= | tr -d ' '); CLAUDE_PID=""
for _ in $(seq 1 16); do
  CMD=$(ps -p $P -o command= 2>/dev/null | awk '{print $1}'); BASE="${CMD##*/}"
  if [ "$BASE" = "claude" ]; then CLAUDE_PID=$P; break; fi
  P=$(ps -p $P -o ppid= 2>/dev/null | tr -d ' '); [ -z "$P" ] || [ "$P" = "1" ] && break
done
[ -z "$CLAUDE_PID" ] && { echo "[radio] cannot locate claude ancestor PID"; exit 1; }
ps -p $CLAUDE_PID -o command= | grep -q -- "--channels[= ][^ ]*plugin:bus@local" || {
  echo "[radio] Channel plugin:bus@local not loaded. Re-run install_alias.sh or restart claude with --channels plugin:bus@local." >&2
  exit 1
}

# 0b. Sweep stale sentinels (dead PIDs).
for f in ~/.claude/bus/opted-in/*; do
  [ -f "$f" ] || continue
  pid=$(basename "$f"); kill -0 "$pid" 2>/dev/null || rm -f "$f"
done
```

## Step 1 — Resolve session_id

Walk parent processes for the first ancestor whose argv0 basename is exactly `claude`. Same logic as `plugin/src/session.ts:40-63`. The Step 0 snippet above already computed `CLAUDE_PID` — that IS the `session_id`.

Reuse:

```bash
SID=$CLAUDE_PID
```

## Step 2 — Assign name A→Z

Atomic critical section via `flock`:

```bash
mkdir -p ~/.claude/bus
NAME=$(
  ( flock 9
    # Dedupe by name, latest ts within 60s.
    used=$(jq -s 'group_by(.name) | map(max_by(.ts)) |
                  map(select(.ts >= (now - 60))) | map(.name) | .[]' \
                  ~/.claude/bus/registry.jsonl 2>/dev/null | tr -d '"')
    for L in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z; do
      echo "$used" | grep -qx "$L" || { echo "$L"; break; }
    done
  ) 9>~/.claude/bus/registry.lock
)
[ -z "$NAME" ] && NAME=AA   # A-Z exhausted, fallback
jq -cn --arg n "$NAME" --arg sid "$SID" --argjson ts $(date +%s) \
  '{name:$n, session_id:$sid, ts:$ts}' >> ~/.claude/bus/registry.jsonl
echo "Joined as **$NAME**"
```

## Step 3 — Write opt-in sentinel

```bash
mkdir -p ~/.claude/bus/opted-in
echo "joined $(date -u +%FT%TZ) name=$NAME" > ~/.claude/bus/opted-in/$SID
```

The plugin reads this **once on startup**. If you joined after `claude` started without prior opt-in, the plugin is already idle (zero CPU, no tails) — see § Plugin lifecycle.

## Step 4 — Heartbeat + idle auto-stop

Background `while true` loop, sleep 30s. Each tick: re-append registry entry (`{name, session_id, ts}`); check `tail -20 ~/.claude/bus/all.jsonl` for last ts; check peer count via dedupe-by-name. If `now - last_msg > 900` AND `peers == 0`: broadcast `"$NAME idle-stop"` via send.ts, `rm` sentinel, exit. Run with `run_in_background: true`; record task_id for `/radio stop`.

## Step 5 — Send verbs (single shared writer)

Every send goes through `plugin/src/cli/send.ts` → `writer.ts` (`appendBroadcast`/`appendTargeted`/`appendReply`). The skill bash NEVER writes JSON to spool files directly — Sh1 single-source enforcement.

For `tell`/`ask` first resolve `<name>` → `session_id` via registry (latest entry within 60s), then:

```bash
# tell / ask: resolve target sid, then invoke
TARGET_SID=$(jq -s --arg n "$TARGET_NAME" 'group_by(.name) | map(max_by(.ts)) |
  map(select(.name == $n and .ts >= (now - 60))) | .[0].session_id' \
  ~/.claude/bus/registry.jsonl 2>/dev/null | tr -d '"')
[ -z "$TARGET_SID" ] || [ "$TARGET_SID" = "null" ] && { echo "[radio] no peer $TARGET_NAME within 60s"; exit 1; }
BUS_NAME=$NAME BUS_TARGET_SID=$TARGET_SID \
  bun run ~/.claude/skills/bus/plugin/src/cli/send.ts <verb> "$TARGET_NAME" "$PAYLOAD"

# all / consensus: no target resolution
BUS_NAME=$NAME bun run ~/.claude/skills/bus/plugin/src/cli/send.ts <verb> "$PAYLOAD"
```

Syntax aliases: `@A msg` → `tell A "msg"`; `@all msg` → `all "msg"`.

### Consensus protocol (mode=consensus)

3 rounds, hard-capped:

1. **Round 1 — Positions** — initiator broadcasts `mode=consensus` with question. Each peer replies `mode=reply` with their position + 1-line reasoning.
2. **Round 2 — Critique** — each peer broadcasts `mode=consensus` round=2 critiquing the weakest opposing position.
3. **Round 3 — Vote** — each peer broadcasts a final ≤20-word answer.

Aggregation (initiator only): collect round-3 votes; if ≥75% agree → `/radio all "CONSENSUS: <answer>"`; else `/radio all "NO CONSENSUS. Positions: ..."`.

Termination guarantees: 60s/round timeout; cap 3 rounds; one vote per peer per round; non-initiators stop after round 3.

## Step 6 — Stop verbs

`/radio stop` (also `off`/`leave`/`quit`/`stop bus`/`stop radio`):

```bash
# Broadcast leave notice
BUS_NAME=$NAME bun run ~/.claude/skills/bus/plugin/src/cli/send.ts all "$NAME leaving"

# SIGTERM the plugin tails (sentinel removal alone won't stop them — per OI-S3-2).
PLUGIN_PID_FILE=~/.claude/bus/plugin-pid/$SID
if [ -f "$PLUGIN_PID_FILE" ]; then
  kill -TERM "$(cat $PLUGIN_PID_FILE)" 2>/dev/null
  rm -f "$PLUGIN_PID_FILE"
else
  pkill -TERM -f "plugin:bus@local.*$SID" 2>/dev/null
fi

# Remove sentinel + heartbeat
rm -f ~/.claude/bus/opted-in/$SID
# Heartbeat process is the bash backgrounded in Step 4 — TaskStop its task_id
# (recorded when started), or it auto-exits when sentinel disappears next loop.

echo "Radio stopped. Plugin tails killed; sentinel removed; registry entry expires in 60s."
```

## Plugin lifecycle

- Plugin **auto-attaches** at session start via `--channels plugin:bus@local` flag in claude alias. No skill action needed at launch.
- Plugin reads sentinel **ONCE at startup** (per OI-S3-1). If you `/radio join` after starting `claude` without having previously been opted-in, the plugin is already idle and tails are not running. Fix:
  ```
  exec claude --channels plugin:bus@local --resume <session_id>
  ```
  Or restart the session normally (next start will check sentinel).
- Plugin writes its own PID to `~/.claude/bus/plugin-pid/<sessionId>` on startup (per server.ts shutdown handler removes it). `/radio stop` reads that file to SIGTERM the right process.

## References

- Writer (single source): `~/.claude/skills/bus/plugin/src/writer.ts`
- Send CLI (skill→writer adapter): `~/.claude/skills/bus/plugin/src/cli/send.ts`
- Plugin server: `~/.claude/skills/bus/plugin/server.ts`
- Session id walker: `~/.claude/skills/bus/plugin/src/session.ts`
- Sentinel reader/sweeper: `~/.claude/skills/bus/plugin/src/sentinel.ts`
- Spool tailer: `~/.claude/skills/bus/plugin/src/spool.ts`
- Envelope schema: `~/.claude/skills/bus/plugin/src/types.ts`
- Spec + plan: `~/.ship/bus-channel-redesign/goals/{01-spec.md, 02-plan.md}`
- v1 backup: `~/.claude/skills/bus/SKILL.md.v1-backup`
