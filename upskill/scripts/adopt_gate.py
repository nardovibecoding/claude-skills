#!/usr/bin/env python3
"""adopt_gate.py — /upskill v2 Phase 6 adopt confirm gate (S5 slice).

Reads overlay.py output JSON. For ADOPT-EXT top-1 candidates only, prompts
user `Adopt this skill? [Y/n/skip]`. Outputs decision JSON for extract.py.

Spec: ~/.ship/upskill/goals/01-spec.md A10a (line 222).
Iron Law: CONFIRM_BYPASS env or flag is FORBIDDEN — no auto-adopt path.

CLI:
  python3 adopt_gate.py --overlay <overlay.json> --out <decision.json>

Exit codes:
  0 = always (decision is encoded in output JSON, not exit code)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _write_out(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill v2 adopt gate (Phase 6)")
    ap.add_argument("--overlay", required=True, help="Path to overlay.py output JSON")
    ap.add_argument("--out", required=True, help="Path to write decision JSON")
    args = ap.parse_args()

    # Iron Law: refuse if CONFIRM_BYPASS is in environment (belt-and-suspenders check)
    import os
    if os.environ.get("CONFIRM_BYPASS"):
        print(
            "ERROR: CONFIRM_BYPASS is set. This is FORBIDDEN per adopt gate Iron Law.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load overlay JSON
    try:
        overlay = json.loads(Path(args.overlay).read_text())
    except Exception as e:
        _write_out(args.out, {"decision": "error", "reason": f"overlay_read_fail: {e}"})
        return 0

    ranked = overlay.get("ranked") or []

    # No candidates at all
    if not ranked:
        _write_out(args.out, {"decision": "n/a", "reason": "no_candidates"})
        return 0

    top1 = ranked[0]

    # Only fire for ADOPT-EXT; other categories (FIX-*, TRIM-*, CLEAN-HOUSE) skip gate
    if top1.get("ia_category") != "ADOPT-EXT":
        _write_out(
            args.out,
            {
                "decision": "n/a",
                "reason": "not_adopt_ext",
                "top1_category": top1.get("ia_category"),
            },
        )
        return 0

    # TTY guard: non-interactive context (cron/CI/piped) — abort immediately
    if not sys.stdin.isatty():
        _write_out(
            args.out,
            {
                "decision": "aborted_no_tty",
                "reason": "no_interactive_tty",
                "top1": {
                    "id": top1.get("id"),
                    "name": top1.get("name"),
                    "url": top1.get("url"),
                    "ia_category": top1.get("ia_category"),
                    "roi": top1.get("roi"),
                    "stars": top1.get("stars"),
                },
            },
        )
        return 0

    # Print 1-line summary
    print(
        f"[1] [{top1.get('ia_category')}] {top1.get('id')} — "
        f"ROI={top1.get('roi')} stars={top1.get('stars')} | {top1.get('url')}"
    )

    # Print description (truncated to 200 chars)
    desc = top1.get("description") or top1.get("name") or "(no description)"
    print(desc[:200])

    # Prompt user
    try:
        answer = input("Adopt this skill? [Y/n/skip]: ").strip()
    except EOFError:
        answer = ""

    top1_summary = {
        "id": top1.get("id"),
        "name": top1.get("name"),
        "url": top1.get("url"),
        "stars": top1.get("stars"),
        "ia_category": top1.get("ia_category"),
        "matched_keywords": top1.get("matched_keywords"),
        "roi": top1.get("roi"),
        "integration_cost_hours": top1.get("integration_cost_hours"),
    }

    if answer in ("Y", "y"):
        _write_out(args.out, {"decision": "adopt", "top1": top1_summary})
    elif answer == "skip":
        _write_out(
            args.out,
            {"decision": "skip", "reason": "user_skip", "top1": top1_summary},
        )
    else:
        # blank, "n", or anything else → abort
        _write_out(
            args.out,
            {"decision": "abort_user", "reason": "user_n", "top1": top1_summary},
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
