#!/usr/bin/env bun
/**
 * /radio (legacy: /bus) send CLI — thin wrapper around src/writer.ts.
 *
 * The skill bash NEVER appends JSON to spool files directly. All send
 * paths route through this CLI which calls the single shared writer.
 * (Sh1 single-source enforcement; per ~/.claude/rules/pm-bot.md +
 * 2026-04-29_multi-channel-shared-storage.md.)
 *
 * Usage:
 *   send.ts tell      <name>      <payload>      → mode=notify, targeted
 *   send.ts ask       <name>      <payload>      → mode=ask,    targeted
 *   send.ts all       <payload>                  → mode=notify, broadcast
 *   send.ts consensus <payload>                  → mode=consensus, broadcast
 *   send.ts reply     <name|sid>  <in_reply_to>  <payload>  → mode=reply, targeted
 *
 * Required env (skill provides):
 *   BUS_NAME       — sender bus letter, e.g. "A"
 *   BUS_TARGET_SID — for `tell`/`ask`: the resolved sessionId for <name>.
 *                    Skill resolves via registry lookup before calling CLI.
 *
 * Optional env:
 *   BUS_IN_REPLY_TO — original msg_id when verb=reply
 *
 * Output: prints {"ok":true,"msg_id":"..."} on stdout, exits 0.
 *         On error: prints "[send] <msg>" to stderr, exits 2.
 *
 * Session-id resolution: walks parent-process chain via session.ts.
 * If invoked outside any claude session (e.g. cron), throws.
 */

import { resolveSessionId } from "../session.js";
import {
  appendBroadcast,
  appendTargeted,
  appendReply,
} from "../writer.js";
import type { BusEnvelope, BusMode } from "../types.js";
import { spawnSync } from "node:child_process";
import path from "node:path";

type Verb = "tell" | "ask" | "all" | "consensus" | "reply" | "vote";

const VERB_TO_MODE: Record<Verb, BusMode> = {
  tell: "notify",
  ask: "ask",
  all: "notify",
  consensus: "consensus",
  reply: "reply",
  vote: "consensus",
};

function die(msg: string, code = 2): never {
  process.stderr.write(`[send] ${msg}\n`);
  process.exit(code);
}

function parseArgs(argv: string[]): {
  verb: Verb;
  target?: string;
  inReplyTo?: string;
  payload: string;
} {
  if (argv.length < 2) die("usage: send.ts <verb> [target] [in_reply_to] <payload>");
  const verb = argv[0] as Verb;
  if (!(verb in VERB_TO_MODE)) die(`unknown verb: ${verb}`);

  if (verb === "all" || verb === "consensus" || verb === "vote") {
    if (argv.length !== 2) die(`${verb} takes exactly 1 arg: <payload>`);
    return { verb, payload: argv[1]! };
  }
  if (verb === "reply") {
    // reply <target> <in_reply_to_msg_id> <payload>
    if (argv.length !== 4) die(`reply takes 3 args: <target> <in_reply_to_msg_id> <payload>`);
    return { verb, target: argv[1]!, inReplyTo: argv[2]!, payload: argv[3]! };
  }
  // tell / ask: <target> <payload>
  if (argv.length !== 3) die(`${verb} takes 2 args: <target> <payload>`);
  return { verb, target: argv[1]!, payload: argv[2]! };
}

function resolveNameToSid(nameOrSid: string): string {
  // Numeric: pass through immediately.
  if (/^\d+$/.test(nameOrSid)) return nameOrSid;
  // Name: call resolve_name.sh.
  const script = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "scripts",
    "resolve_name.sh",
  );
  const r = spawnSync("bash", [script, nameOrSid], { encoding: "utf8" });
  if (r.status !== 0) {
    die(`recipient_not_found: ${nameOrSid}`);
  }
  const sid = r.stdout.trim();
  if (!sid || !/^\d+$/.test(sid)) {
    die(`recipient_not_found: ${nameOrSid}`);
  }
  return sid;
}

async function main(): Promise<void> {
  const { verb, target, inReplyTo, payload } = parseArgs(process.argv.slice(2));

  // Resolve sender session_id from process tree (claude PID).
  let sid: string;
  try {
    sid = resolveSessionId();
  } catch (e) {
    die(`session resolve failed: ${(e as Error).message}`);
  }
  if (!/^\d+$/.test(sid)) die(`invalid session_id: ${sid}`);

  const busName = process.env.BUS_NAME;
  if (!busName || busName.length === 0) {
    die("BUS_NAME env required (skill must export sender bus letter)");
  }

  const mode = VERB_TO_MODE[verb];
  const ts = new Date().toISOString();
  const msg_id = `${sid}-${Date.now()}`;

  const envelope: BusEnvelope = {
    msg_id,
    from: busName,
    from_session_id: sid,
    to: verb === "all" || verb === "consensus" || verb === "vote" ? "all" : target!,
    mode,
    ts,
    payload,
  };

  // in_reply_to: prefer explicit arg (reply verb), then env fallback.
  const replyTo = inReplyTo ?? process.env.BUS_IN_REPLY_TO;
  if (replyTo) envelope.in_reply_to = replyTo;

  // Consensus envelope fields — required by writer validation when mode=consensus.
  // Skill provides these via env (BUS_ROUND, BUS_KIND, BUS_CONSENSUS_ID).
  if (mode === "consensus") {
    const roundStr = process.env.BUS_ROUND;
    const kind = process.env.BUS_KIND as "question" | "vote" | "verdict" | undefined;
    const consensusId = process.env.BUS_CONSENSUS_ID;
    if (roundStr) envelope.round = Number(roundStr);
    if (kind) envelope.kind = kind;
    if (consensusId) envelope.consensus_id = consensusId;
  }

  try {
    if (verb === "all" || verb === "consensus" || verb === "vote") {
      await appendBroadcast(envelope);
    } else if (verb === "reply") {
      // target may be a bus name or numeric sid; resolve_name.sh handles both.
      const recipientSid = resolveNameToSid(target!);
      // appendReply enriches envelope with mode=reply + reply_from.
      await appendReply(recipientSid, { ...envelope, reply_from: busName });
      process.stdout.write(
        JSON.stringify({ ok: true, msg_id, in_reply_to: replyTo ?? null }) + "\n",
      );
      process.exit(0);
    } else {
      // tell / ask: target is the resolved sessionId (skill resolves name→sid)
      const targetSid = process.env.BUS_TARGET_SID ?? target!;
      if (!/^\d+$/.test(targetSid)) {
        die(
          `target session_id must be numeric (skill resolves <name>→<sid> via registry); got: ${targetSid}`,
        );
      }
      // mutate envelope.to to the bus name (human-readable) but route by sid
      await appendTargeted(targetSid, envelope);
    }
  } catch (e) {
    die(`write failed: ${(e as Error).message}`);
  }

  process.stdout.write(JSON.stringify({ ok: true, msg_id }) + "\n");
  process.exit(0);
}

// Test-only export (skips main() when imported)
export { parseArgs, VERB_TO_MODE, resolveNameToSid };

if (import.meta.main) {
  await main();
}
