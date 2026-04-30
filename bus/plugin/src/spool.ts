// Event-driven spool tail for /bus v2 plugin (S3).
//
// Design:
// - fs.watch on the file's parent dir (macOS FSEvents). Watching the file
//   itself drops events on rename/replace; watching the dir survives rotate.
// - On any change touching our target basename: stat → read [offset..size).
// - Track byte offset in-memory only (restart re-tails from EOF of current
//   file at startup; this is intentional — plugin starts at "now", not "all
//   history", so a /bus join mid-traffic doesn't replay the backlog).
// - Truncation detection: if stat.size < offset → reset offset to 0 and
//   re-read; dedupe (S3 dedupe.ts) absorbs any re-emit.
// - Partial-line buffering: split on \n; keep trailing partial in memory;
//   emit only newline-terminated lines.
// - Debounce: coalesce rapid FSEvents bursts into one read pass via a 50ms
//   trailing-edge timer.
//
// Idle CPU: 0% — fs.watch is event-driven (kqueue/FSEvents), no polling.

import { existsSync, statSync, openSync, readSync, closeSync, watch } from "node:fs";
import path from "node:path";

export interface SpoolHandle {
  stop(): void;
}

const DEBOUNCE_MS = 50;

export function tailSpool(
  filePath: string,
  onLine: (line: string) => void,
): SpoolHandle {
  const dir = path.dirname(filePath);
  const base = path.basename(filePath);
  let offset = 0;
  let buffer = "";
  let stopped = false;
  let pending: ReturnType<typeof setTimeout> | null = null;

  // Start at end-of-current-file: we want "from now" semantics.
  if (existsSync(filePath)) {
    try {
      offset = statSync(filePath).size;
    } catch {
      offset = 0;
    }
  }

  function drain(): void {
    if (stopped) return;
    if (!existsSync(filePath)) {
      // File gone — reset, wait for re-creation event.
      offset = 0;
      buffer = "";
      return;
    }
    let size: number;
    try {
      size = statSync(filePath).size;
    } catch {
      return;
    }
    if (size < offset) {
      // Truncation / rotation. Reset offset; dedupe absorbs replay.
      offset = 0;
      buffer = "";
    }
    if (size === offset) return;
    let fd: number;
    try {
      fd = openSync(filePath, "r");
    } catch {
      return;
    }
    try {
      const len = size - offset;
      const buf = Buffer.alloc(len);
      const read = readSync(fd, buf, 0, len, offset);
      offset += read;
      buffer += buf.subarray(0, read).toString("utf8");
    } finally {
      try { closeSync(fd); } catch { /* ignore */ }
    }
    let nl: number;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl);
      buffer = buffer.slice(nl + 1);
      if (line.length > 0) {
        try {
          onLine(line);
        } catch (e) {
          process.stderr.write(`[bus] tail onLine threw: ${(e as Error).message}\n`);
        }
      }
    }
  }

  function schedule(): void {
    if (stopped) return;
    if (pending) return;
    pending = setTimeout(() => {
      pending = null;
      drain();
    }, DEBOUNCE_MS);
  }

  // Watch the parent dir; filter on basename. fs.watch on a non-existent file
  // throws; on the dir it works even if the file appears later.
  const watcher = watch(dir, (_eventType, changed) => {
    if (changed === base) schedule();
  });

  // Initial drain in case events fire before watcher is armed (rare on macOS
  // but cheap insurance). Use schedule() so first emit honors debounce path.
  schedule();

  return {
    stop(): void {
      stopped = true;
      if (pending) {
        clearTimeout(pending);
        pending = null;
      }
      try { watcher.close(); } catch { /* ignore */ }
    },
  };
}

// Test-only export for assertions on debounce timing.
export const _internals = { DEBOUNCE_MS };
