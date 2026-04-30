import { describe, test, expect, beforeEach, afterAll } from "bun:test";
import { promises as fs } from "node:fs";
import path from "node:path";
import {
  appendBroadcast,
  appendTargeted,
  appendReply,
  _paths,
} from "../src/writer.js";
import type { BusEnvelope } from "../src/types.js";

const TEST_SID = "999991";
const TEST_SID_2 = "999992";
const TEST_SENDER = "999993";

const TEST_FILES = [
  _paths.BROADCAST_PATH,
  path.join(_paths.INBOX_DIR, `${TEST_SID}.jsonl`),
  path.join(_paths.INBOX_DIR, `${TEST_SID_2}.jsonl`),
  path.join(_paths.INBOX_DIR, `${TEST_SENDER}.jsonl`),
];

async function cleanup() {
  for (const f of TEST_FILES) {
    await fs.rm(f, { force: true });
  }
}

function baseEnv(overrides: Partial<BusEnvelope> = {}): BusEnvelope {
  return {
    msg_id: "test-msg-1",
    from: "A",
    from_session_id: TEST_SENDER,
    to: "all",
    mode: "notify",
    ts: "2026-04-30T15:20:00+08:00",
    payload: "hello",
    ...overrides,
  };
}

beforeEach(cleanup);
afterAll(cleanup);

describe("writer", () => {
  test("T1 appendBroadcast writes valid JSON to all.jsonl", async () => {
    await appendBroadcast(baseEnv());
    const exists = await Bun.file(_paths.BROADCAST_PATH).exists();
    expect(exists).toBe(true);
    const lines = (await fs.readFile(_paths.BROADCAST_PATH, "utf8"))
      .split("\n")
      .filter(Boolean);
    expect(lines.length).toBe(1);
    const parsed = JSON.parse(lines[0]);
    expect(parsed.msg_id).toBe("test-msg-1");
    expect(parsed.to).toBe("all");
    expect(parsed.mode).toBe("notify");
  });

  test("T2 appendTargeted writes to inbox/<sid>.jsonl per recipient", async () => {
    await appendTargeted(TEST_SID, baseEnv({ msg_id: "m-a", to: TEST_SID }));
    await appendTargeted(TEST_SID_2, baseEnv({ msg_id: "m-b", to: TEST_SID_2 }));
    const a = await fs.readFile(path.join(_paths.INBOX_DIR, `${TEST_SID}.jsonl`), "utf8");
    const b = await fs.readFile(path.join(_paths.INBOX_DIR, `${TEST_SID_2}.jsonl`), "utf8");
    expect(JSON.parse(a.trim()).msg_id).toBe("m-a");
    expect(JSON.parse(b.trim()).msg_id).toBe("m-b");
  });

  test("T3 appendReply sets reply_from + targets sender's inbox", async () => {
    await appendReply(
      TEST_SENDER,
      baseEnv({
        msg_id: "r-1",
        from: "B",
        from_session_id: "999994",
        to: TEST_SENDER,
        mode: "notify",
        in_reply_to: "orig-1",
      }),
    );
    const txt = await fs.readFile(path.join(_paths.INBOX_DIR, `${TEST_SENDER}.jsonl`), "utf8");
    const parsed = JSON.parse(txt.trim());
    expect(parsed.mode).toBe("reply");
    expect(parsed.reply_from).toBe("B");
    expect(parsed.in_reply_to).toBe("orig-1");
  });

  test("T4 schema validation rejects missing msg_id", async () => {
    const bad = baseEnv() as Partial<BusEnvelope>;
    delete bad.msg_id;
    await expect(appendBroadcast(bad as BusEnvelope)).rejects.toThrow(TypeError);
  });

  test("T5 mode validation rejects 'garbage'", async () => {
    const bad = baseEnv({ mode: "garbage" as unknown as BusEnvelope["mode"] });
    await expect(appendBroadcast(bad)).rejects.toThrow(TypeError);
  });

  test("T6 directory-traversal protection rejects '../etc/passwd'", async () => {
    await expect(appendTargeted("../etc/passwd", baseEnv())).rejects.toThrow(TypeError);
    await expect(appendTargeted("abc", baseEnv())).rejects.toThrow(TypeError);
    await expect(appendTargeted("123/456", baseEnv())).rejects.toThrow(TypeError);
  });

  test("T7 concurrent appends land as 10 distinct lines (atomicity)", async () => {
    const envs = Array.from({ length: 10 }, (_, i) =>
      baseEnv({ msg_id: `c-${i}`, payload: `body-${i}` }),
    );
    await Promise.all(envs.map((e) => appendBroadcast(e)));
    const lines = (await fs.readFile(_paths.BROADCAST_PATH, "utf8"))
      .split("\n")
      .filter(Boolean);
    expect(lines.length).toBe(10);
    const ids = new Set(lines.map((l) => JSON.parse(l).msg_id));
    expect(ids.size).toBe(10);
    // every line is parseable JSON => no torn writes
    for (const l of lines) expect(() => JSON.parse(l)).not.toThrow();
  });
});
