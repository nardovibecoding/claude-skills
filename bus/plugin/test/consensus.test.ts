// consensus.test.ts -- Unit tests for consensus envelope schema + vote verb.
//
// T1: mode=consensus requires round + kind + consensus_id; missing -> reject
// T2: mode=tell (non-consensus) with round set -> reject
// T3: vote verb parseArgs returns correct shape
// T4: verdict math -- 4/5 agree (80%) -> CONSENSUS; 3/5 agree (60%) -> NO-CONSENSUS
// T5: 75% edge -- 3/4 agree (75%) -> CONSENSUS; 2/3 agree (66%) -> NO-CONSENSUS
// T6: round=0 valid only for kind=verdict; round=0 + kind=question -> reject

import { describe, test, expect, beforeEach, afterAll } from "bun:test";
import { promises as fs } from "node:fs";
import path from "node:path";
import {
  appendBroadcast,
  _paths,
} from "../src/writer.js";
import type { BusEnvelope } from "../src/types.js";
import { parseArgs } from "../src/cli/send.js";

// --- Schema validation tests (via appendBroadcast which calls validateEnvelope) ---

const TEST_BROADCAST_FILE = _paths.BROADCAST_PATH;

async function cleanupBroadcast() {
  await fs.rm(TEST_BROADCAST_FILE, { force: true });
}

function baseConsensusEnv(overrides: Partial<BusEnvelope> = {}): BusEnvelope {
  return {
    msg_id: "c-test-1",
    from: "A",
    from_session_id: "99999",
    to: "all",
    mode: "consensus",
    ts: "2026-04-30T15:00:00+08:00",
    payload: "should we deploy?",
    round: 1,
    kind: "question",
    consensus_id: "99999-c-1746000000",
    ...overrides,
  };
}

beforeEach(cleanupBroadcast);
afterAll(cleanupBroadcast);

describe("consensus schema validation", () => {
  test("T1a valid consensus envelope (question) is accepted", async () => {
    await expect(appendBroadcast(baseConsensusEnv())).resolves.toBeUndefined();
  });

  test("T1b mode=consensus missing round -> reject", async () => {
    const env = baseConsensusEnv();
    delete (env as Partial<BusEnvelope>).round;
    await expect(appendBroadcast(env)).rejects.toThrow(/mode=consensus requires field: round/);
  });

  test("T1c mode=consensus missing kind -> reject", async () => {
    const env = baseConsensusEnv();
    delete (env as Partial<BusEnvelope>).kind;
    await expect(appendBroadcast(env)).rejects.toThrow(/mode=consensus requires field: kind/);
  });

  test("T1d mode=consensus missing consensus_id -> reject", async () => {
    const env = baseConsensusEnv();
    delete (env as Partial<BusEnvelope>).consensus_id;
    await expect(appendBroadcast(env)).rejects.toThrow(/mode=consensus requires field: consensus_id/);
  });

  test("T2 mode=notify with round set -> reject (consensus fields forbidden on non-consensus)", async () => {
    const env: BusEnvelope = {
      msg_id: "tell-1",
      from: "A",
      from_session_id: "99999",
      to: "B",
      mode: "notify",
      ts: "2026-04-30T15:00:00+08:00",
      payload: "hello",
      round: 1,  // forbidden on non-consensus mode
    };
    await expect(appendBroadcast(env)).rejects.toThrow(/round field only valid for mode=consensus/);
  });

  test("T6a round=0 valid for kind=verdict", async () => {
    const env = baseConsensusEnv({ round: 0, kind: "verdict", payload: "CONSENSUS" });
    await expect(appendBroadcast(env)).resolves.toBeUndefined();
  });

  test("T6b round=0 + kind=question -> reject", async () => {
    const env = baseConsensusEnv({ round: 0, kind: "question" });
    await expect(appendBroadcast(env)).rejects.toThrow(/round=0 only valid for kind=verdict/);
  });

  test("T6c kind=verdict + round=1 -> reject (verdict must use round=0)", async () => {
    const env = baseConsensusEnv({ round: 1, kind: "verdict" });
    await expect(appendBroadcast(env)).rejects.toThrow(/kind=verdict must use round=0/);
  });
});

// --- parseArgs vote verb tests ---

describe("send.ts vote verb", () => {
  test("T3a vote parseArgs returns correct shape", () => {
    const result = parseArgs(["vote", "99999-c-1746000000", "1", "agree", "clear winner"]);
    expect(result.verb).toBe("vote");
    if (result.verb !== "vote") throw new Error("guard");
    expect(result.consensusId).toBe("99999-c-1746000000");
    expect(result.round).toBe(1);
    expect(result.stance).toBe("agree");
    expect(result.reason).toBe("clear winner");
    expect(result.payload).toBe("agree: clear winner");
  });

  test("T3b vote parseArgs with disagree", () => {
    const result = parseArgs(["vote", "88888-c-1000000", "2", "disagree", "too risky"]);
    expect(result.verb).toBe("vote");
    if (result.verb !== "vote") throw new Error("guard");
    expect(result.stance).toBe("disagree");
    expect(result.payload).toBe("disagree: too risky");
  });

  test("T3c vote with invalid round -> subprocess exits non-zero", () => {
    const { spawnSync } = require("node:child_process");
    const SEND = require("node:path").resolve(__dirname, "..", "src", "cli", "send.ts");
    const r = spawnSync("bun", ["run", SEND, "vote", "99999-c-123", "4", "agree", "reason"], {
      encoding: "utf8",
      env: { ...process.env, BUS_NAME: "A" },
    });
    expect(r.status).not.toBe(0);
    expect((r.stderr ?? "").toString()).toContain("vote round must be 1-3");
  });

  test("T3d vote with invalid stance -> subprocess exits non-zero", () => {
    const { spawnSync } = require("node:child_process");
    const SEND = require("node:path").resolve(__dirname, "..", "src", "cli", "send.ts");
    const r = spawnSync("bun", ["run", SEND, "vote", "99999-c-123", "1", "maybe", "reason"], {
      encoding: "utf8",
      env: { ...process.env, BUS_NAME: "A" },
    });
    expect(r.status).not.toBe(0);
    expect((r.stderr ?? "").toString()).toContain("stance must be agree|disagree");
  });
});

// --- Verdict math tests (pure computation, no I/O) ---

// Mirrors the integer math in consensus.sh: agree*100/total >= 75
function thresholdMet(agree: number, total: number): boolean {
  if (total === 0) return false;
  return Math.floor((agree * 100) / total) >= 75;
}

describe("verdict math", () => {
  test("T4a 4/5 agree (80%) -> CONSENSUS", () => {
    expect(thresholdMet(4, 5)).toBe(true);
  });

  test("T4b 3/5 agree (60%) -> NO-CONSENSUS", () => {
    expect(thresholdMet(3, 5)).toBe(false);
  });

  test("T5a 3/4 agree (75%) -> CONSENSUS (edge case per spec)", () => {
    expect(thresholdMet(3, 4)).toBe(true);
  });

  test("T5b 2/3 agree (66%) -> NO-CONSENSUS", () => {
    expect(thresholdMet(2, 3)).toBe(false);
  });

  test("T5c 0/5 agree -> NO-CONSENSUS (zero peers)", () => {
    expect(thresholdMet(0, 5)).toBe(false);
  });

  test("T5d total=0 -> NO-CONSENSUS (no peers responded)", () => {
    expect(thresholdMet(0, 0)).toBe(false);
  });
});
