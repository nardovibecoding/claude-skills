// Tests for src/cli/send.ts — verb dispatch + envelope correctness.
// Uses BUS_HOME-equivalent: we redirect HOME via env then verify spool files.
//
// Strategy: spawn the CLI as a subprocess so import.meta.main fires; assert
// stdout {ok,msg_id}, exit code, and spool file contents.

import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const SEND = path.resolve(__dirname, "..", "src", "cli", "send.ts");

let tmpHome: string;

function run(
  args: string[],
  env: Record<string, string> = {},
): { code: number; out: string; err: string } {
  const r = spawnSync("bun", ["run", SEND, ...args], {
    encoding: "utf8",
    env: { ...process.env, HOME: tmpHome, ...env },
  });
  return {
    code: r.status ?? -1,
    out: r.stdout?.toString() ?? "",
    err: r.stderr?.toString() ?? "",
  };
}

beforeEach(() => {
  tmpHome = mkdtempSync(path.join(tmpdir(), "bus-cli-test-"));
  // Pre-create dirs the writer would create on demand (defensive).
  mkdirSync(path.join(tmpHome, ".claude", "bus", "inbox"), { recursive: true });
});

afterEach(() => {
  rmSync(tmpHome, { recursive: true, force: true });
});

describe("send.ts CLI", () => {
  test("T1 tell <name> writes mode=notify envelope to inbox/<sid>.jsonl", () => {
    // Arrange: pretend target session_id is a real-looking PID via env override.
    const targetSid = "99999";
    const r = run(["tell", "B", "hello B"], {
      BUS_NAME: "A",
      BUS_TARGET_SID: targetSid,
    });
    expect(r.code).toBe(0);
    const parsed = JSON.parse(r.out);
    expect(parsed.ok).toBe(true);
    expect(typeof parsed.msg_id).toBe("string");

    const inboxFile = path.join(
      tmpHome,
      ".claude",
      "bus",
      "inbox",
      `${targetSid}.jsonl`,
    );
    expect(existsSync(inboxFile)).toBe(true);
    const line = readFileSync(inboxFile, "utf8").trim().split("\n")[0]!;
    const env = JSON.parse(line);
    expect(env.mode).toBe("notify");
    expect(env.from).toBe("A");
    expect(env.to).toBe("B");
    expect(env.payload).toBe("hello B");
    expect(env.msg_id).toBe(parsed.msg_id);
  });

  test("T2 ask <name> writes mode=ask envelope", () => {
    const targetSid = "88888";
    const r = run(["ask", "B", "what's your status?"], {
      BUS_NAME: "A",
      BUS_TARGET_SID: targetSid,
    });
    expect(r.code).toBe(0);

    const inboxFile = path.join(
      tmpHome,
      ".claude",
      "bus",
      "inbox",
      `${targetSid}.jsonl`,
    );
    const env = JSON.parse(readFileSync(inboxFile, "utf8").trim());
    expect(env.mode).toBe("ask");
    expect(env.payload).toBe("what's your status?");
  });

  test("T3 all writes mode=notify envelope to all.jsonl with to='all'", () => {
    const r = run(["all", "broadcast text"], { BUS_NAME: "A" });
    expect(r.code).toBe(0);

    const allFile = path.join(tmpHome, ".claude", "bus", "all.jsonl");
    expect(existsSync(allFile)).toBe(true);
    const env = JSON.parse(readFileSync(allFile, "utf8").trim());
    expect(env.mode).toBe("notify");
    expect(env.to).toBe("all");
    expect(env.payload).toBe("broadcast text");
  });

  test("T4 unknown verb exits non-zero with stderr error", () => {
    const r = run(["frobnicate", "x"], { BUS_NAME: "A" });
    expect(r.code).not.toBe(0);
    expect(r.err).toContain("unknown verb");
  });

  test("T5 missing BUS_NAME exits non-zero", () => {
    // Strip BUS_NAME explicitly
    const r2 = spawnSync("bun", ["run", SEND, "all", "x"], {
      encoding: "utf8",
      env: { ...process.env, HOME: tmpHome, BUS_NAME: "" },
    });
    expect(r2.status).not.toBe(0);
    expect((r2.stderr ?? "").toString()).toContain("BUS_NAME");
  });

  test("T6 consensus verb writes mode=consensus to all.jsonl", () => {
    const r = run(["consensus", "Postgres or MySQL?"], { BUS_NAME: "A" });
    expect(r.code).toBe(0);
    const allFile = path.join(tmpHome, ".claude", "bus", "all.jsonl");
    const env = JSON.parse(readFileSync(allFile, "utf8").trim());
    expect(env.mode).toBe("consensus");
    expect(env.to).toBe("all");
  });

  test("T7 reply verb with numeric sid writes mode=reply + reply_from + in_reply_to to recipient inbox", () => {
    const recipientSid = "22222";
    const origMsgId = "11111-1234567890";
    const r = run(
      ["reply", recipientSid, origMsgId, "pong"],
      { BUS_NAME: "B" },
    );
    expect(r.code).toBe(0);
    const parsed = JSON.parse(r.out);
    expect(parsed.ok).toBe(true);
    expect(parsed.in_reply_to).toBe(origMsgId);

    const inboxFile = path.join(tmpHome, ".claude", "bus", "inbox", `${recipientSid}.jsonl`);
    expect(existsSync(inboxFile)).toBe(true);
    const env = JSON.parse(readFileSync(inboxFile, "utf8").trim());
    expect(env.mode).toBe("reply");
    expect(env.reply_from).toBe("B");
    expect(env.in_reply_to).toBe(origMsgId);
    expect(env.payload).toBe("pong");
    expect(env.from).toBe("B");
  });

  test("T8 reply with name target resolves via resolve_name.sh (registry)", () => {
    // Seed a registry entry for name "A" with session_id 11111.
    const busDir = path.join(tmpHome, ".claude", "bus");
    const registry = path.join(busDir, "registry.jsonl");
    const ts = new Date().toISOString();
    const { writeFileSync } = await import("node:fs");
    writeFileSync(registry, JSON.stringify({ name: "A", session_id: "11111", ts }) + "\n");

    const origMsgId = "99999-111";
    const r = run(["reply", "A", origMsgId, "hello A"], { BUS_NAME: "B" });
    expect(r.code).toBe(0);

    const inboxFile = path.join(busDir, "inbox", "11111.jsonl");
    expect(existsSync(inboxFile)).toBe(true);
    const env = JSON.parse(readFileSync(inboxFile, "utf8").trim());
    expect(env.mode).toBe("reply");
    expect(env.reply_from).toBe("B");
    expect(env.in_reply_to).toBe(origMsgId);
    expect(env.to).toBe("A");
  });

  test("T9 reply with numeric sid target passes through without registry lookup", () => {
    // No registry file exists — numeric sid must not trigger resolve_name.sh lookup.
    const recipientSid = "55555";
    const origMsgId = "44444-999";
    const r = run(["reply", recipientSid, origMsgId, "direct-sid-reply"], { BUS_NAME: "C" });
    // Should succeed even without registry present.
    expect(r.code).toBe(0);

    const inboxFile = path.join(tmpHome, ".claude", "bus", "inbox", `${recipientSid}.jsonl`);
    const env = JSON.parse(readFileSync(inboxFile, "utf8").trim());
    expect(env.mode).toBe("reply");
    expect(env.reply_from).toBe("C");
    expect(env.in_reply_to).toBe(origMsgId);
  });
});
