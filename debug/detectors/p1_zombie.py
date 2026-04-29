"""P1: zombie process detector. Lists procs in 'Z' state."""
from __future__ import annotations

from ._shell import run_on

# Per-host thresholds. Mac is a workstation; some short-lived zombies between
# reaping cycles are normal. VPS hosts run lean and any zombie is suspicious.
THRESHOLDS = {
    "mac":    {"warn": 10, "crit": 30},
    "local":  {"warn": 10, "crit": 30},
    "hel":    {"warn": 1,  "crit": 5},
    "london": {"warn": 1,  "crit": 5},
}
_DEFAULT_T = {"warn": 5, "crit": 15}


def scan(host: str) -> dict:
    # ps STAT field 'Z' = zombie/defunct. Same flag works on macOS + Linux.
    cmd = "ps -eo pid,ppid,stat,comm,etime | awk 'NR==1 || $3 ~ /Z/'"
    rc, out, err = run_on(host, cmd)
    if rc != 0:
        return {"verdict": "error", "evidence_cmd": cmd, "findings": [],
                "summary": f"ps failed rc={rc}: {err.strip()[:200]}"}
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # First line is header.
    findings = []
    for ln in lines[1:]:
        parts = ln.split(None, 4)
        if len(parts) < 4:
            continue
        findings.append({"pid": parts[0], "ppid": parts[1], "stat": parts[2],
                         "comm": parts[3], "etime": parts[4] if len(parts) > 4 else ""})
    n = len(findings)
    if n == 0:
        verdict = "ok"
        summary = "no zombies"
    elif n < 5:
        verdict = "warn"
        summary = f"{n} zombie procs"
    else:
        verdict = "crit"
        summary = f"{n} zombie procs (>=5)"
    return {"verdict": verdict, "evidence_cmd": cmd,
            "findings": findings, "summary": summary}
