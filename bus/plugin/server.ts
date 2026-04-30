#!/usr/bin/env bun
/**
 * /bus v2 channel plugin — MCP server skeleton (S2).
 *
 * Connects via stdio as channel `plugin:bus@local`, registers the channel
 * capability, and exposes a no-op `pushEvent` placeholder. S3 will wire the
 * spool tail (~/.claude/bus/inbox/<session_id>.jsonl) and actual notification
 * delivery via `notifications/claude/channel`.
 *
 * Reference: anthropics/claude-plugins-official external_plugins/fakechat
 * (commit @main as of 2026-04-30): server name is plain string, capabilities
 * are { tools: {}, experimental: { 'claude/channel': {} } }, transport is
 * StdioServerTransport. We mirror that shape.
 *
 * Diagnostic output: stderr ONLY. stdout is the JSON-RPC channel.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { resolveSessionId } from "./src/session.js";
import { isOptedIn, cleanStaleSentinels } from "./src/sentinel.js";
import type { BusEnvelope } from "./src/types.js";

const SERVER_NAME = "plugin:bus@local";
const SERVER_VERSION = "0.1.0";

function log(action: string, kvs: Record<string, string | number> = {}): void {
  const parts = Object.entries(kvs).map(([k, v]) => `${k}=${v}`);
  process.stderr.write(`[bus] ${action} ${parts.join(" ")}\n`);
}

const sessionId = resolveSessionId();
log("plugin attached", { session_id: sessionId });

// Best-effort sweep on startup — costs <5ms, prevents cruft accumulation.
try {
  const swept = cleanStaleSentinels();
  if (swept > 0) log("startup sweep", { stale_cleaned: swept });
} catch (e) {
  log("startup sweep failed", { err: String((e as Error).message) });
}

// S3 will replace this body. For now: pure no-op so the symbol exists and
// downstream wiring (spool tail) has its push target. Exported for testing
// and so S3's diff is one-file.
export function pushEvent(_envelope: BusEnvelope): void {
  // intentionally empty in S2
}

const mcp = new Server(
  { name: SERVER_NAME, version: SERVER_VERSION },
  {
    capabilities: { tools: {}, experimental: { "claude/channel": {} } },
    instructions:
      "Inter-session message bus. Other claude sessions can send notifications to this session via /bus skill. Messages arrive as channel events when this session has opted-in (sentinel at ~/.claude/bus/opted-in/<session_id>).",
  },
);

// Minimal tool surface for S2. /bus skill itself owns the user-facing verbs;
// the MCP layer just needs to be a valid server. S3 may add tools if needed
// for delivery; for now we expose a status probe.
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
    };
    return { content: [{ type: "text", text: JSON.stringify(status) }] };
  }
  return {
    content: [{ type: "text", text: `unknown tool: ${req.params.name}` }],
    isError: true,
  };
});

// Graceful shutdown. MCP transport's close() flushes any pending frames.
function shutdown(sig: string): void {
  log("shutdown", { signal: sig });
  // Server.close() is async but we exit synchronously — best-effort.
  void mcp.close().finally(() => process.exit(0));
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));

await mcp.connect(new StdioServerTransport());
log("mcp connected", { transport: "stdio" });
