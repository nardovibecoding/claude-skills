"""P3: hot-loop detector. Two ps samples 3s apart; flag procs >5% CPU in both."""
from __future__ import annotations

import time

from ._shell import run_on

CPU_WARN = 5.0
CPU_CRIT = 50.0


def _sample(host: str) -> dict[str, dict]:
    cmd = "ps -eo pid,pcpu,comm,args | tail -n +2"
    rc, out, _ = run_on(host, cmd)
    if rc != 0:
        return {}
    procs = {}
    for ln in out.splitlines():
        parts = ln.split(None, 3)
        if len(parts) < 3:
            continue
        try:
            cpu = float(parts[1])
        except ValueError:
            continue
        procs[parts[0]] = {"pid": parts[0], "pcpu": cpu, "comm": parts[2],
                           "args": parts[3] if len(parts) > 3 else parts[2]}
    return procs


def scan(host: str) -> dict:
    s1 = _sample(host)
    if not s1:
        return {"verdict": "error", "evidence_cmd": "ps -eo pid,pcpu,comm,args (x2)",
                "findings": [], "summary": "first ps sample failed"}
    time.sleep(3)
    s2 = _sample(host)
    if not s2:
        return {"verdict": "error", "evidence_cmd": "ps -eo pid,pcpu,comm,args (x2)",
                "findings": [], "summary": "second ps sample failed"}
    findings = []
    for pid, p in s2.items():
        prev = s1.get(pid)
        if not prev:
            continue
        if p["pcpu"] >= CPU_WARN and prev["pcpu"] >= CPU_WARN:
            findings.append({"pid": pid, "comm": p["comm"],
                             "pcpu_t0": prev["pcpu"], "pcpu_t1": p["pcpu"],
                             "args": p["args"][:120]})
    findings.sort(key=lambda x: x["pcpu_t1"], reverse=True)
    crit = [f for f in findings if f["pcpu_t1"] >= CPU_CRIT]
    if crit:
        verdict = "crit"
        summary = f"{len(crit)} procs >={CPU_CRIT}% CPU sustained, {len(findings)} >={CPU_WARN}%"
    elif findings:
        verdict = "warn"
        summary = f"{len(findings)} procs >={CPU_WARN}% CPU sustained 3s"
    else:
        verdict = "ok"
        summary = "no sustained hot procs"
    return {"verdict": verdict, "evidence_cmd": "ps -eo pid,pcpu,comm,args (sampled 2x, 3s apart)",
            "findings": findings[:30], "summary": summary}
