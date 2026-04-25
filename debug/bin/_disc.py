#!/usr/bin/env python3
"""
_disc.py — shared discipline writers for /debug modes (S3 Sh4 merge).

Three sinks, used by both Wiring (cmd_check) and Bug (cmd_bug):
  - write_observation()   → .ship/<bug-slug>/experiments/observations.md
  - write_round()         → .ship/<bug-slug>/experiments/rounds.md
  - write_causal_chain()  → .ship/<bug-slug>/state/causal-chain.md
  - atomic_ledger_append() → ~/NardoWorld/realize-debt.md (lockfile + atomic write; closes D1)

Templates mirror:
  - ~/.claude/skills/ship/phases/common/observations.md
  - ~/.claude/skills/ship/phases/common/rounds.md
  - ~/.claude/rules/ship.md § Causal chain completeness
"""
from __future__ import annotations
import fcntl
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SHIP_ROOT = HOME / ".ship"
LEDGER = HOME / "NardoWorld" / "realize-debt.md"
LEDGER_LOCK = HOME / "NardoWorld" / ".realize-debt.lock"

VALID_ISOLATION = ("[single-point]", "[N-comparison]", "[isolation-verified]")


def _bug_dir(bug_slug: str) -> Path:
    d = SHIP_ROOT / bug_slug
    (d / "experiments").mkdir(parents=True, exist_ok=True)
    (d / "state").mkdir(parents=True, exist_ok=True)
    return d


def write_observation(bug_slug: str, text: str, isolation_label: str,
                      observer: str = "main-assistant",
                      trigger: str = "/debug bug runtime-verify") -> Path:
    """Append one observation block to .ship/<bug-slug>/experiments/observations.md."""
    if not any(isolation_label.startswith(v.rstrip("]")) for v in VALID_ISOLATION):
        isolation_label = "[single-point]"
    bd = _bug_dir(bug_slug)
    obs_path = bd / "experiments" / "observations.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = f"""
### {ts} — {bug_slug}-obs

observer:       {observer}
trigger:        {trigger}

raw output:     {text}

isolation label:  {isolation_label}

permitted claims from this entry:
  - describes observed behavior
  NOT permitted: "X caused Y" / "rules out Z" unless [isolation-verified]

downgrades applied:
  - n/a (auto-written by /debug bug)
"""
    if not obs_path.exists():
        obs_path.write_text(f"# Observations log — {bug_slug}\n\nSee ~/.claude/skills/ship/phases/common/observations.md for schema.\n")
    with open(obs_path, "a") as f:
        f.write(block)
    return obs_path


def write_round(bug_slug: str, sha: str, claimed_vars: list[str],
                observed_outcome: str, round_n: int = 1) -> Path:
    """Append one round block to .ship/<bug-slug>/experiments/rounds.md."""
    bd = _bug_dir(bug_slug)
    rounds_path = bd / "experiments" / "rounds.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sha_str = sha if sha else "unknown"
    verdict = "[first-round]" if round_n == 1 else "[unisolated]"
    claimed_str = "\n  - ".join(claimed_vars) if claimed_vars else "first round — no prior baseline"
    block = f"""
### Round {round_n} — {ts} — {bug_slug}

claimed-vars-changed-vs-prior:
  - {claimed_str}

deploy state at test:
  git SHA:            {sha_str}

actual-vars-changed-vs-prior:
  - (computed by user via `git diff <prev>..<this>` before next round)

observed outcome:
  - symptom: {observed_outcome}

verdict: {verdict}

next-round plan (if symptom persists):
  - var to vary:        <one variable>
  - falsification:      <observation that would refute current hypothesis>
"""
    if not rounds_path.exists():
        rounds_path.write_text(f"# Debug rounds log — {bug_slug}\n\nSee ~/.claude/skills/ship/phases/common/rounds.md for schema.\n")
    with open(rounds_path, "a") as f:
        f.write(block)
    return rounds_path


def write_causal_chain(bug_slug: str, steps: list[dict]) -> Path:
    """Write numbered causal chain to .ship/<bug-slug>/state/causal-chain.md.

    Each step: {n: int, text: str, citation: str}
      citation must be `[cited file:line]` / `[cited cmd]` / `[GAP — unverified, exp:<X>]`.
      No `???` leaps allowed — replaces them with `[GAP — unverified]`.
    """
    bd = _bug_dir(bug_slug)
    chain_path = bd / "state" / "causal-chain.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Causal chain — {bug_slug}\n",
             f"Written {ts} by /debug bug Step 11 DEPTH-CHECK.\n",
             "Per ~/.claude/rules/ship.md § Causal chain completeness — every step `[cited]` or `[GAP — unverified]`.\n"]
    for s in steps:
        text = s.get("text", "")
        cite = s.get("citation", "[GAP — unverified]")
        if "???" in text or "???" in cite:
            cite = "[GAP — unverified, exp: re-investigate this leap]"
        lines.append(f"{s.get('n', '?')}. {text} {cite}")
    chain_path.write_text("\n".join(lines) + "\n")
    return chain_path


def _next_id_locked(txt: str) -> str:
    ids = re.findall(r"^## (R-\d{4}) ", txt, re.MULTILINE)
    if not ids:
        return "R-0001"
    n = max(int(i.split("-")[1]) for i in ids)
    return f"R-{n+1:04d}"


def atomic_ledger_append(entry_body_template, header_if_new: str = "") -> str:
    """Atomically append a new ledger entry. Closes D1 (ledger ID race).

    entry_body_template: callable(entry_id: str) -> str
      Receives the freshly-allocated R-NNNN id and returns the full markdown block.
      Caller composes the body inside the lock so the id is correct.

    Returns the entry_id assigned. Uses fcntl.LOCK_EX on LEDGER_LOCK; re-reads max id
    AFTER acquiring lock; writes via tmpfile + os.replace for atomicity.
    """
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_LOCK.parent.mkdir(parents=True, exist_ok=True)
    # Open lock file
    lock_fd = os.open(str(LEDGER_LOCK), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        # Re-read inside lock
        if LEDGER.exists():
            cur = LEDGER.read_text()
        else:
            cur = header_if_new or ""
        entry_id = _next_id_locked(cur)
        body = entry_body_template(entry_id)
        new_content = cur + body
        # Atomic replace: write tmpfile in same dir, then os.replace
        with tempfile.NamedTemporaryFile(
                mode="w", dir=str(LEDGER.parent),
                prefix=".realize-debt.tmp.", delete=False) as tf:
            tf.write(new_content)
            tmp_path = tf.name
        os.replace(tmp_path, str(LEDGER))
        return entry_id
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def normalize_feature_tokens(feature: str) -> list[str]:
    """Closes D2 (matcher fragility). Generate kebab/camel/snake/lower variants.

    Input may be kebab-case, camelCase, snake_case, or lowercase. Returns list with
    all four variants (lowercased for case-insensitive substring match) plus the
    raw input.
    """
    raw = feature.strip()
    # Split into tokens by any of: -, _, camelCase boundary
    parts = re.split(r"[-_\s]+", raw)
    expanded = []
    for p in parts:
        # split camelCase
        sub = re.sub(r"(?<!^)(?=[A-Z])", " ", p).split()
        expanded.extend(sub if sub else [p])
    expanded = [w for w in expanded if w]
    if not expanded:
        return [raw.lower()]
    lower_parts = [w.lower() for w in expanded]
    kebab = "-".join(lower_parts)
    snake = "_".join(lower_parts)
    lower = "".join(lower_parts)
    camel = lower_parts[0] + "".join(w.capitalize() for w in lower_parts[1:])
    variants = list({kebab, snake, lower, camel.lower(), raw.lower()})
    return variants
