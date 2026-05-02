#!/usr/bin/env python3
"""Phase 9 — data-hygiene detector.

Two scopes:
  A. bot-data hygiene (cross-platform pollution, dead deprecated, oversized, file-map drift)
  B. SSOT log hygiene (size, retention prune, schema drift, writer-gap, per-host parity)

Read-only by default. `--fix` enables auto-prune for size + retention only;
pollution / drift / writer-gap stay warn-only (manual decision per Phase 9 spec).

Usage:
  python3 phase9_data_hygiene.py [--dry-run] [--fix] [--scope bot-data|ssot|all]
"""

import argparse
import datetime as dt
import gzip
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HOME = Path.home()
FILE_MAP = HOME / "NardoWorld" / "projects" / "prediction-markets" / "file-map.md"
SSOT_DIR_LOCAL = HOME / "NardoWorld" / "meta" / "ssot"
SSOT_QUERY = HOME / ".claude" / "scripts" / "ssot-query.sh"

# α.S7 — integrity detector (D1+D4)
sys.path.insert(0, str(HOME / ".claude" / "skills" / "lint" / "_lib"))
try:
    from ssot_integrity import run_integrity_checks  # noqa: E402
except Exception:
    run_integrity_checks = None  # tolerate absence; integrity row will SKIP

# Hosts in scope (mac is local; others via ssh)
BOT_HOSTS = [
    {"alias": "hel",    "ssh": "hel",    "data_dir": "/home/bernard/prediction-markets/packages/bot/data", "platform": "kalshi"},
    {"alias": "london", "ssh": "london", "data_dir": "/home/pm/prediction-markets/packages/bot/data",       "platform": "poly"},
]
SSOT_HOSTS = [
    {"alias": "mac",    "ssh": None,     "ssot_dir": str(SSOT_DIR_LOCAL)},
    {"alias": "hel",    "ssh": "hel",    "ssot_dir": "~/NardoWorld/meta/ssot"},
    {"alias": "london", "ssh": "london", "ssot_dir": "~/NardoWorld/meta/ssot"},
]

# H3 path classifier — validated in heuristic-validation.md H3
POLY_SIDE_RE = re.compile(r"^(clob_|polymarket_|poly_)")
KALSHI_SIDE_RE = re.compile(r"^kalshi_")

# H2 schema fields — required per spec §3
SSOT_REQUIRED_FIELDS = {"ts", "host", "event_id", "kind", "actor", "subject", "outcome"}

OVERSIZE_BYTES = 500 * 1024 * 1024  # 500MB
RETENTION_DAYS = 90
WRITER_GAP_HOURS = 1
SSH_TIMEOUT_S = 8


def _run(cmd: List[str], timeout: int = SSH_TIMEOUT_S) -> Tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


def _ssh(host: str, remote_cmd: str, timeout: int = SSH_TIMEOUT_S) -> Tuple[int, str, str]:
    return _run(["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout}", host, remote_cmd], timeout)


def _read_file_map() -> Dict[str, str]:
    """Return {filename: row_text} indexed from file-map.md. Empty if missing."""
    out = {}
    if not FILE_MAP.exists():
        return out
    text = FILE_MAP.read_text()
    # Match table rows referencing filenames in backticks
    for m in re.finditer(r"\|\s*`([A-Za-z0-9_./*-]+\.(?:json|jsonl|gz|log|lock))`\s*\|([^\n]+)", text):
        fname = m.group(1)
        row = m.group(2)
        out[fname] = row
    return out


def _deprecated_filenames(file_map: Dict[str, str]) -> List[str]:
    return [fn for fn, row in file_map.items() if "DEPRECATED" in row.upper()]


# H3 — pollution classifier (held-out validated)
def classify_pollution(filename: str, host_platform: str) -> Optional[str]:
    """Return 'cross-platform' if filename violates host's platform, else None."""
    if host_platform == "kalshi" and POLY_SIDE_RE.match(filename):
        return "cross-platform"
    if host_platform == "poly" and KALSHI_SIDE_RE.match(filename):
        return "cross-platform"
    return None


# H2 — schema-drift detector (held-out validated)
def detect_schema_drift(line: str) -> Optional[str]:
    """Return reason string if row drifts, else None."""
    line = line.strip()
    if not line:
        return "empty-line"
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return "json-parse-error"
    if not isinstance(obj, dict):
        return "not-object"
    missing = SSOT_REQUIRED_FIELDS - set(obj.keys())
    if missing:
        return f"missing-fields:{','.join(sorted(missing))}"
    # type sanity — strings expected
    for k in ("ts", "host", "event_id", "kind", "actor", "subject", "outcome"):
        v = obj.get(k)
        if v is None or not isinstance(v, str) or not v:
            return f"null-or-wrong-type:{k}"
    # ts ISO shape
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", obj["ts"]):
        return "ts-not-iso"
    # event_id shape
    if not obj["event_id"].startswith("evt_"):
        return "event_id-bad-prefix"
    return None


def _list_dir(host: Dict, dir_path: str) -> List[Tuple[str, int, int]]:
    """Return [(filename, size_bytes, mtime_epoch)] for files in dir_path.

    Portable across BSD (mac) + GNU (linux) — uses ls + stat fallback per file.
    """
    if host["ssh"]:
        # Linux: GNU find -printf works
        cmd = f"find {dir_path} -maxdepth 1 -type f -printf '%f\\t%s\\t%T@\\n' 2>/dev/null"
        rc, out, _ = _ssh(host["ssh"], cmd)
    else:
        # macOS: BSD find lacks -printf — use stat -f
        cmd = (f"cd '{dir_path}' 2>/dev/null && "
               f"find . -maxdepth 1 -type f 2>/dev/null | "
               f"while read f; do "
               f"  stat -f '%N\t%z\t%m' \"$f\" 2>/dev/null || stat -c '%n\t%s\t%Y' \"$f\" 2>/dev/null; "
               f"done")
        rc, out, _ = _run(["bash", "-c", cmd])
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        fname = parts[0].lstrip("./")
        try:
            rows.append((fname, int(parts[1]), int(float(parts[2]))))
        except ValueError:
            continue
    return rows


def scope_bot_data(report: List[str], file_map: Dict[str, str]) -> Dict[str, int]:
    """Run bot-data hygiene detectors; returns counts dict."""
    counts = {"pollution": 0, "deprecated": 0, "oversized": 0, "drift": 0, "host_total_bytes": 0}
    deprecated = set(_deprecated_filenames(file_map))
    file_map_basenames = set(file_map.keys())

    report.append("\n## Scope A — bot-data hygiene\n")

    if not file_map.keys():
        report.append("- WARN file-map missing or unparseable → deprecated + drift checks SKIPPED\n")

    for host in BOT_HOSTS:
        report.append(f"\n### {host['alias']} ({host['data_dir']}) — platform={host['platform']}\n")
        files = _list_dir(host, host["data_dir"])
        if not files:
            report.append(f"- SKIP host={host['alias']} reason=ssh-timeout-or-dir-empty\n")
            continue
        host_total = sum(s for _, s, _ in files)
        counts["host_total_bytes"] += host_total
        report.append(f"- files={len(files)}  total={host_total / 1024 / 1024:.0f}MB\n")

        # Cross-platform pollution
        pollution_hits = []
        for fname, size, mtime in files:
            base = fname.split("/")[-1]
            if classify_pollution(base, host["platform"]):
                pollution_hits.append((base, size, mtime))
        if pollution_hits:
            report.append(f"- FAIL cross-platform pollution: {len(pollution_hits)} files\n")
            for fname, size, mtime in pollution_hits[:10]:
                age_d = (dt.datetime.now().timestamp() - mtime) / 86400
                report.append(f"    - `{fname}`  {size / 1024 / 1024:.1f}MB  age={age_d:.0f}d\n")
            counts["pollution"] += len(pollution_hits)
        else:
            report.append("- PASS no cross-platform pollution\n")

        # Dead deprecated
        dep_hits = [(f, s, m) for f, s, m in files if f in deprecated]
        if dep_hits:
            report.append(f"- WARN deprecated files still on disk: {len(dep_hits)}\n")
            for fname, size, mtime in dep_hits:
                report.append(f"    - `{fname}`  {size / 1024 / 1024:.1f}MB\n")
            counts["deprecated"] += len(dep_hits)

        # Oversized
        oversize_hits = [(f, s) for f, s, _ in files if s > OVERSIZE_BYTES]
        if oversize_hits:
            report.append(f"- WARN oversized (>500MB): {len(oversize_hits)}\n")
            for fname, size in oversize_hits[:10]:
                report.append(f"    - `{fname}`  {size / 1024 / 1024:.0f}MB\n")
            counts["oversized"] += len(oversize_hits)

        # File-map drift (only when file-map non-empty)
        if file_map_basenames:
            drift = []
            for fname, size, _ in files:
                if size < 1024:  # skip tiny config files - too noisy
                    continue
                # tolerate timestamped rotation variants like clob_cancels.20260425-101043.jsonl.gz
                base_root = re.sub(r"\.\d{8}-\d{6}", "", fname)
                if fname not in file_map_basenames and base_root not in file_map_basenames:
                    drift.append(fname)
            if drift:
                report.append(f"- WARN file-map drift (on disk, not in map): {len(drift)} [unverified]\n")
                for f in drift[:8]:
                    report.append(f"    - `{f}`\n")
                if len(drift) > 8:
                    report.append(f"    - ... +{len(drift) - 8} more\n")
                counts["drift"] += len(drift)

    return counts


def _ssot_size_and_archives(host: Dict) -> Optional[Dict]:
    """Return {size: int, archives: [(name, mtime, size)]} or None on failure."""
    dir_path = str(Path(host["ssot_dir"]).expanduser()) if not host["ssh"] else host["ssot_dir"]
    rows = _list_dir(host, dir_path)
    if not rows and host["ssh"]:
        return None
    cur_size = 0
    archives = []
    for fname, size, mtime in rows:
        if fname == "ssot.jsonl":
            cur_size = size
        elif re.match(r"^ssot\.\d{8}-\d{6}\.jsonl\.gz$", fname):
            archives.append((fname, mtime, size))
    return {"size": cur_size, "archives": archives}


def _sample_ssot_lines(host: Dict, n: int = 100) -> List[str]:
    """Sample n random lines from ssot.jsonl on host."""
    path = f"{host['ssot_dir']}/ssot.jsonl"
    if host["ssh"]:
        rc, out, _ = _ssh(host["ssh"], f"shuf -n {n} '{path}' 2>/dev/null || head -n {n} '{path}' 2>/dev/null")
    else:
        local_path = Path(path).expanduser()
        if not local_path.exists():
            return []
        rc, out, _ = _run(["bash", "-c", f"shuf -n {n} '{local_path}' 2>/dev/null || head -n {n} '{local_path}'"])
    if rc != 0:
        return []
    return [l for l in out.splitlines() if l.strip()]


def _query_writer_gap() -> Dict[str, Optional[str]]:
    """Query SSOT for MAX(ts) per host. Returns {host: iso_ts or None}."""
    if not SSOT_QUERY.exists():
        return {}
    rc, out, _ = _run([str(SSOT_QUERY), "SELECT host, CAST(MAX(ts) AS VARCHAR) AS last_ts FROM ssot GROUP BY host"], timeout=20)
    if rc != 0:
        return {}
    result = {}
    for line in out.splitlines():
        line = line.strip()
        if not line or "host" in line.lower() or set(line) <= set("-│ "):
            continue
        # DuckDB box-drawing output: │ mac │ 2026-04-30 09:00:51.072 │
        parts = [p.strip() for p in re.split(r"[│|]", line) if p.strip()]
        if len(parts) >= 2 and parts[0] in ("mac", "hel", "london"):
            result[parts[0]] = parts[1]
    return result


def _bot_active(host_alias: str) -> Optional[bool]:
    """Return True/False if matching bot service is-active, None on probe failure."""
    if host_alias == "hel":
        unit = "kalshi-bot.service"
    elif host_alias == "london":
        unit = "pm-bot.service"
    else:
        return None
    rc, out, _ = _ssh(host_alias, f"systemctl is-active {unit}")
    if rc == 0 and out.strip() == "active":
        return True
    if "inactive" in out or "failed" in out:
        return False
    return None


def scope_ssot(report: List[str], do_fix: bool, dry_run: bool) -> Dict[str, int]:
    counts = {"oversize": 0, "retention_prune": 0, "drift_rows": 0, "writer_gap": 0, "missing_host": 0}
    report.append("\n## Scope B — SSOT log hygiene\n")

    # Per-host size + archives + drift
    for host in SSOT_HOSTS:
        report.append(f"\n### {host['alias']} ({host['ssot_dir']})\n")
        info = _ssot_size_and_archives(host)
        if info is None:
            report.append(f"- SKIP host={host['alias']} reason=ssh-timeout-or-dir-missing\n")
            counts["missing_host"] += 1
            continue
        if info["size"] == 0 and not info["archives"]:
            report.append(f"- SKIP host={host['alias']} reason=ssot.jsonl-absent (writer not yet deployed)\n")
            counts["missing_host"] += 1
            continue

        # 1. Size
        size_mb = info["size"] / 1024 / 1024
        if info["size"] > OVERSIZE_BYTES:
            verdict = "FAIL" if size_mb > 1024 else "WARN"
            report.append(f"- {verdict} ssot.jsonl size = {size_mb:.0f}MB (>500MB threshold)\n")
            counts["oversize"] += 1
            if do_fix and not dry_run:
                # Rotate via remote cmd
                stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
                rotate_cmd = (f"cd {host['ssot_dir']} && mv ssot.jsonl ssot.{stamp}.jsonl && "
                              f"touch ssot.jsonl && chmod 644 ssot.jsonl && gzip ssot.{stamp}.jsonl &")
                if host["ssh"]:
                    _ssh(host["ssh"], rotate_cmd)
                else:
                    _run(["bash", "-c", rotate_cmd])
                report.append(f"    - FIX rotated → ssot.{stamp}.jsonl.gz (async gzip)\n")
        else:
            report.append(f"- PASS ssot.jsonl size = {size_mb:.1f}MB\n")

        # 2. Retention prune
        now = dt.datetime.now().timestamp()
        old_archives = [(n, m, s) for n, m, s in info["archives"] if (now - m) / 86400 > RETENTION_DAYS]
        if old_archives:
            report.append(f"- WARN {len(old_archives)} archives >{RETENTION_DAYS}d retention\n")
            counts["retention_prune"] += len(old_archives)
            if do_fix and not dry_run:
                names = " ".join(f"'{host['ssot_dir']}/{n}'" for n, _, _ in old_archives)
                rm_cmd = f"rm -f {names}"
                if host["ssh"]:
                    _ssh(host["ssh"], rm_cmd)
                else:
                    _run(["bash", "-c", rm_cmd])
                report.append(f"    - FIX deleted {len(old_archives)} archive(s)\n")

        # 3. Schema drift
        sample = _sample_ssot_lines(host, n=100)
        if sample:
            drifted = [(l, detect_schema_drift(l)) for l in sample]
            drifted = [(l, r) for l, r in drifted if r is not None]
            if drifted:
                report.append(f"- WARN schema drift: {len(drifted)}/{len(sample)} sample rows\n")
                seen = {}
                for _, r in drifted[:5]:
                    seen[r] = seen.get(r, 0) + 1
                for r, c in seen.items():
                    report.append(f"    - `{r}` × {c}\n")
                counts["drift_rows"] += len(drifted)
            else:
                report.append(f"- PASS schema clean ({len(sample)}/{len(sample)} sample rows)\n")

        # α.S7 — integrity (missing-required + unknown-kinds). Local file only (mac).
        if host["alias"] == "mac" and run_integrity_checks is not None:
            local_path = SSOT_DIR_LOCAL / "ssot.jsonl"
            try:
                ic = run_integrity_checks(local_path)
                missing = ic.get("missing_required", 0)
                unk = ic.get("unknown_kinds", {}) or {}
                unk_total = sum(unk.values())
                verdict_m = "PASS" if missing == 0 else "FAIL"
                verdict_u = "PASS" if unk_total == 0 else "WARN"
                report.append(f"- {verdict_m} host=mac integrity_missing_required={missing}\n")
                report.append(f"- {verdict_u} host=mac integrity_unknown_kinds={unk_total}")
                if unk:
                    report.append(f" detail={dict(sorted(unk.items()))}")
                report.append("\n")
                counts["integrity_missing_required"] = counts.get("integrity_missing_required", 0) + missing
                counts["integrity_unknown_kinds"] = counts.get("integrity_unknown_kinds", 0) + unk_total
            except Exception as e:
                report.append(f"- SKIP integrity check error={e}\n")

    # 4. Writer-gap detection
    report.append("\n### Writer-gap detection (cross-host MAX(ts))\n")
    last_ts = _query_writer_gap()
    if not last_ts:
        report.append("- SKIP query helper unavailable or no events yet\n")
    else:
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        for host_alias, ts_str in last_ts.items():
            try:
                if ts_str is None:
                    report.append(f"- SKIP host={host_alias} reason=ts-null\n")
                    continue
                # DuckDB returns "YYYY-MM-DD HH:MM:SS.fff"
                last = dt.datetime.strptime(ts_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                report.append(f"- SKIP host={host_alias} reason=ts-parse-fail ({ts_str})\n")
                continue
            gap_h = (now - last).total_seconds() / 3600
            expected_active = (host_alias == "mac") or (_bot_active(host_alias) is True)
            if gap_h > WRITER_GAP_HOURS and expected_active:
                report.append(f"- FAIL host={host_alias} writer-gap = {gap_h:.1f}h (expected active)\n")
                counts["writer_gap"] += 1
            elif gap_h > WRITER_GAP_HOURS:
                report.append(f"- INFO host={host_alias} writer-gap = {gap_h:.1f}h (no active source — OK)\n")
            else:
                report.append(f"- PASS host={host_alias} last_ts={ts_str} gap={gap_h * 60:.0f}min\n")

    # 5. Per-host parity
    report.append("\n### Per-host parity\n")
    expected = {"mac"}  # always
    # hel: include if writer-deployed OR bot-active
    for h_alias in ("hel", "london"):
        info = _ssot_size_and_archives(next(x for x in SSOT_HOSTS if x["alias"] == h_alias))
        if info and info["size"] > 0:
            expected.add(h_alias)
    seen_hosts = set(last_ts.keys()) if last_ts else set()
    missing = expected - seen_hosts
    if missing:
        report.append(f"- WARN expected hosts absent from query result: {sorted(missing)}\n")
        counts["missing_host"] += len(missing)
    else:
        report.append(f"- PASS all expected hosts present: {sorted(expected)}\n")

    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, no fixes (default)")
    ap.add_argument("--fix", action="store_true", help="auto-prune size + retention")
    ap.add_argument("--scope", choices=["bot-data", "ssot", "all"], default="all")
    args = ap.parse_args()
    do_fix = args.fix and not args.dry_run

    report: List[str] = []
    report.append(f"# /lint Phase 9 — data-hygiene report\n")
    report.append(f"\nGenerated: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}  scope={args.scope}  fix={do_fix}\n")

    file_map = _read_file_map()

    bot_counts = {}
    ssot_counts = {}
    if args.scope in ("bot-data", "all"):
        bot_counts = scope_bot_data(report, file_map)
    if args.scope in ("ssot", "all"):
        ssot_counts = scope_ssot(report, do_fix, args.dry_run)

    report.append("\n## Summary\n")
    if bot_counts:
        report.append(f"- bot-data: pollution={bot_counts.get('pollution', 0)}, "
                      f"deprecated={bot_counts.get('deprecated', 0)}, "
                      f"oversized={bot_counts.get('oversized', 0)}, "
                      f"drift={bot_counts.get('drift', 0)}\n")
    if ssot_counts:
        report.append(f"- ssot: oversize={ssot_counts.get('oversize', 0)}, "
                      f"retention_prune={ssot_counts.get('retention_prune', 0)}, "
                      f"drift_rows={ssot_counts.get('drift_rows', 0)}, "
                      f"writer_gap={ssot_counts.get('writer_gap', 0)}, "
                      f"missing_host={ssot_counts.get('missing_host', 0)}\n")

    sys.stdout.write("".join(report))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
