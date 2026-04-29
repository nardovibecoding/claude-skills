"""P4: leak suspect detector. Top RSS hogs + delta over a 30s window."""
from __future__ import annotations

import time

from ._shell import run_on

RSS_WARN_KB = 500_000     # 500 MB
RSS_CRIT_KB = 1_500_000   # 1.5 GB
DELTA_WARN_KB = 50_000    # 50 MB grew in 30s == ~100 MB/min
DELTA_CRIT_KB = 200_000


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
    crit = [f for f in findings if f["rss_kb"] >= RSS_CRIT_KB or f["delta_kb_30s"] >= DELTA_CRIT_KB]
    warn = [f for f in findings if f["rss_kb"] >= RSS_WARN_KB or f["delta_kb_30s"] >= DELTA_WARN_KB]
    if crit:
        verdict = "crit"
        summary = f"{len(crit)} procs RSS>=1.5GB or grew>=200MB/30s"
    elif warn:
        verdict = "warn"
        summary = f"{len(warn)} procs RSS>=500MB or grew>=50MB/30s"
    else:
        verdict = "ok"
        summary = "top procs within budget"
    return {"verdict": verdict, "evidence_cmd": cmd,
            "findings": findings, "summary": summary}
