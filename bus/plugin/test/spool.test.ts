import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, writeFileSync, appendFileSync, truncateSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { tailSpool } from "../src/spool.js";
import { SeenSet } from "../src/dedupe.js";

const SETTLE_MS = 200; // > DEBOUNCE_MS (50) + FSEvents coalesce slack

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

let dir: string;
let file: string;

beforeEach(() => {
  dir = mkdtempSync(path.join(tmpdir(), "bus-spool-"));
  file = path.join(dir, "spool.jsonl");
  writeFileSync(file, ""); // start empty
});

afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe("tailSpool", () => {
  test("T1 emits each newline-terminated line written line-by-line", async () => {
    const lines: string[] = [];
    const h = tailSpool(file, (l) => lines.push(l));
    await sleep(SETTLE_MS);
    appendFileSync(file, "alpha\n");
    await sleep(SETTLE_MS);
    appendFileSync(file, "bravo\n");
    await sleep(SETTLE_MS);
    appendFileSync(file, "charlie\n");
    await sleep(SETTLE_MS);
    h.stop();
    expect(lines).toEqual(["alpha", "bravo", "charlie"]);
  });

  test("T2 buffers partial lines until newline arrives", async () => {
    const lines: string[] = [];
    const h = tailSpool(file, (l) => lines.push(l));
    await sleep(SETTLE_MS);
    appendFileSync(file, "abc");
    await sleep(SETTLE_MS);
    expect(lines).toEqual([]);
    appendFileSync(file, "def\n");
    await sleep(SETTLE_MS);
    h.stop();
    expect(lines).toEqual(["abcdef"]);
  });

  test("T3 handles truncation: re-reads from start after size shrinks", async () => {
    const lines: string[] = [];
    appendFileSync(file, "one\ntwo\nthree\n");
    const h = tailSpool(file, (l) => lines.push(l));
    await sleep(SETTLE_MS);
    appendFileSync(file, "four\nfive\n");
    await sleep(SETTLE_MS);
    truncateSync(file, 0);
    await sleep(SETTLE_MS);
    appendFileSync(file, "six\nseven\n");
    await sleep(SETTLE_MS);
    h.stop();
    // tail starts at EOF — pre-existing one/two/three NOT emitted.
    // four/five emitted, then truncation reset, then six/seven emitted.
    expect(lines).toEqual(["four", "five", "six", "seven"]);
  });

  test("T4 stop() prevents further emissions", async () => {
    const lines: string[] = [];
    const h = tailSpool(file, (l) => lines.push(l));
    await sleep(SETTLE_MS);
    appendFileSync(file, "early\n");
    await sleep(SETTLE_MS);
    h.stop();
    appendFileSync(file, "after-stop\n");
    await sleep(SETTLE_MS);
    expect(lines).toEqual(["early"]);
  });
});

describe("SeenSet", () => {
  test("T5 evicts oldest beyond cap", () => {
    const s = new SeenSet(3);
    s.add("a"); s.add("b"); s.add("c");
    expect(s.size).toBe(3);
    s.add("d");
    expect(s.size).toBe(3);
    expect(s.has("a")).toBe(false); // oldest evicted
    expect(s.has("b")).toBe(true);
    expect(s.has("c")).toBe(true);
    expect(s.has("d")).toBe(true);
  });

  test("T6 has returns true after add; false otherwise", () => {
    const s = new SeenSet();
    expect(s.has("x")).toBe(false);
    s.add("x");
    expect(s.has("x")).toBe(true);
    expect(s.has("y")).toBe(false);
  });

  test("T7 re-adding existing id moves it to most-recent (LRU touch)", () => {
    const s = new SeenSet(3);
    s.add("a"); s.add("b"); s.add("c");
    s.add("a"); // touch a — now b is oldest
    s.add("d");
    expect(s.has("b")).toBe(false); // b evicted
    expect(s.has("a")).toBe(true);
    expect(s.has("c")).toBe(true);
    expect(s.has("d")).toBe(true);
  });

  test("T8 cap < 1 throws", () => {
    expect(() => new SeenSet(0)).toThrow();
  });
});
