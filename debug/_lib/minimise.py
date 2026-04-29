"""
Delta-debugging engine for /debug auto-minimise.

Implements Zeller & Hildebrandt (2002) ddmin binary-partition algorithm
plus three convenience wrappers (lines / env / files), a 1D workload
binary-search, and a flaky-aware probe wrapper.

Pure stdlib. No external deps.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence


# ────────────────────────────────────────────────────────────────────────────
# Result + Fingerprint primitives
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class ProbeResult:
    exit: int
    stdout: str
    stderr: str
    wall_ms: int


@dataclass
class Fingerprint:
    """How to recognise that the bug is still present in a probe result."""
    exit_code: Optional[int] = None        # e.g. 1 — exact match
    exit_nonzero: bool = False             # any non-zero exit counts
    stderr_regex: Optional[str] = None     # compiled-on-match
    stdout_regex: Optional[str] = None

    def match(self, r: ProbeResult) -> bool:
        if self.exit_code is not None and r.exit != self.exit_code:
            return False
        if self.exit_nonzero and r.exit == 0:
            return False
        if self.stderr_regex and not re.search(self.stderr_regex, r.stderr):
            return False
        if self.stdout_regex and not re.search(self.stdout_regex, r.stdout):
            return False
        # if no criteria specified, never match (fail loud)
        if (self.exit_code is None and not self.exit_nonzero
                and not self.stderr_regex and not self.stdout_regex):
            raise ValueError("Fingerprint has no match criteria — specify exit_code, exit_nonzero, stderr_regex, or stdout_regex")
        return True


@dataclass
class MinimiseStats:
    probes: int = 0
    kept_strips: int = 0
    reverted_strips: int = 0
    cap_reached: bool = False
    log: list = field(default_factory=list)  # list of dict rows for minimise-log.md


# ────────────────────────────────────────────────────────────────────────────
# Core ddmin (Zeller binary-partition)
# ────────────────────────────────────────────────────────────────────────────

def ddmin(
    items: list,
    probe_fn: Callable[[list], bool],
    max_probes: int = 100,
    on_step: Optional[Callable[[dict], None]] = None,
) -> tuple[list, MinimiseStats]:
    """
    Zeller's binary-partition ddmin. Returns the smallest sublist of `items`
    such that `probe_fn(sublist)` returns True, plus stats.

    `probe_fn(subset) → True` means "bug still reproduces with this subset".

    Algorithm:
      n = 2; while len(items) > 1:
        partition items into n chunks
        for each chunk c:
          if probe_fn(items - c):  # bug reproduces without c → c is irrelevant
            items = items - c; n = max(n-1, 2); restart partition
        else if probe_fn(c):       # bug reproduces with just c → drop everything else
          items = c; n = 2; restart
        else if n < len(items):    # increase granularity
          n = min(n*2, len(items))
        else:
          break  # 1-minimal
      return items
    """
    stats = MinimiseStats()

    def emit(entry: dict) -> None:
        stats.log.append(entry)
        if on_step:
            on_step(entry)

    def probe(subset: list, label: str) -> bool:
        if stats.probes >= max_probes:
            stats.cap_reached = True
            return False
        stats.probes += 1
        result = probe_fn(subset)
        emit({
            "probe": stats.probes,
            "label": label,
            "size": len(subset),
            "reproduces": result,
        })
        return result

    n = 2
    current = list(items)

    while len(current) > 1:
        if stats.cap_reached:
            break

        chunk_size = max(len(current) // n, 1)
        partitions = [current[i:i + chunk_size] for i in range(0, len(current), chunk_size)]

        # Try removing each chunk → keep the complement that still reproduces
        complement_reduced = False
        for i, chunk in enumerate(partitions):
            complement = [x for x in current if x not in chunk]
            if not complement:
                continue
            if probe(complement, f"complement-of-chunk-{i+1}/{len(partitions)}"):
                current = complement
                stats.kept_strips += 1
                n = max(n - 1, 2)
                complement_reduced = True
                break

        if complement_reduced:
            continue

        # Try each chunk in isolation → reproducing chunk = drop everything else
        chunk_isolated = False
        for i, chunk in enumerate(partitions):
            if probe(chunk, f"isolate-chunk-{i+1}/{len(partitions)}"):
                current = chunk
                stats.kept_strips += 1
                n = 2
                chunk_isolated = True
                break

        if chunk_isolated:
            continue

        # Increase granularity
        if n < len(current):
            n = min(n * 2, len(current))
        else:
            break  # 1-minimal — no further progress possible

    return current, stats


# ────────────────────────────────────────────────────────────────────────────
# Probe runners
# ────────────────────────────────────────────────────────────────────────────

def run_command(
    cmd: list[str] | str,
    env: Optional[dict] = None,
    cwd: Optional[Path] = None,
    timeout: Optional[int] = 60,
) -> ProbeResult:
    """Run a command and capture exit/stdout/stderr/wall-time."""
    shell = isinstance(cmd, str)
    t0 = time.monotonic()
    try:
        p = subprocess.run(
            cmd,
            shell=shell,
            env=env,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        wall_ms = int((time.monotonic() - t0) * 1000)
        return ProbeResult(exit=p.returncode, stdout=p.stdout, stderr=p.stderr, wall_ms=wall_ms)
    except subprocess.TimeoutExpired as e:
        wall_ms = int((time.monotonic() - t0) * 1000)
        return ProbeResult(
            exit=124,
            stdout=(e.stdout.decode() if e.stdout else "") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=f"[timeout after {timeout}s]",
            wall_ms=wall_ms,
        )


def _maybe_reset(reset_cmd: Optional[str]) -> None:
    if reset_cmd:
        r = run_command(reset_cmd, timeout=30)
        if r.exit != 0:
            raise RuntimeError(f"reset_cmd failed (exit {r.exit}): {r.stderr[:200]}")


# ────────────────────────────────────────────────────────────────────────────
# ddmin_lines — partition lines of repro.sh, keep smallest failing subset
# ────────────────────────────────────────────────────────────────────────────

def ddmin_lines(
    repro_path: Path,
    fingerprint: Fingerprint,
    reset_cmd: Optional[str] = None,
    max_probes: int = 100,
    timeout: int = 60,
    out_path: Optional[Path] = None,
    preserve_lines: Optional[Callable[[str], bool]] = None,
) -> tuple[list[str], MinimiseStats]:
    """
    Minimise lines of a repro shell script. `preserve_lines(line) → True` means
    the line is structural (e.g. shebang, `set -e`) and must never be stripped.
    """
    repro_path = Path(repro_path)
    original_lines = repro_path.read_text().splitlines(keepends=True)

    if preserve_lines is None:
        preserve_lines = lambda line: line.startswith("#!") or line.strip().startswith("set ")

    structural = [(i, ln) for i, ln in enumerate(original_lines) if preserve_lines(ln)]
    candidate = [(i, ln) for i, ln in enumerate(original_lines) if not preserve_lines(ln)]

    tmp_path = repro_path.with_suffix(repro_path.suffix + ".probe")

    def probe_fn(subset: list[tuple[int, str]]) -> bool:
        # reassemble: structural lines + chosen candidate lines, in original index order
        chosen = sorted(structural + subset, key=lambda x: x[0])
        body = "".join(ln for _, ln in chosen)
        tmp_path.write_text(body)
        os.chmod(tmp_path, 0o755)
        _maybe_reset(reset_cmd)
        r = run_command([str(tmp_path)], timeout=timeout)
        return fingerprint.match(r)

    try:
        minimal_candidates, stats = ddmin(candidate, probe_fn, max_probes=max_probes)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    final_lines = [ln for _, ln in sorted(structural + minimal_candidates, key=lambda x: x[0])]

    if out_path:
        out_path = Path(out_path)
        out_path.write_text("".join(final_lines))
        os.chmod(out_path, 0o755)

    return final_lines, stats


# ────────────────────────────────────────────────────────────────────────────
# ddmin_env — minimise env-var subset
# ────────────────────────────────────────────────────────────────────────────

def ddmin_env(
    env_keys: Sequence[str],
    base_env: dict[str, str],
    run_cmd: list[str] | str,
    fingerprint: Fingerprint,
    reset_cmd: Optional[str] = None,
    max_probes: int = 100,
    timeout: int = 60,
) -> tuple[list[str], MinimiseStats]:
    """Find smallest subset of env_keys that, when set in env, still triggers fingerprint."""
    keys = list(env_keys)

    def probe_fn(subset: list[str]) -> bool:
        env = {k: v for k, v in base_env.items() if k not in keys or k in subset}
        # Always carry PATH/HOME for sanity
        for must in ("PATH", "HOME"):
            if must in os.environ and must not in env:
                env[must] = os.environ[must]
        _maybe_reset(reset_cmd)
        r = run_command(run_cmd, env=env, timeout=timeout)
        return fingerprint.match(r)

    return ddmin(keys, probe_fn, max_probes=max_probes)


# ────────────────────────────────────────────────────────────────────────────
# ddmin_files — minimise file set (rename-to-.bak to "remove")
# ────────────────────────────────────────────────────────────────────────────

def ddmin_files(
    paths: Sequence[Path],
    run_cmd: list[str] | str,
    fingerprint: Fingerprint,
    reset_cmd: Optional[str] = None,
    max_probes: int = 100,
    timeout: int = 60,
) -> tuple[list[Path], MinimiseStats]:
    """
    Find smallest subset of `paths` that, when present (others renamed to .bak),
    still triggers fingerprint. Idempotent restore on entry/exit.
    """
    files = [Path(p) for p in paths]
    bak_suffix = ".ddmin-bak"

    def restore_all() -> None:
        for f in files:
            bak = f.with_suffix(f.suffix + bak_suffix)
            if bak.exists() and not f.exists():
                bak.rename(f)

    restore_all()  # idempotent on entry

    def probe_fn(subset: list[Path]) -> bool:
        present = set(subset)
        # rename absent files to .bak
        for f in files:
            bak = f.with_suffix(f.suffix + bak_suffix)
            if f in present:
                if bak.exists() and not f.exists():
                    bak.rename(f)
            else:
                if f.exists():
                    f.rename(bak)
        try:
            _maybe_reset(reset_cmd)
            r = run_command(run_cmd, timeout=timeout)
            return fingerprint.match(r)
        finally:
            pass  # leave state for next probe; final restore in outer try

    try:
        return ddmin(files, probe_fn, max_probes=max_probes)
    finally:
        restore_all()


# ────────────────────────────────────────────────────────────────────────────
# bsearch_workload — 1D binary search for smallest workload showing regression
# ────────────────────────────────────────────────────────────────────────────

def bsearch_workload(
    low: int,
    high: int,
    perf_fn: Callable[[int], int],
    baseline_ms: int,
    target_ratio: float = 1.5,
    max_probes: int = 30,
) -> tuple[int, MinimiseStats]:
    """
    Find smallest workload size in [low, high] where perf_fn(size) >= baseline_ms * target_ratio.

    Assumes monotonic: larger workload → larger or equal wall-time.
    """
    stats = MinimiseStats()
    threshold = baseline_ms * target_ratio

    def measure(size: int) -> bool:
        if stats.probes >= max_probes:
            stats.cap_reached = True
            return False
        stats.probes += 1
        ms = perf_fn(size)
        regresses = ms >= threshold
        stats.log.append({
            "probe": stats.probes,
            "size": size,
            "wall_ms": ms,
            "regresses": regresses,
        })
        return regresses

    # First check high end actually regresses; if not, bail
    if not measure(high):
        return high, stats  # nothing regresses; return upper bound as best-known

    lo, hi = low, high
    smallest_regressing = high
    while lo <= hi and not stats.cap_reached:
        mid = (lo + hi) // 2
        if mid <= 0:
            break
        if measure(mid):
            smallest_regressing = mid
            hi = mid - 1
        else:
            lo = mid + 1

    return smallest_regressing, stats


# ────────────────────────────────────────────────────────────────────────────
# flaky_probe — wrap a fingerprint-based probe into a flaky-aware oracle
# ────────────────────────────────────────────────────────────────────────────

def flaky_probe(
    raw_probe: Callable[[list], ProbeResult],
    fingerprint: Fingerprint,
    runs: int,
    threshold: float = 0.5,
) -> Callable[[list], bool]:
    """
    Wrap a single-shot probe into an N-runs majority oracle. Returns a probe_fn
    that runs `raw_probe` `runs` times and returns True iff fail-rate >= threshold.
    """
    if runs < 2:
        raise ValueError("flaky_probe requires runs >= 2")

    def oracle(subset: list) -> bool:
        fails = 0
        for _ in range(runs):
            r = raw_probe(subset)
            if fingerprint.match(r):
                fails += 1
        return (fails / runs) >= threshold

    return oracle


# ────────────────────────────────────────────────────────────────────────────
# Non-determinism precheck (AC-8)
# ────────────────────────────────────────────────────────────────────────────

def precheck_deterministic(
    repro_path: Path,
    fingerprint: Fingerprint,
    trials: int = 3,
    timeout: int = 60,
) -> bool:
    """Run the full repro `trials` times. Return True iff all trials agree on fingerprint match."""
    repro_path = Path(repro_path)
    matches = []
    for _ in range(trials):
        r = run_command([str(repro_path)], timeout=timeout)
        matches.append(fingerprint.match(r))
    return len(set(matches)) == 1


# ────────────────────────────────────────────────────────────────────────────
# Log emitter — minimise-log.md row formatting
# ────────────────────────────────────────────────────────────────────────────

def render_log(stats: MinimiseStats, header: str) -> str:
    out = [f"# {header}\n"]
    out.append(f"\nprobes={stats.probes} kept_strips={stats.kept_strips} cap_reached={stats.cap_reached}\n")
    out.append("\n| # | label | size | reproduces |\n|---|---|---|---|\n")
    for row in stats.log:
        if "label" in row:
            out.append(f"| {row['probe']} | {row['label']} | {row['size']} | {row['reproduces']} |\n")
        else:
            out.append(f"| {row['probe']} | size={row['size']} | {row.get('wall_ms','?')}ms | {row.get('regresses','?')} |\n")
    return "".join(out)
