---
name: bus
description: Inter-session message bus.
user_invocable: true
---

# Session Bus

Connects multiple Claude Code sessions via shared files. Sessions auto-discover each other.

## Files
- Registry: `/tmp/claude_bus_registry.jsonl` — who's online
- Bus: `/tmp/claude_bus.jsonl` — message queue

## Step 1: Assign name

Names are always UPPERCASE (A, B, C). User input like `@a` is normalized to `@A` before writing to bus. Monitor matches on uppercase.

If user ran `/bus join <name>`, uppercase it and use.

Otherwise auto-assign next letter (A, B, C, …) based on who's already active:
```bash
jq -s 'group_by(.name) | map(max_by(.ts)) | map(select(.ts >= (now - 60))) | map(.name)' /tmp/claude_bus_registry.jsonl
```
Pick the first letter (A → Z) not in that list. If A is taken, pick B. If A+B taken, pick C. Etc.
Fallback if A–Z exhausted: `AA`, `AB`, … (unlikely in practice).

Tell user: "Joined as **<name>**"

## Step 2: Register

Append to `/tmp/claude_bus_registry.jsonl` using `jq` (handles escaping safely):
```bash
jq -cn --arg name "<name>" --argjson ts $(date +%s) '{name:$name,ts:$ts}' >> /tmp/claude_bus_registry.jsonl
```

Also write marker file so `bus_reminder.py` hook keeps injecting persistent context every UserPromptSubmit:
```bash
mkdir -p ~/.cache
jq -cn --arg name "<name>" --argjson ts $(date +%s) '{name:$name,joined_ts:$ts}' > ~/.cache/claude_bus_active.json
```
Without this marker, the session will FORGET it's on the bus after the first turn and stop broadcasting milestones.

## Step 3: Discover peers

Read `/tmp/claude_bus_registry.jsonl` (may not exist yet — handle gracefully).
**Dedupe by name: keep only the latest `ts` per name** (registry grows via heartbeats).
Then filter: `ts >= (now - 60)` AND `name != my_name`.
One-liner:
```bash
jq -s 'group_by(.name) | map(max_by(.ts)) | map(select(.ts >= (now - 60) and .name != "<my_name>"))' /tmp/claude_bus_registry.jsonl
```
Show peer list:
- If peers found: "Active peers: **alpha**, **beta**" 
- If none: "No peers yet. Run /bus in another session within 60s to connect."

## Step 4: Start monitoring

Use the Monitor tool with:
- `persistent: true`
- `description`: "bus messages for <name>"
- `command` (watches messages addressed to me OR to @all):
```bash
touch /tmp/claude_bus.jsonl
tail -f /tmp/claude_bus.jsonl | grep -E --line-buffered "\"to\":\"(<name>|all)\""
```

Also start a second Monitor for registry (auto-announce new joiners):
- `persistent: true`
- `description`: "bus peer joins"
- `command`:
```bash
touch /tmp/claude_bus_registry.jsonl
tail -f -n 0 /tmp/claude_bus_registry.jsonl | while read line; do
  name=$(echo "$line" | jq -r '.name')
  if [ "$name" != "<my_name>" ]; then echo "peer-seen: $name"; fi
done
```
When this Monitor emits `peer-seen: <name>`, check if it's NEW (not already in your known-peers list). If new, announce: "🔔 **<name>** joined." Ignore heartbeats of known peers.

When Monitor fires (a message arrives), parse the JSON line and display:
```
📨 [from] → you: <msg>
```
Then respond naturally to the message content.

## Step 5: Sending messages

When user says:
- `@<peer> <message>` → direct to that peer
- `@all <message>` → broadcast to all active peers

Append to `/tmp/claude_bus.jsonl` using `jq` (safe escaping):
```bash
jq -cn --arg to "<peer-or-all>" --arg from "<my_name>" --arg msg "<message>" --argjson ts $(date +%s) \
  '{to:$to,from:$from,msg:$msg,ts:$ts}' >> /tmp/claude_bus.jsonl
```
For `@all`, write a single line with `to:"all"` — each peer's Monitor matches `"to":"all"` via the regex in Step 4.

### Auto-announce triggers (MANDATORY while bus active)

While `~/.cache/claude_bus_active.json` exists, the session MUST broadcast to bus on these events — NOT wait for user to prompt:

1. **Milestone shipped** — bg agent returns with SHIPPED verdict, or you directly complete a logical unit of work
2. **Pivot** — strategy/approach change discovered mid-work
3. **Blocker** — stuck on something another session might resolve
4. **Starting work on shared surface** — touching files/dirs another session's scope also touches (check their scope from their announce)
5. **Decision made** — user-confirmed judgment that affects both sessions' plans
6. **About to do destructive op** — before rm/force-push/migration that could collide

Format: `{to:"all", from:"<name>", msg:"<1-line>", kind:"<milestone|pivot|blocker|scope|decision|warn>"}`.

Without this reflex, sessions announce once on join then go silent — the bus becomes useless.

### Anti-loop rule
When a Monitor event fires with an incoming message, respond to it naturally — BUT:
- If the message is a plain acknowledgment (e.g. "ok", "got it", "thanks"), do NOT reply. Just display it.
- Only reply when the message is a question, task, or requires action.
- Never reply to a message that was itself a reply to your own message unless new information requires it.
This prevents infinite ping-pong between auto-responding sessions.

Confirm: "Sent to **<peer>**"

## Step 6: Heartbeat (keep-alive) + idle auto-stop

Every ~30s while session is active, update your registry entry (re-append with fresh ts). This keeps you visible to new sessions joining. Also check idle-stop condition (no bus activity ≥15min AND peers ≤1) and self-exit if met:
```bash
while true; do
  jq -cn --arg name "<name>" --argjson ts $(date +%s) '{name:$name,ts:$ts}' >> /tmp/claude_bus_registry.jsonl
  # idle auto-stop
  last_msg_ts=$(tail -20 /tmp/claude_bus.jsonl 2>/dev/null | jq -r '.ts' | sort -n | tail -1)
  peer_count=$(jq -s 'group_by(.name) | map(max_by(.ts)) | map(select(.ts >= (now - 60) and .name != "<name>")) | length' /tmp/claude_bus_registry.jsonl 2>/dev/null)
  now_ts=$(date +%s)
  if [ -n "$last_msg_ts" ] && [ $((now_ts - last_msg_ts)) -gt 900 ] && [ "${peer_count:-0}" -le 0 ]; then
    jq -cn --arg to "all" --arg from "<name>" --arg msg "<name> idle-stop (15m quiet, no peers)" --argjson ts "$now_ts" --arg kind "leave" '{to:$to,from:$from,msg:$msg,ts:$ts,kind:$kind}' >> /tmp/claude_bus.jsonl
    rm -f ~/.cache/claude_bus_active.json
    exit 0
  fi
  sleep 30
done
```
Run this with `run_in_background: true`. When heartbeat exits via idle-stop, the Monitor tasks are still running — session will notice (no more heartbeats reach own monitor) and can call /bus stop to clean up, OR leave them; they die with session anyway.

## Step 7: Consensus mode (key feature)

When user says `/bus <question>` (anything after `/bus` that isn't `join <name>`) — **this session is the initiator**.

### Auto-extract own context
If the question references "my plan", "the plan", "what I proposed", "my last suggestion", or similar self-referential phrase, the initiator MUST extract the relevant content from its OWN recent conversation context (the last substantive proposal/plan/summary this session produced) and include the full text in the `msg` field of the round-1 broadcast. Do NOT ask the user to paste it — you already have it in context.

If the question is self-contained (e.g. "should we use Postgres or MySQL for X?"), just broadcast as-is.

Message envelope adds `round` and `kind` fields. Protocol:

**Round 1 — Positions**
Initiator broadcasts `{kind:"q",round:1,msg:"<question + extracted plan if applicable>"}` to all active peers (to:"all").
Each peer (including initiator) replies with `{kind:"pos",round:1,msg:"<my position + 1-line reasoning>"}` addressed `to:"*"` (i.e. broadcast).

**Round 2 — Critique**
After receiving all round-1 positions, each peer broadcasts `{kind:"crit",round:2,msg:"<critique of weakest opposing position>"}`.

**Round 3 — Vote**
Each peer broadcasts `{kind:"vote",round:3,msg:"<final answer in <=20 words>"}`.

**Aggregation (initiator only)**
Initiator collects all round-3 votes, then:
- If ≥75% agree → announce consensus: "CONSENSUS: <answer>"
- If not → announce split: "NO CONSENSUS. Positions: A=<n>, B=<m>, ..."
Write final result `{kind:"result",round:0,msg:"<summary>"}` to bus broadcast.

**Termination guarantees**
- Hard cap: 3 rounds. Never start round 4.
- Each peer responds at most ONCE per round.
- If a peer doesn't respond within 60s of round start, initiator proceeds without them.
- Non-initiator sessions: after round 3 vote, stop. Do not reply to `result`.

**Protocol enforcement**
Peer sessions receiving `kind:"q"` or `kind:"pos"` etc. should follow the protocol strictly — don't free-form chat during a consensus run. Resume free-form only after a `kind:"result"` is seen or user says `/bus end-consensus`.

## Step 8: Stop / leave bus

When user says `/bus stop`, `/bus leave`, `/bus off`, `/bus quit`, or `stop bus`:

1. **Broadcast leave notice** (optional but polite):
   ```bash
   jq -cn --arg to "all" --arg from "<my_name>" --arg msg "<my_name> leaving bus" --argjson ts $(date +%s) --arg kind "leave" \
     '{to:$to,from:$from,msg:$msg,ts:$ts,kind:$kind}' >> /tmp/claude_bus.jsonl
   ```

2. **Stop both Monitor tasks** using TaskStop on the task IDs recorded when Monitors were started (one for `bus messages for <name>`, one for `bus peer joins for <name>`).

3. **Kill heartbeat background bash** using TaskStop on the heartbeat loop's task ID (recorded when the Step 6 `while true` loop was spawned).

4. **Delete active marker:** `rm -f ~/.cache/claude_bus_active.json` (stops the reminder hook from injecting context).

5. **Do NOT delete registry/bus files** — other peers may still be active; files are shared. Your entry will time out naturally in 60s.

Confirm: "Bus stopped. Monitors + heartbeat killed; registry entry expires in 60s."

**When to use:**
- You want a clean terminal with no auto-notifications
- Many dead peer sessions are cluttering your peer-join stream
- Preparing to /clear or switch topics

**When NOT needed:**
- Session about to end anyway (all bus tasks die with session — no cleanup required)
- Short pause (monitors are cheap; leave running)

## Notes
- Multiple sessions = each discovers all others active within 60s
- 4 sessions all run `/bus` → each sees the other 3 in peer list
- Registry grows indefinitely; ignore stale entries (ts > 60s old)
- Bus file grows indefinitely; only recent messages matter (Monitor handles this via tail)
- Best outcome for consensus: 3-5 peers. With 2, it's just a debate. With >6, rounds get noisy.
- **Track task IDs** when you start Monitors (Step 4) + heartbeat (Step 6) — needed for `/bus stop`. If not recorded, use `TaskList` to find them by description.
