"""P4: leak suspect detector. Top RSS hogs + delta over a 30s window."""
from __future__ import annotations

import time

from ._shell import run_on

# Per-host RSS thresholds. Mac dev workstation runs Chrome / Claude Code / Xcode
# routinely 10-20 GB collectively; lean VPS hosts run 200-800 MB total.
# Mirrors NardoWorld/scripts/bigd/performance/detectors/host_metrics.py.
RSS_THRESHOLDS_KB = {
    "mac":    {"warn": 8_000_000,  "crit": 16_000_000},
    "local":  {"warn": 8_000_000,  "crit": 16_000_000},
    "hel":    {"warn": 800_000,    "crit": 1_500_000},
    "london": {"warn": 800_000,    "crit": 1_500_000},
}
_DEFAULT_RSS = {"warn": 1_500_000, "crit": 4_000_000}

# Delta thresholds: 30s growth that suggests a real leak vs. noise.
# A 50 MB jump in 30s on Mac is normal (browser tab loading); on VPS it's a smoke alarm.
DELTA_THRESHOLDS_KB = {
    "mac":    {"warn": 200_000, "crit": 500_000},
    "local":  {"warn": 200_000, "crit": 500_000},
    "hel":    {"warn": 30_000,  "crit": 100_000},
    "london": {"warn": 30_000,  "crit": 100_000},
}
_DEFAULT_DELTA = {"warn": 50_000, "crit": 200_000}


def _sample(host: str) -> dict[str, int]:
    cmd = "ps -eo pid,rss,comm | tail -n +2"
    rc, out, _ = run_on(host, cmd)
    if rc != 0:
        return {}
    procs = {}
    for ln in out.splitlines():
        parts = ln.split(None, 2)
        if len(parts) < 3:
            continue
        try:
            procs[parts[0]] = int(parts[1])
        except ValueError:
            continue
    return procs


def scan(host: str) -> dict:
    s1 = _sample(host)
    if not s1:
        return {"verdict": "error", "evidence_cmd": "ps -eo pid,rss,comm (x2)",
                "findings": [], "summary": "first ps sample failed"}
    time.sleep(30)
    cmd = "ps -eo pid,rss,vsz,comm,args | sort -k2 -nr | head -20"
    rc, out, err = run_on(host, cmd)
    if rc != 0:
        return {"verdict": "error", "evidence_cmd": cmd, "findings": [],
                "summary": f"ps failed rc={rc}: {err.strip()[:200]}"}
    s2 = _sample(host)
    findings = []
    for ln in out.splitlines():
        parts = ln.split(None, 4)
        if len(parts) < 4:
            continue
        try:
            rss = int(parts[1])
            vsz = int(parts[2])
        except ValueError:
            continue
        pid = parts[0]
        delta = (s2.get(pid, rss) - s1.get(pid, rss))
        findings.append({"pid": pid, "rss_kb": rss, "vsz_kb": vsz,
                         "comm": parts[3], "args": parts[4][:120] if len(parts) > 4 else parts[3],
                         "delta_kb_30s": delta})
    rss_t = RSS_THRESHOLDS_KB.get(host, _DEFAULT_RSS)
    delta_t = DELTA_THRESHOLDS_KB.get(host, _DEFAULT_DELTA)
    crit = [f for f in findings if f["rss_kb"] >= rss_t["crit"] or f["delta_kb_30s"] >= delta_t["crit"]]
    warn = [f for f in findings if f["rss_kb"] >= rss_t["warn"] or f["delta_kb_30s"] >= delta_t["warn"]]
    if crit:
        verdict = "crit"
        summary = (f"{len(crit)} procs RSS>={rss_t['crit']//1000}MB "
                   f"or grew>={delta_t['crit']//1000}MB/30s on {host}")
    elif warn:
        verdict = "warn"
        summary = (f"{len(warn)} procs RSS>={rss_t['warn']//1000}MB "
                   f"or grew>={delta_t['warn']//1000}MB/30s on {host}")
    else:
        verdict = "ok"
        summary = f"top procs within budget on {host}"
    return {"verdict": verdict, "evidence_cmd": cmd,
            "findings": findings, "summary": summary}
