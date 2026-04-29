"""P2: orphan process detector. PPID=1 procs not in init-adopted allowlist.

The London 32-orphan-git-receive-pack incident (2026-04-29 morning, see
~/.claude/projects/-Users-bernard/memory/convo_2026-04-29_vibeisland-perf-perm-fix-deep.md)
is the canonical case. Sshd disconnect mid-push leaves index-pack/receive-pack
re-parented to PID 1, hot CPU, not reaped by sshd.
"""
from __future__ import annotations

from ._shell import run_on

# Procs whose PPID=1 is normal (started by init/launchd/systemd directly).
EXPECTED_INIT_ADOPTED = {
    # macOS launchd-managed
    "launchd", "logd", "WindowServer", "loginwindow", "Dock", "Finder",
    "SystemUIServer", "ControlCenter", "NotificationCenter", "Spotlight",
    "coreaudiod", "syslogd", "configd", "powerd", "bluetoothd",
    # systemd-managed common
    "systemd", "systemd-journal", "systemd-logind", "systemd-resolve",
    "systemd-timesyn", "systemd-udevd", "systemd-network",
    "sshd", "cron", "rsyslogd", "dbus-daemon", "agetty", "containerd",
    "dockerd", "snapd", "polkitd", "udisksd",
    # bot-relevant
    "node", "python3", "python",  # could be legit services; only flag git-class below
}

# Always-suspicious comm patterns (substring match) — these should never be
# init-adopted in normal operation.
SUSPICIOUS_PATTERNS = [
    "git index-pack", "git-index-pack", "index-pack",
    "git receive-pack", "git-receive-pack", "receive-pack",
    "git upload-pack", "git-upload-pack", "upload-pack",
    "<defunct>",
]


def scan(host: str) -> dict:
    cmd = "ps -eo pid,ppid,user,etime,comm,args | awk 'NR==1 || $2==1'"
    rc, out, err = run_on(host, cmd)
    if rc != 0:
        return {"verdict": "error", "evidence_cmd": cmd, "findings": [],
                "summary": f"ps failed rc={rc}: {err.strip()[:200]}"}
    lines = [ln for ln in out.splitlines() if ln.strip()]
    findings = []
    suspicious = 0
    for ln in lines[1:]:
        parts = ln.split(None, 5)
        if len(parts) < 5:
            continue
        pid, ppid, user, etime, comm = parts[:5]
        args = parts[5] if len(parts) > 5 else comm
        # Match against allowlist by comm basename (strip leading [, brackets).
        comm_clean = comm.strip("[]").split("/")[-1]
        is_suspicious = any(pat in args for pat in SUSPICIOUS_PATTERNS)
        if is_suspicious or comm_clean not in EXPECTED_INIT_ADOPTED:
            findings.append({"pid": pid, "ppid": ppid, "user": user,
                             "etime": etime, "comm": comm_clean,
                             "args": args[:120],
                             "suspicious": is_suspicious})
            if is_suspicious:
                suspicious += 1
    # Verdict driven by SUSPICIOUS hits only. The "non-allowlist PPID=1" count
    # is reported but does not flip the verdict — Mac alone has hundreds of
    # legit PPID=1 helpers (Chrome Helper, *Service.app, etc.) that no static
    # allowlist will ever fully cover.
    if suspicious >= 5:
        verdict = "crit"
        summary = f"{suspicious} suspicious orphans (git-pack/defunct), {len(findings)} non-allowlist PPID=1 (informational)"
    elif suspicious > 0:
        verdict = "warn"
        summary = f"{suspicious} suspicious orphans, {len(findings)} non-allowlist PPID=1 (informational)"
    else:
        verdict = "ok"
        summary = f"0 suspicious orphans, {len(findings)} non-allowlist PPID=1 (informational)"
    # Limit findings to suspicious + first 10 non-suspicious so the .md stays readable.
    susp_findings = [f for f in findings if f["suspicious"]]
    other_findings = [f for f in findings if not f["suspicious"]][:10]
    return {"verdict": verdict, "evidence_cmd": cmd,
            "findings": susp_findings + other_findings, "summary": summary}
