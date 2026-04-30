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
 *   send.ts tell      <name>      <payload>                                -> mode=notify, targeted
 *   send.ts ask       <name>      <payload>                                -> mode=ask,    targeted
 *   send.ts all       <payload>                                            -> mode=notify, broadcast
 *   send.ts consensus <payload>                                            -> mode=consensus, broadcast
 *   send.ts reply     <name|sid>  <in_reply_to>  <payload>                -> mode=reply, targeted
 *   send.ts vote      <consensus_id> <round> <agree|disagree> "<reason>"  -> mode=consensus kind=vote, targeted to initiator
 *
 * Required env (skill provides):
 *   BUS_NAME       - sender bus letter, e.g. "A"
 *   BUS_TARGET_SID - for tell/ask/vote: the resolved sessionId for target.
 *                    Skill resolves via registry lookup before calling CLI.
 *                    For vote: must be the initiator session_id (found via all.jsonl scan).
 *
 * Optional env:
 *   BUS_IN_REPLY_TO - original msg_id when verb=reply
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
import os from "node:os";

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

// Discriminated union so each path has its exact args available.
type ParsedArgs =
  | { verb: "tell" | "ask"; target: string; payload: string }
  | { verb: "all" | "consensus"; payload: string }
  | { verb: "reply"; target: string; inReplyTo: string; payload: string }
  | { verb: "vote"; consensusId: string; round: number; stance: "agree" | "disagree"; reason: string; payload: string };

function parseArgs(argv: string[]): ParsedArgs {
  if (argv.length < 2) die("usage: send.ts <verb> [args...] <payload>");
  const verb = argv[0] as Verb;
  if (!(verb in VERB_TO_MODE)) die(`unknown verb: ${verb}`);

  if (verb === "all" || verb === "consensus") {
    if (argv.length !== 2) die(`${verb} takes exactly 1 arg: <payload>`);
    return { verb, payload: argv[1]! };
  }
  if (verb === "reply") {
    // reply <target> <in_reply_to_msg_id> <payload>
    if (argv.length !== 4) die(`reply takes 3 args: <target> <in_reply_to_msg_id> <payload>`);
    return { verb, target: argv[1]!, inReplyTo: argv[2]!, payload: argv[3]! };
  }
  if (verb === "vote") {
    // vote <consensus_id> <round> <agree|disagree> "<reason>"
    if (argv.length !== 5) die("vote takes 4 args: <consensus_id> <round> <agree|disagree> <reason>");
    const round = parseInt(argv[2]!, 10);
    if (isNaN(round) || round < 1 || round > 3) die(`vote round must be 1-3; got: ${argv[2]}`);
    const stance = argv[3] as "agree" | "disagree";
    if (stance !== "agree" && stance !== "disagree") die(`stance must be agree|disagree; got: ${argv[3]}`);
    return {
      verb,
      consensusId: argv[1]!,
      round,
      stance,
      reason: argv[4]!,
      payload: `${stance}: ${argv[4]!}`,
    };
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
    import.meta.dir,
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

/**
 * For vote verb: find initiator session_id by scanning all.jsonl for the
 * most recent kind=question envelope matching consensus_id.
 * BUS_TARGET_SID env takes precedence (set by consensus.sh or test harness).
 */
function resolveInitiatorSid(consensusId: string): string {
  const envSid = process.env.BUS_TARGET_SID;
  if (envSid && /^\d+$/.test(envSid)) return envSid;

  const allJsonl = path.join(os.homedir(), ".claude", "bus", "all.jsonl");
  const r = spawnSync("sh", [
    "-c",
    // jq: filter question envelopes for this consensus_id, emit from_session_id, take last
    `jq -r --arg cid "${consensusId}" 'select(.consensus_id == $cid and .kind == "question") | .from_session_id' "${allJsonl}" 2>/dev/null | tail -1`,
  ], { encoding: "utf8" });
  const sid = (r.stdout ?? "").trim();
  if (!sid || !/^\d+$/.test(sid)) {
    die(`cannot resolve initiator for consensus_id=${consensusId}; set BUS_TARGET_SID`);
  }
  return sid;
}

async function main(): Promise<void> {
  const parsed = parseArgs(process.argv.slice(2));

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

  const ts = new Date().toISOString();
  const msg_id = `${sid}-${Date.now()}`;

  // --- vote verb: targeted to initiator's inbox with consensus fields ---
  if (parsed.verb === "vote") {
    const initiatorSid = resolveInitiatorSid(parsed.consensusId);
    const envelope: BusEnvelope = {
      msg_id,
      from: busName,
      from_session_id: sid,
      to: initiatorSid,
      mode: "consensus",
      ts,
      payload: parsed.payload,
      round: parsed.round,
      kind: "vote",
      consensus_id: parsed.consensusId,
    };
    try {
      await appendTargeted(initiatorSid, envelope);
    } catch (e) {
      die(`write failed: ${(e as Error).message}`);
    }
    process.stdout.write(JSON.stringify({ ok: true, msg_id }) + "\n");
    process.exit(0);
  }

  // --- reply verb: targeted back to original sender ---
  if (parsed.verb === "reply") {
    const envelope: BusEnvelope = {
      msg_id,
      from: busName,
      from_session_id: sid,
      to: parsed.target,
      mode: "reply",
      ts,
      payload: parsed.payload,
      in_reply_to: parsed.inReplyTo,
    };
    try {
      const recipientSid = resolveNameToSid(parsed.target);
      await appendReply(recipientSid, { ...envelope, reply_from: busName });
    } catch (e) {
      die(`write failed: ${(e as Error).message}`);
    }
    process.stdout.write(
      JSON.stringify({ ok: true, msg_id, in_reply_to: parsed.inReplyTo }) + "\n",
    );
    process.exit(0);
  }

  // --- all / consensus: broadcast ---
  if (parsed.verb === "all" || parsed.verb === "consensus") {
    const envelope: BusEnvelope = {
      msg_id,
      from: busName,
      from_session_id: sid,
      to: "all",
      mode: VERB_TO_MODE[parsed.verb],
      ts,
      payload: parsed.payload,
    };
    const replyTo = process.env.BUS_IN_REPLY_TO;
    if (replyTo) envelope.in_reply_to = replyTo;
    // Consensus envelope fields — required by writer when mode=consensus.
    // Skill provides via env: BUS_ROUND, BUS_KIND, BUS_CONSENSUS_ID.
    if (parsed.verb === "consensus") {
      const roundStr = process.env.BUS_ROUND;
      const kind = process.env.BUS_KIND as "question" | "vote" | "verdict" | undefined;
      const consensusId = process.env.BUS_CONSENSUS_ID;
      if (roundStr) envelope.round = Number(roundStr);
      if (kind) envelope.kind = kind;
      if (consensusId) envelope.consensus_id = consensusId;
    }
    try {
      await appendBroadcast(envelope);
    } catch (e) {
      die(`write failed: ${(e as Error).message}`);
    }
    process.stdout.write(JSON.stringify({ ok: true, msg_id }) + "\n");
    process.exit(0);
  }

  // --- tell / ask: targeted ---
  const envelope: BusEnvelope = {
    msg_id,
    from: busName,
    from_session_id: sid,
    to: parsed.target,
    mode: VERB_TO_MODE[parsed.verb],
    ts,
    payload: parsed.payload,
  };
  const replyTo = process.env.BUS_IN_REPLY_TO;
  if (replyTo) envelope.in_reply_to = replyTo;
  try {
    const targetSid = process.env.BUS_TARGET_SID ?? parsed.target;
    if (!/^\d+$/.test(targetSid)) {
      die(
        `target session_id must be numeric (skill resolves <name>-><sid> via registry); got: ${targetSid}`,
      );
    }
    await appendTargeted(targetSid, envelope);
  } catch (e) {
    die(`write failed: ${(e as Error).message}`);
  }

  process.stdout.write(JSON.stringify({ ok: true, msg_id }) + "\n");
  process.exit(0);
}

// Test-only exports (skips main() when imported)
export { parseArgs, VERB_TO_MODE, resolveNameToSid, resolveInitiatorSid };

if (import.meta.main) {
  await main();
}
