// Opt-in sentinel: presence of `~/.claude/bus/opted-in/<sessionId>` means the
// session has run /bus opt-in. Plugin reads this on every push attempt.
// Opt-in WRITE is owned by the skill (S4) — this module only reads + sweeps.
//
// Stale-sentinel sweep: kill -0 each PID; if dead, rm. Returns count cleaned.
// Semantics on EPERM (PID exists but owned by another user): treat as alive
// (better safe than wrong sweep) — covered in S2 §7 Q&A.

import { existsSync, readdirSync, unlinkSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const OPTED_IN_DIR = path.join(os.homedir(), ".claude", "bus", "opted-in");

export function isOptedIn(sessionId: string): boolean {
  if (!/^\d+$/.test(sessionId)) return false;
  return existsSync(path.join(OPTED_IN_DIR, sessionId));
}

export function cleanStaleSentinels(): number {
  if (!existsSync(OPTED_IN_DIR)) return 0;
  let cleaned = 0;
  for (const name of readdirSync(OPTED_IN_DIR)) {
    if (!/^\d+$/.test(name)) continue;
    const pid = Number(name);
    let alive = true;
    try {
      // process.kill(pid, 0): existence probe. Throws on dead PID.
      // EPERM (PID exists, not ours) → caught, treat as alive.
      process.kill(pid, 0);
    } catch (e) {
      const code = (e as NodeJS.ErrnoException).code;
      if (code === "ESRCH") alive = false;
      // EPERM, EINVAL, anything else → assume alive (don't sweep).
    }
    if (!alive) {
      try {
        unlinkSync(path.join(OPTED_IN_DIR, name));
        cleaned++;
      } catch {
        // race: another sweep got it first — fine.
      }
    }
  }
  return cleaned;
}

export const _paths = { OPTED_IN_DIR };
