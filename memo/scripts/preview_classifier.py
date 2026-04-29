#!/usr/bin/env python3
"""Preview-only: run the frozen classifier against the validation corpus, print breakdown + samples.

No ground-truth needed. Lets Bernard eyeball what L1/L2/L3/L4 catch before labelling.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from email_poller import _classify  # type: ignore

CSV_PATH = Path.home() / ".ship/memo-email-poller-rebuild/experiments/validation-corpus.csv"


def main() -> int:
    if not CSV_PATH.exists():
        sys.stderr.write(f"corpus not found: {CSV_PATH}\n")
        return 1

    rows = list(csv.DictReader(CSV_PATH.open()))
    by_layer: dict[str, list[dict]] = defaultdict(list)
    counter: Counter = Counter()

    for r in rows:
        # build a parsed-message dict matching what _classify expects
        # extract bare email from "Name <addr@host>" form
        from_full = r["from"]
        if "<" in from_full and ">" in from_full:
            from_addr = from_full.split("<", 1)[1].rstrip(">").strip().lower()
        else:
            from_addr = from_full.strip().lower()
        parsed = {
            "from_addr": from_addr,
            "subject": r["subject"],
            "body_raw": r["snippet"],
            "headers": (
                [{"name": "List-Unsubscribe", "value": "<x>"}]
                if r.get("has_list_unsubscribe", "").upper() == "TRUE"
                else []
            ),
        }
        verdict, reason = _classify(parsed)
        layer = reason.split(":")[0]  # "L1"/"L2"/"L3"/"L4"
        counter[(verdict, layer)] += 1
        by_layer[layer].append({**r, "_verdict": verdict, "_reason": reason})

    print(f"\n=== preview against {len(rows)} corpus rows ===\n")
    print("verdict counts:")
    total_surface = sum(c for (v, _), c in counter.items() if v == "surface")
    total_suppress = sum(c for (v, _), c in counter.items() if v == "suppress")
    print(f"  surface: {total_surface} ({100*total_surface/len(rows):.0f}%)")
    print(f"  suppress: {total_suppress} ({100*total_suppress/len(rows):.0f}%)")

    print("\nby layer:")
    for layer in ("L1", "L2", "L3", "L4"):
        n = sum(c for (_, lyr), c in counter.items() if lyr == layer)
        v = "suppress" if layer in ("L1", "L3", "L4") else "surface"
        print(f"  {layer} ({v}): {n}")

    print("\n=== samples (first 5 per layer) ===\n")
    for layer in ("L1", "L2", "L3", "L4"):
        rows_l = by_layer.get(layer, [])
        if not rows_l:
            continue
        print(f"--- {layer} ({len(rows_l)} total) ---")
        for r in rows_l[:5]:
            sender = r["from"][:40]
            subj = r["subject"][:60]
            reason = r["_reason"]
            print(f"  [{r['_verdict']:>8}] {sender:<40} | {subj:<60} | {reason}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
