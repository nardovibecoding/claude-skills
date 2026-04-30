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
| `/radio reply <name> <msg_id> "msg"` | reply | send reply back to named peer; links to original by msg_id | `/radio reply A 11111-999 "done"` |
| `/radio claim <path>` | — | claim a file/dir; block other sessions from editing it | `/radio claim ~/project/foo.ts` |
| `/radio release <path>` | — | release own claim; broadcast unlock | `/radio release ~/project/foo.ts` |
| `/radio release --all` | — | release all own claims (called automatically on leave) | `/radio release --all` |
| `/radio claims` | — | list active claims with ages; sweep dead-session claims | `/radio claims` |
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
- **`mode=ask`** — when you receive a `<channel source='bus' mode='ask' from='<X>' msg_id='<id>'>` event, treat it as if the user just asked the question. Produce your full answer as your normal turn output. Then immediately invoke:
  ```bash
  BUS_NAME=$NAME bun run ~/.claude/skills/bus/plugin/src/cli/send.ts reply <X> <id> "<your-answer>"
  ```
  This relays your answer back to sender A's inbox. The relay call is mandatory — without it, A never receives your response. After sending, do NOT chain any further replies on your own initiative.
- **`mode=consensus kind=question`** — a consensus round question has arrived. Cast ONE vote for this round via:
  ```bash
  BUS_NAME=$NAME BUS_TARGET_SID=<from_session_id> \
    bun run ~/.claude/skills/bus/plugin/src/cli/send.ts vote \
    <consensus_id> <round> <agree|disagree> "<1-line reason <=20 words>"
  ```
  Only one vote per round (initiator deduplicates by from+round). Do not free-form chat during the consensus run.
- **`mode=consensus kind=vote`** — silently log; do not respond. Vote envelopes are routed to the initiator's inbox only; non-initiators should never receive them in normal operation.
- **`mode=consensus kind=verdict`** — display the verdict to the user (CONSENSUS or NO-CONSENSUS with final round and agree/total). No further action. Resume free-form after verdict or after user says `/radio end-consensus`.
- **`mode=reply`** — when you receive `<channel source='bus' mode='reply' from='<X>' in_reply_to='<id>'>`, display the reply and update your context. **Do not call `send.ts reply` again** (anti-loop rule). The conversation ends here unless the user explicitly asks you to follow up.

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

## Step 2 — Assign name A→Z (+ write sentinel) via `join.sh`

Atomic name pick + sentinel write are bundled into `scripts/join.sh`. Locking primitive is `mkdir`-as-lock (atomic on POSIX); `flock(1)` is absent on macOS Bash 3.2 by default. Critical section runs in <50ms typical.

```bash
# Optional: BUS_NAME=A forces a specific name (rejected if taken).
RESP=$(bash ~/.claude/skills/bus/scripts/join.sh)
echo "$RESP" | jq -e '.ok == true' >/dev/null || {
  REASON=$(echo "$RESP" | jq -r '.reason')
  echo "[radio] join failed: $REASON" >&2
  exit 1
}
NAME=$(echo "$RESP" | jq -r '.name')
SID=$(echo "$RESP" | jq -r '.session_id')
echo "Joined as **$NAME**"
```

`join.sh` does, inside the critical section: stale-sentinel sweep → read+dedupe registry (60s liveness window) → pick A..Z (fallback AA..AZ) → append registry entry → write `~/.claude/bus/opted-in/<sid>`. Validates `BUS_NAME` against `^[A-Z]+$` (reject specials/injection); auto-uppercases lowercase input.

## Step 3 — Sentinel handshake (already done by Step 2)

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

# reply: resolve recipient name → sid, then invoke (3-arg form)
TARGET_SID=$(bash ~/.claude/skills/bus/scripts/resolve_name.sh "$TARGET_NAME")
[ -z "$TARGET_SID" ] && { echo "[radio] no peer $TARGET_NAME within 60s"; exit 1; }
BUS_NAME=$NAME bun run ~/.claude/skills/bus/plugin/src/cli/send.ts reply "$TARGET_NAME" "$IN_REPLY_TO_MSG_ID" "$PAYLOAD"
```

Syntax aliases: `@A msg` → `tell A "msg"`; `@all msg` → `all "msg"`.

### Consensus protocol (mode=consensus)

**Initiator** (`/radio consensus <question>`):
```bash
BUS_NAME=$NAME BUS_SID=$SID bash ~/.claude/skills/bus/scripts/consensus.sh "$QUESTION"
```
The script runs 3 rounds (hard cap). Each round:
1. Broadcasts `kind=question` envelope to `all.jsonl`
2. Waits 60s polling initiator's inbox for `kind=vote` envelopes
3. Tallies votes (dedup by from+round); if `agree*100/total >= 75` → CONSENSUS, early exit
After final round (or early exit): broadcasts `kind=verdict` envelope to `all.jsonl`.

**Threshold**: integer math — `agree*100/total >= 75`. So 3/4=75 PASSES, 2/3=66 FAILS. Zero responses = no consensus.

**Peer** (non-initiator): on receiving `kind=question`, cast one vote per round (see Mode behavior above). On receiving `kind=verdict`, display to user and stop.

## Step 6 — Stop verbs

`/radio stop` (also `off`/`leave`/`quit`/`stop bus`/`stop radio`):

```bash
# 1. Broadcast leave notice (best-effort; ignore failure if writer down)
BUS_NAME=$NAME bun run ~/.claude/skills/bus/plugin/src/cli/send.ts all "$NAME leaving" 2>/dev/null || true

# 2. Atomic teardown: SIGTERM plugin + remove sentinel + drop registry entries.
RESP=$(bash ~/.claude/skills/bus/scripts/leave.sh)
echo "$RESP" | jq -e '.ok == true' >/dev/null || echo "[radio] leave warning: $RESP" >&2

# 3. Heartbeat process is the bash backgrounded in Step 4 — TaskStop its task_id
#    (recorded when started), or it auto-exits when sentinel disappears next loop.

echo "Radio stopped. Plugin tails killed; sentinel removed; registry entries dropped."
```

`leave.sh` does, inside the same `mkdir`-lock critical section as `join.sh`: read `plugin-pid/<sid>` and SIGTERM if present (fallback to `pkill -f "plugin:bus@local.*<sid>"` covered by main.ts shutdown handler) → `rm` sentinel → filter `registry.jsonl` to drop all entries with this `session_id`.

## Plugin lifecycle

- Plugin **auto-attaches** at session start via `--channels plugin:bus@local` flag in claude alias. No skill action needed at launch.
- Plugin reads sentinel **ONCE at startup** (per OI-S3-1). If you `/radio join` after starting `claude` without having previously been opted-in, the plugin is already idle and tails are not running. Fix:
  ```
  exec claude --channels plugin:bus@local --resume <session_id>
  ```
  Or restart the session normally (next start will check sentinel).
- Plugin writes its own PID to `~/.claude/bus/plugin-pid/<sessionId>` on startup (per server.ts shutdown handler removes it). `/radio stop` reads that file to SIGTERM the right process.

## References

`plugin/src/{writer,session,sentinel,spool,types}.ts`, `plugin/src/cli/send.ts`, `plugin/server.ts`, `~/.ship/bus-channel-redesign/goals/{01-spec.md,02-plan.md}`. v1 archived at `SKILL.md.v1-backup`.

## § File coordination (claim/release)

Sessions can lock a file path so no other session's Edit/Write/NotebookEdit/MultiEdit tool call proceeds without explicit bypass.

**Claim semantics:**
- `claim.sh <path>` resolves to absolute path, sha256 keys a file in `~/.claude/bus/claims/<sha>`.
- If the path is already claimed by another live session: `{ok:false, reason:"already_claimed"}`, exit 1.
- Idempotent: claiming your own already-claimed path refreshes `ts` and returns `{ok:true, refreshed:true}`.
- Dead-session claims (kill -0 fails) are auto-expired and taken over.
- Claim file has 6 required fields: `path`, `sha`, `session_id`, `name`, `ts`, `host`.

**Release semantics:**
- `release.sh <path>` removes the claim. No-op if not claimed.
- `release.sh --all` releases all own claims. Called automatically on `/radio stop` via leave.sh.
- `release.sh <path> --force` releases even a foreign claim (emergency; broadcasts).

**Hook enforcement:**
- `~/.claude/hooks/radio_claim_guard.py` fires on PreToolUse for `Edit`, `Write`, `NotebookEdit`, `MultiEdit`.
- Reads `BUS_DIR/claims/<sha>` for the target file_path; blocks if claimed by another live session.
- Fast-exit: if `~/.claude/bus/claims/` is empty or missing, exits in <1ms (zero overhead).
- Bypass: set `RADIO_CLAIM_BYPASS=1` in env — hook allows with stderr warning.
- Stale claims (dead PID) are swept on read by both hook and `claims_list.sh`.

**Stale sweep:** `claims_list.sh` auto-removes claims from dead sessions older than 1 hour.

**Step 5 dispatch for claim verbs:**
```bash
# /radio claim <path>
bash ~/.claude/skills/bus/scripts/claim.sh "$PATH_ARG"

# /radio release <path>  OR  /radio release --all
bash ~/.claude/skills/bus/scripts/release.sh "$PATH_ARG"   # or --all

# /radio claims  [--json]
bash ~/.claude/skills/bus/scripts/claims_list.sh
```

## v1 decommission status

v1 hook decommissioned 2026-04-30 (S8). `bus_reminder.py` renamed `.disabled`. `settings.json` UserPromptSubmit hook entry removed (backup at `~/.claude/settings.json.bak.s8.*`). v1 SKILL.md preserved at `SKILL.md.v1-backup`. Re-enable: `mv ~/.claude/hooks/bus_reminder.py{.disabled,}` + restore settings.json from latest `.bak.s8.*`.
