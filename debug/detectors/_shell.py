"""Shared shell helpers for P1-P4 detectors. SSH wraps with 10s timeout."""
from __future__ import annotations

import shlex
import subprocess

SSH_TIMEOUT = 10
KNOWN_HOSTS = {"local", "mac", "hel", "london"}


def run_on(host: str, cmd: str, timeout: int = SSH_TIMEOUT) -> tuple[int, str, str]:
    """Run `cmd` on host. host in {local, mac, hel, london}. Returns (rc, stdout, stderr)."""
    if host in ("local", "mac"):
        full = ["bash", "-lc", cmd]
    elif host in ("hel", "london"):
        full = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout}",
                "-o", "ControlMaster=no", "-o", "ControlPath=none",
                host, cmd]
    else:
        return 127, "", f"unknown host: {host}"
    try:
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout + 5)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout + 5}s"
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"


def quote_for_remote(s: str) -> str:
    return shlex.quote(s)
