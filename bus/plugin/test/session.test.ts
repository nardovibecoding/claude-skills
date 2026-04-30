// Tests for src/session.ts and src/sentinel.ts.
import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { mkdirSync, writeFileSync, existsSync, rmSync } from "node:fs";
import path from "node:path";
import os from "node:os";
import {
  resolveSessionId,
  _resetSessionIdCacheForTests,
} from "../src/session.js";
import { isOptedIn, cleanStaleSentinels, _paths } from "../src/sentinel.js";

describe("resolveSessionId", () => {
  beforeEach(() => _resetSessionIdCacheForTests());

  test("returns digit-only string", () => {
    const sid = resolveSessionId();
    expect(sid).toMatch(/^\d+$/);
  });

  test("is cached across calls", () => {
    const a = resolveSessionId();
    const b = resolveSessionId();
    expect(a).toBe(b);
  });
});

describe("isOptedIn / cleanStaleSentinels", () => {
  // Use real opted-in dir; clean up only files we create.
  const dir = _paths.OPTED_IN_DIR;
  const created: string[] = [];

  beforeEach(() => {
    mkdirSync(dir, { recursive: true });
  });

  afterEach(() => {
    for (const f of created) {
      try { rmSync(f); } catch {}
    }
    created.length = 0;
  });

  test("isOptedIn false when sentinel missing", () => {
    expect(isOptedIn("999999991")).toBe(false);
  });

  test("isOptedIn true when sentinel present", () => {
    const sid = "999999992";
    const f = path.join(dir, sid);
    writeFileSync(f, "");
    created.push(f);
    expect(isOptedIn(sid)).toBe(true);
  });

  test("isOptedIn rejects non-numeric session ids", () => {
    expect(isOptedIn("../etc/passwd")).toBe(false);
    expect(isOptedIn("abc")).toBe(false);
  });

  test("cleanStaleSentinels removes dead-PID sentinel, preserves live one", () => {
    const deadPid = "999999993"; // not a real PID
    const liveSid = String(process.pid); // definitely alive
    const fDead = path.join(dir, deadPid);
    const fLive = path.join(dir, liveSid);
    writeFileSync(fDead, "");
    writeFileSync(fLive, "");
    created.push(fDead, fLive);

    const swept = cleanStaleSentinels();
    expect(swept).toBeGreaterThanOrEqual(1);
    expect(existsSync(fDead)).toBe(false);
    expect(existsSync(fLive)).toBe(true);
  });
});
