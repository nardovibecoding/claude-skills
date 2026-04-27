#!/usr/bin/env python3
"""
/bigd --since N diff renderer.

Reads ~/inbox/_summaries/consumed/<date>_bundle.json for the last N days,
compares finding_ids across days, prints NEW / RECURRING / RESOLVED panel.

Usage: python3 since_diff.py [DAYS]   (default 7)
"""
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def main(argv: list[str]) -> int:
    days = int(argv[1]) if len(argv) > 1 else 7
    today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
    window_dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    consumed_dir = os.path.expanduser("~/inbox/_summaries/consumed")

    per_day: dict[str, dict] = {}
    for d in window_dates:
        fp = f"{consumed_dir}/{d}_bundle.json"
        if not os.path.exists(fp):
            continue
        try:
            b = json.load(open(fp))
        except Exception:
            continue
        findings = {}
        for daemon_key, s in b.get("summaries", {}).items():
            for pa in s.get("proposed_actions", []):
                fid = pa.get("finding_id") or pa.get("id") or ""
                if not fid:
                    continue
                findings[fid] = {
                    "title": pa.get("title", "")[:80],
                    "risk": pa.get("risk", "?"),
                    "key": daemon_key,
                }
        per_day[d] = findings

    if not per_day:
        print(f"No bundles found in last {days} days under {consumed_dir}/")
        return 0

    sorted_dates = sorted(per_day.keys())
    latest = sorted_dates[-1]
    prior_union: set[str] = set()
    for d in sorted_dates[:-1]:
        prior_union.update(per_day[d].keys())
    latest_set = set(per_day[latest].keys())

    new_ids = latest_set - prior_union
    resolved_ids = prior_union - latest_set
    recurring_ids = latest_set & prior_union

    def recur_count(fid: str) -> int:
        return sum(1 for d in sorted_dates if fid in per_day.get(d, {}))

    print(
        f"=== /bigd --since {days}d | range {sorted_dates[0]} → {latest} "
        f"({len(per_day)} days w/ data) ===\n"
    )

    print(f"### 🆕 NEW today (not seen in prior {days-1} days) — {len(new_ids)}")
    for fid in sorted(new_ids):
        f = per_day[latest][fid]
        print(f"  [{f['risk']:6s}] {f['key']:20s}  {f['title']}")
    print()

    print(f"### 🔁 RECURRING (seen on multiple days, still open today) — {len(recurring_ids)}")
    for fid in sorted(recurring_ids, key=lambda x: -recur_count(x)):
        n = recur_count(fid)
        f = per_day[latest][fid]
        print(f"  [{f['risk']:6s}] {f['key']:20s}  ×{n}d  {f['title']}")
    print()

    print(f"### ✅ RESOLVED since prior days (not in today's bundle) — {len(resolved_ids)}")
    for fid in sorted(resolved_ids):
        for d in reversed(sorted_dates[:-1]):
            if fid in per_day[d]:
                f = per_day[d][fid]
                print(f"  [{f['risk']:6s}] {f['key']:20s}  (last seen {d})  {f['title']}")
                break
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
