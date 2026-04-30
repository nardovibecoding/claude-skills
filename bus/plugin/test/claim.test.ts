/**
 * claim.test.ts — unit tests for /radio claim/release shell scripts.
 * Tests run the actual bash scripts with BUS_FORCE_SID and BUS_DIR overrides
 * so they operate on a temp directory and never touch the real ~/.claude/bus.
 */

import { describe, test, expect, beforeAll, afterAll, beforeEach } from "bun:test";
import { mkdtempSync, rmSync, mkdirSync, existsSync, readFileSync, writeFileSync, realpathSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { spawnSync } from "child_process";

const SCRIPTS_DIR = join(import.meta.dir, "../../scripts");
const CLAIM_SH = join(SCRIPTS_DIR, "claim.sh");
const RELEASE_SH = join(SCRIPTS_DIR, "release.sh");

let TMP_DIR: string;
let CANARY_FILE: string;

function sha256(s: string): string {
  const { createHash } = require("crypto");
  return createHash("sha256").update(s).digest("hex");
}

function runScript(
  script: string,
  args: string[],
  env: Record<string, string> = {},
  sid: string = "11111"
): { stdout: string; stderr: string; status: number } {
  const r = spawnSync("bash", [script, ...args], {
    env: {
      ...process.env,
      BUS_DIR: TMP_DIR,
      BUS_FORCE_SID: sid,
      BUS_NAME: "TEST",
      PATH: process.env.PATH ?? "/usr/local/bin:/usr/bin:/bin",
      ...env,
    },
    encoding: "utf8",
    timeout: 10000,
  });
  return {
    stdout: r.stdout ?? "",
    stderr: r.stderr ?? "",
    status: r.status ?? 1,
  };
}

beforeAll(() => {
  TMP_DIR = mkdtempSync(join(tmpdir(), "bus-claim-test-"));
  mkdirSync(join(TMP_DIR, "claims"), { recursive: true });
  // Create canary file so realpath succeeds.
  CANARY_FILE = join(TMP_DIR, "canary.txt");
  writeFileSync(CANARY_FILE, "canary");
});

afterAll(() => {
  try { rmSync(TMP_DIR, { recursive: true, force: true }); } catch { /* ok */ }
});

beforeEach(() => {
  // Wipe claims between tests.
  const claimsDir = join(TMP_DIR, "claims");
  if (existsSync(claimsDir)) {
    rmSync(claimsDir, { recursive: true, force: true });
    mkdirSync(claimsDir, { recursive: true });
  }
});

describe("claim.sh", () => {
  test("T1: claim writes claim file with correct JSON shape (6 required fields)", () => {
    const r = runScript(CLAIM_SH, [CANARY_FILE]);
    expect(r.status).toBe(0);

    const resp = JSON.parse(r.stdout.trim());
    expect(resp.ok).toBe(true);
    expect(resp.sha).toBeTruthy();
    expect(resp.path).toBe(CANARY_FILE);

    // Verify claim file on disk.
    const claimFilePath = join(TMP_DIR, "claims", resp.sha);
    expect(existsSync(claimFilePath)).toBe(true);

    const claim = JSON.parse(readFileSync(claimFilePath, "utf8"));
    // Must have all 6 required fields.
    expect(typeof claim.path).toBe("string");
    expect(typeof claim.sha).toBe("string");
    expect(typeof claim.session_id).toBe("number");
    expect(typeof claim.name).toBe("string");
    expect(typeof claim.ts).toBe("string");
    expect(typeof claim.host).toBe("string");
    expect(claim.path).toBe(CANARY_FILE);
    expect(claim.session_id).toBe(11111);
  });

  test("T2: claim same path twice from same session = idempotent (ok:true, refreshed:true)", () => {
    const r1 = runScript(CLAIM_SH, [CANARY_FILE], {}, "22222");
    expect(r1.status).toBe(0);
    const resp1 = JSON.parse(r1.stdout.trim());
    expect(resp1.ok).toBe(true);

    // Second claim from same session.
    const r2 = runScript(CLAIM_SH, [CANARY_FILE], {}, "22222");
    expect(r2.status).toBe(0);
    const resp2 = JSON.parse(r2.stdout.trim());
    expect(resp2.ok).toBe(true);
    expect(resp2.refreshed).toBe(true);
  });

  test("T3: claim same path from different session = fails with already_claimed", () => {
    // Session A claims.
    const rA = runScript(CLAIM_SH, [CANARY_FILE], {}, "33333");
    expect(rA.status).toBe(0);

    // Simulate session A is alive by using a real PID (our own process).
    // We'll write a claim file with session_id = current PID so kill -0 passes.
    const resp = JSON.parse(rA.stdout.trim());
    const claimFilePath = join(TMP_DIR, "claims", resp.sha);
    const claim = JSON.parse(readFileSync(claimFilePath, "utf8"));
    // Patch session_id to our own PID so it's "alive".
    claim.session_id = process.pid;
    writeFileSync(claimFilePath, JSON.stringify(claim));

    // Session B tries to claim.
    const rB = runScript(CLAIM_SH, [CANARY_FILE], {}, "44444");
    expect(rB.status).toBe(1);
    const respB = JSON.parse(rB.stdout.trim());
    expect(respB.ok).toBe(false);
    expect(respB.reason).toBe("already_claimed");
    expect(typeof respB.by).toBe("string");
    expect(typeof respB.at).toBe("string");
  });

  test("T6: sha256 of canary path matches expected value (deterministic)", () => {
    const r = runScript(CLAIM_SH, [CANARY_FILE]);
    expect(r.status).toBe(0);
    const resp = JSON.parse(r.stdout.trim());
    const expectedSha = sha256(CANARY_FILE);
    expect(resp.sha).toBe(expectedSha);
  });
});

describe("release.sh", () => {
  test("T4: release removes claim file", () => {
    // Claim first.
    const rC = runScript(CLAIM_SH, [CANARY_FILE], {}, "55555");
    expect(rC.status).toBe(0);
    const resp = JSON.parse(rC.stdout.trim());
    const claimFilePath = join(TMP_DIR, "claims", resp.sha);
    expect(existsSync(claimFilePath)).toBe(true);

    // Release.
    const rR = runScript(RELEASE_SH, [CANARY_FILE], {}, "55555");
    expect(rR.status).toBe(0);
    const respR = JSON.parse(rR.stdout.trim());
    expect(respR.ok).toBe(true);
    expect(respR.released).toContain(CANARY_FILE);

    // Claim file must be gone.
    expect(existsSync(claimFilePath)).toBe(false);
  });

  test("T5: release of foreign claim fails without --force", () => {
    // Session A claims with a real PID so it's alive.
    const r = runScript(CLAIM_SH, [CANARY_FILE], {}, "66666");
    expect(r.status).toBe(0);
    const resp = JSON.parse(r.stdout.trim());
    const claimFilePath = join(TMP_DIR, "claims", resp.sha);

    // Patch to real PID.
    const claim = JSON.parse(readFileSync(claimFilePath, "utf8"));
    claim.session_id = process.pid;
    writeFileSync(claimFilePath, JSON.stringify(claim));

    // Session B tries to release.
    const rB = runScript(RELEASE_SH, [CANARY_FILE], {}, "77777");
    expect(rB.status).toBe(1);
    const respB = JSON.parse(rB.stdout.trim());
    expect(respB.ok).toBe(false);
    expect(respB.reason).toBe("not_own_claim");
  });
});
