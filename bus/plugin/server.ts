#!/usr/bin/env bun
/**
 * /bus v2 channel plugin — MCP server (S3 = wire push pipeline).
 *
 * Connects via stdio as channel `plugin:bus@local`. On startup:
 *   - resolve session_id from parent-process walk (claude PID)
 *   - sweep stale opt-in sentinels (best-effort)
 *   - check sentinel for THIS session_id:
 *       absent → log "not opted in, idle"; do not tail anything (zero CPU)
 *       present → tail BOTH ~/.claude/bus/all.jsonl (broadcast) and
 *                 ~/.claude/bus/inbox/<session_id>.jsonl (targeted)
 *   - for each emitted line: parse envelope, skip own messages (own
 *     from_session_id), skip duplicates (msg_id LRU dedupe), push to Claude
 *     via mcp.notification({ method: 'notifications/claude/channel', ... }).
 *
 * Reference: anthropics/claude-plugins-official external_plugins/fakechat
 * (server.ts:136-145) + telegram (server.ts:404-425). SDK signature:
 * Server.notification(notification, options?): Promise<void>
 * (node_modules/@modelcontextprotocol/sdk/dist/esm/shared/protocol.d.ts:383).
 *
 * Re-check sentinel? NO. Opt-in is one-way; sentinel checked at startup only.
 * /bus join after plugin started in idle mode = restart claude session
 * required (documented as OI-S3-1).
 *
 * Diagnostic output: stderr ONLY. stdout is the JSON-RPC channel.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import path from "node:path";
import os from "node:os";
import { resolveSessionId } from "./src/session.js";
import { isOptedIn, cleanStaleSentinels } from "./src/sentinel.js";
import { tailSpool, type SpoolHandle } from "./src/spool.js";
import { SeenSet } from "./src/dedupe.js";
import { type BusEnvelope, BUS_MODES, REQUIRED_KEYS } from "./src/types.js";

const SERVER_NAME = "plugin:bus@local";
const SERVER_VERSION = "0.1.0";

const BUS_ROOT = path.join(os.homedir(), ".claude", "bus");
const BROADCAST_PATH = path.join(BUS_ROOT, "all.jsonl");
const INBOX_DIR = path.join(BUS_ROOT, "inbox");

function log(action: string, kvs: Record<string, string | number> = {}): void {
  const parts = Object.entries(kvs).map(([k, v]) => `${k}=${v}`);
  process.stderr.write(`[bus] ${action} ${parts.join(" ")}\n`);
}

const sessionId = resolveSessionId();
log("plugin attached", { session_id: sessionId });

try {
  const swept = cleanStaleSentinels();
  if (swept > 0) log("startup sweep", { stale_cleaned: swept });
} catch (e) {
  log("startup sweep failed", { err: String((e as Error).message) });
}

const seen = new SeenSet(1000);
const tails: SpoolHandle[] = [];

const mcp = new Server(
  { name: SERVER_NAME, version: SERVER_VERSION },
  {
    capabilities: { tools: {}, experimental: { "claude/channel": {} } },
    instructions:
      "Inter-session message bus. Other claude sessions can send notifications to this session via /bus skill. Messages arrive as channel events when this session has opted-in (sentinel at ~/.claude/bus/opted-in/<session_id>).",
  },
);

function parseEnvelope(line: string): BusEnvelope | null {
  let env: unknown;
  try {
    env = JSON.parse(line);
  } catch {
    return null;
  }
  if (env === null || typeof env !== "object") return null;
  const e = env as Record<string, unknown>;
  for (const k of REQUIRED_KEYS) {
    if (typeof e[k] !== "string" || (e[k] as string).length === 0) return null;
  }
  if (!BUS_MODES.has(e.mode as BusEnvelope["mode"])) return null;
  return e as unknown as BusEnvelope;
}

export function pushEvent(envelope: BusEnvelope): void {
  if (envelope.from_session_id === sessionId) return; // never push own writes
  if (seen.has(envelope.msg_id)) return;
  seen.add(envelope.msg_id);
  const meta: Record<string, string> = {
    chat_id: "bus",
    message_id: envelope.msg_id,
    user: envelope.from,
    user_id: envelope.from_session_id,
    ts: envelope.ts,
    mode: envelope.mode,
    to: envelope.to,
  };
  if (envelope.in_reply_to) meta.in_reply_to = envelope.in_reply_to;
  if (envelope.reply_from) meta.reply_from = envelope.reply_from;
  void mcp
    .notification({
      method: "notifications/claude/channel",
      params: { content: envelope.payload, meta },
    })
    .catch((e: Error) => {
      log("push failed", { msg_id: envelope.msg_id, err: e.message });
    });
  log("push", {
    msg_id: envelope.msg_id,
    from: envelope.from,
    to: envelope.to,
    mode: envelope.mode,
  });
}

function onLine(source: string, line: string): void {
  const env = parseEnvelope(line);
  if (!env) {
    log("malformed envelope", { source, head: line.slice(0, 40) });
    return;
  }
  pushEvent(env);
}

function startTails(): void {
  const inboxPath = path.join(INBOX_DIR, `${sessionId}.jsonl`);
  tails.push(tailSpool(BROADCAST_PATH, (l) => onLine("all", l)));
  tails.push(tailSpool(inboxPath, (l) => onLine("inbox", l)));
  log("tails started", { broadcast: BROADCAST_PATH, inbox: inboxPath });
}

if (isOptedIn(sessionId)) {
  startTails();
} else {
  log("not opted in, idle", { session_id: sessionId });
}

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "bus_status",
      description: "Probe /bus plugin status (session_id, opted-in flag).",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
    },
  ],
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === "bus_status") {
    const status = {
      session_id: sessionId,
      opted_in: isOptedIn(sessionId),
      version: SERVER_VERSION,
      tails_active: tails.length,
      seen_size: seen.size,
    };
    return { content: [{ type: "text", text: JSON.stringify(status) }] };
  }
  return {
    content: [{ type: "text", text: `unknown tool: ${req.params.name}` }],
    isError: true,
  };
});

function shutdown(sig: string): void {
  log("shutdown", { signal: sig });
  for (const t of tails) {
    try { t.stop(); } catch { /* ignore */ }
  }
  void mcp.close().finally(() => process.exit(0));
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));

await mcp.connect(new StdioServerTransport());
log("mcp connected", { transport: "stdio" });
