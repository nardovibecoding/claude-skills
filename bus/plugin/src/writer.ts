// Single shared writer for /bus v2. Every send path (tell/ask/all/consensus/reply)
// goes through the 3 exported functions below. Per ~/NardoWorld/lessons/
// 2026-04-29_multi-channel-shared-storage.md — one shared store + one writer.
//
// Atomicity: each append is one O_APPEND syscall (fs.promises.appendFile).
// POSIX guarantees atomic append for writes <= PIPE_BUF (4096 on macOS).
// Envelopes serialize to <500 bytes JSON, so concurrent writers from
// distinct processes interleave at line boundaries only — never mid-line.
//
// Runtime: requires Bun (uses Bun-friendly fs/promises API; identical on Node
// but we gate at load time to fail loud if the wider plugin is run elsewhere).

import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import { type BusEnvelope, BUS_MODES, REQUIRED_KEYS, CONSENSUS_KINDS, CONSENSUS_REQUIRED_KEYS } from "./types.js";

if (typeof (globalThis as { Bun?: unknown }).Bun === "undefined") {
  throw new Error("Bun runtime required, current = node");
}

const BUS_ROOT = path.join(os.homedir(), ".claude", "bus");
const BROADCAST_PATH = path.join(BUS_ROOT, "all.jsonl");
const INBOX_DIR = path.join(BUS_ROOT, "inbox");

const SESSION_ID_RE = /^\d+$/;

function validateEnvelope(env: BusEnvelope): void {
  if (env === null || typeof env !== "object") {
    throw new TypeError("envelope must be an object");
  }
  for (const key of REQUIRED_KEYS) {
    const v = env[key];
    if (typeof v !== "string" || v.length === 0) {
      throw new TypeError(`envelope missing required field: ${key}`);
    }
  }
  if (!BUS_MODES.has(env.mode)) {
    throw new TypeError(`invalid mode: ${env.mode}`);
  }
  // Consensus-specific validation.
  if (env.mode === "consensus") {
    // All three consensus fields required when mode=consensus.
    for (const key of CONSENSUS_REQUIRED_KEYS) {
      if (env[key] === undefined || env[key] === null) {
        throw new TypeError(`mode=consensus requires field: ${key}`);
      }
    }
    // round 0 is allowed for kind=verdict (final announcement); rounds 1-3 for question/vote.
    const isVerdict = env.kind === "verdict";
    if (typeof env.round !== "number" || env.round < 0 || env.round > 3) {
      throw new TypeError(`consensus round must be 0 (verdict) or 1-3; got: ${env.round}`);
    }
    if (!isVerdict && env.round === 0) {
      throw new TypeError(`round=0 only valid for kind=verdict; got kind=${env.kind}`);
    }
    if (isVerdict && env.round !== 0) {
      throw new TypeError(`kind=verdict must use round=0; got round=${env.round}`);
    }
    if (!CONSENSUS_KINDS.has(env.kind!)) {
      throw new TypeError(`invalid consensus kind: ${env.kind}`);
    }
    if (typeof env.consensus_id !== "string" || env.consensus_id.length === 0) {
      throw new TypeError("consensus_id must be a non-empty string");
    }
  } else {
    // Consensus fields forbidden on non-consensus modes.
    if (env.round !== undefined) {
      throw new TypeError(`round field only valid for mode=consensus; got mode=${env.mode}`);
    }
    if (env.kind !== undefined) {
      throw new TypeError(`kind field only valid for mode=consensus; got mode=${env.mode}`);
    }
    if (env.consensus_id !== undefined) {
      throw new TypeError(`consensus_id field only valid for mode=consensus; got mode=${env.mode}`);
    }
  }
}

function validateSessionId(sid: string): void {
  if (!SESSION_ID_RE.test(sid)) {
    throw new TypeError(`invalid targetSessionId (must be digit-only PID): ${sid}`);
  }
}

async function _appendLine(filePath: string, env: BusEnvelope): Promise<void> {
  validateEnvelope(env);
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  // O_APPEND atomic for <PIPE_BUF; one syscall per line.
  await fs.appendFile(filePath, JSON.stringify(env) + "\n", { flag: "a" });
}

export async function appendBroadcast(envelope: BusEnvelope): Promise<void> {
  await _appendLine(BROADCAST_PATH, envelope);
}

export async function appendTargeted(
  targetSessionId: string,
  envelope: BusEnvelope,
): Promise<void> {
  validateSessionId(targetSessionId);
  await _appendLine(path.join(INBOX_DIR, `${targetSessionId}.jsonl`), envelope);
}

export async function appendReply(
  senderSessionId: string,
  envelope: BusEnvelope,
): Promise<void> {
  validateSessionId(senderSessionId);
  const enriched: BusEnvelope = {
    ...envelope,
    mode: "reply",
    reply_from: envelope.reply_from ?? envelope.from,
  };
  await _appendLine(path.join(INBOX_DIR, `${senderSessionId}.jsonl`), enriched);
}

// Test-only path exports (avoid hardcoding in tests).
export const _paths = { BUS_ROOT, BROADCAST_PATH, INBOX_DIR };
