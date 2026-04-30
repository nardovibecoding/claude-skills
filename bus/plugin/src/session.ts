// Session ID resolver for /bus v2 plugin.
// Walks the parent-process chain via `ps -p <pid> -o ppid=,command=` until
// it finds the first ancestor whose command is exactly `claude` (the binary
// itself, not `wet claude`, not `/path/to/claude`, not `bash`). That PID is
// the session_id we use as the routing key.
//
// Falls back to process.ppid with a stderr warning if the walk fails (ps
// missing, permission error, no `claude` ancestor within depth limit).
//
// Result is cached on first call — session id never changes for the lifetime
// of a single plugin process.

import { spawnSync } from "node:child_process";

const MAX_DEPTH = 16;

let _cached: string | null = null;

function readPpidAndCmd(pid: number): { ppid: number; cmd: string } | null {
  // ps -o ppid=,command= prints "  PPID COMMAND..." with leading whitespace.
  const r = spawnSync("ps", ["-p", String(pid), "-o", "ppid=,command="], {
    encoding: "utf8",
  });
  if (r.status !== 0 || !r.stdout) return null;
  const line = r.stdout.trim();
  if (!line) return null;
  const m = line.match(/^\s*(\d+)\s+(.*)$/);
  if (!m) return null;
  return { ppid: Number(m[1]), cmd: m[2] };
}

function basenameOfArgv0(cmd: string): string {
  // command= returns "argv0 arg1 arg2..." — split on first whitespace, then
  // basename the executable. Quoted paths are rare on macOS for `claude`.
  const argv0 = cmd.split(/\s+/, 1)[0] ?? "";
  const slash = argv0.lastIndexOf("/");
  return slash >= 0 ? argv0.slice(slash + 1) : argv0;
}

export function resolveSessionId(): string {
  if (_cached !== null) return _cached;

  let pid = process.ppid; // start one above plugin process
  for (let depth = 0; depth < MAX_DEPTH; depth++) {
    const info = readPpidAndCmd(pid);
    if (!info) break;
    const exe = basenameOfArgv0(info.cmd);
    if (exe === "claude") {
      _cached = String(pid);
      return _cached;
    }
    if (info.ppid <= 1) break; // hit launchd/init
    pid = info.ppid;
  }

  // Fallback: use immediate parent PID, warn loudly.
  const fallback = String(process.ppid);
  process.stderr.write(
    `[bus] WARN session-id resolve failed; falling back to ppid=${fallback}\n`,
  );
  _cached = fallback;
  return _cached;
}

// Test-only: reset cache between unit tests.
export function _resetSessionIdCacheForTests(): void {
  _cached = null;
}
