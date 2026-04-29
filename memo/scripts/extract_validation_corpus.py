#!/usr/bin/env python3
"""extract_validation_corpus.py — Slice 4 corpus extractor.

Extracts TWO disjoint pools from Bernard's Inbox for Slice 5 measurement:

  Pool A — random Inbox sample (precision target):
      in:inbox newer_than:60d -label:memo-processed
      Sample 200 random messages.

  Pool B — Bernard-replied seeds (recall target):
      Inbox messages whose Message-ID appears as In-Reply-To in any of
      Bernard's last-60d Sent messages. Cap 50 candidates.

Writes ~/.ship/memo-email-poller-rebuild/experiments/validation-corpus.csv.
Bernard hand-labels label_required_action + label_reason; Slice 5 reads it.

CRITICAL: this script does NOT classify. No imports of _classify or any
regex constant from email_poller. Tainting check:

    grep -E "_classify|_SUPPRESS_DOMAIN_RE|_PROMO_SUBJECT_RE|_ACTION_SUBJECT_RE|_RECEIPT_RE|_OTP" extract_validation_corpus.py

must return ZERO matches.
"""
from __future__ import annotations

import csv
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Reuse auth + service helpers ONLY. Do NOT import classifier.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from email_poller import _build_service, _load_credentials  # type: ignore  # noqa: E402

OUT_DIR = Path.home() / ".ship" / "memo-email-poller-rebuild" / "experiments"
OUT_PATH = OUT_DIR / "validation-corpus.csv"

POOL_A_TARGET = 200
POOL_B_TARGET = 50
PAGE_SIZE = 500
MAX_INBOX_LIST = 4000  # cap how many inbox ids we'll list before sampling
MAX_SENT_LIST = 2000   # cap how many sent ids we'll scan for In-Reply-To

CSV_FIELDS = [
    "pool", "msgid", "from", "subject", "internal_date",
    "snippet", "has_list_unsubscribe", "has_bernard_reply",
    "label_required_action", "label_reason",
]


def _list_ids(service, query: str, cap: int) -> list[str]:
    """Page through messages.list, return ids capped at `cap`."""
    ids: list[str] = []
    page_token = None
    while len(ids) < cap:
        resp: dict = {}
        for attempt in range(2):
            try:
                resp = service.users().messages().list(
                    userId="me", q=query,
                    maxResults=PAGE_SIZE, pageToken=page_token,
                ).execute()
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 0:
                    sys.stderr.write(f"corpus: list retry after {e}\n")
                    time.sleep(2)
                    continue
                raise
        for m in resp.get("messages", []) or []:
            ids.append(m["id"])
            if len(ids) >= cap:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def _get_metadata(service, msgid: str, headers: list[str]) -> dict | None:
    for attempt in range(2):
        try:
            return service.users().messages().get(
                userId="me", id=msgid,
                format="metadata", metadataHeaders=headers,
            ).execute()
        except Exception as e:  # noqa: BLE001
            if attempt == 0:
                time.sleep(1)
                continue
            sys.stderr.write(f"corpus: skip {msgid}: {e}\n")
            return None
    return None


def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []) or []:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "") or ""
    return ""


def _to_iso(internal_date_ms: str) -> str:
    try:
        ms = int(internal_date_ms)
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_replied_msgid_set(service) -> set[str]:
    """Scan Bernard's recent Sent for In-Reply-To headers; collect referenced Message-IDs."""
    sys.stderr.write("corpus: listing Sent for reply-graph (60d, cap 2000)…\n")
    sent_ids = _list_ids(service, "in:sent newer_than:60d", MAX_SENT_LIST)
    sys.stderr.write(f"corpus: scanning {len(sent_ids)} Sent messages for In-Reply-To…\n")
    referenced: set[str] = set()
    for i, sid in enumerate(sent_ids, 1):
        if i % 200 == 0:
            sys.stderr.write(f"corpus: sent {i}/{len(sent_ids)}…\n")
        msg = _get_metadata(service, sid, ["In-Reply-To", "References"])
        if not msg:
            continue
        irt = _header(msg, "In-Reply-To").strip()
        refs = _header(msg, "References").strip()
        for token in (irt + " " + refs).split():
            t = token.strip().strip("<>").strip()
            if t:
                referenced.add(t)
    return referenced


def _row_for(service, msgid: str, pool: str, replied_set: set[str]) -> dict | None:
    msg = _get_metadata(service, msgid, ["From", "Subject", "Message-ID", "List-Unsubscribe"])
    if not msg:
        return None
    has_lu = bool(_header(msg, "List-Unsubscribe").strip())
    raw_msgid = _header(msg, "Message-ID").strip().strip("<>").strip()
    has_reply = (pool == "B") or (raw_msgid in replied_set if raw_msgid else False)
    return {
        "pool": pool,
        "msgid": msgid,
        "from": _header(msg, "From"),
        "subject": _header(msg, "Subject"),
        "internal_date": _to_iso(msg.get("internalDate", "")),
        "snippet": (msg.get("snippet", "") or "")[:200],
        "has_list_unsubscribe": "TRUE" if has_lu else "FALSE",
        "has_bernard_reply": "TRUE" if has_reply else "FALSE",
        "label_required_action": "",
        "label_reason": "",
    }


def main() -> int:
    creds = _load_credentials()
    service = _build_service(creds)

    # Pool A: random Inbox sample.
    sys.stderr.write("corpus: listing Inbox (60d, cap 4000)…\n")
    inbox_ids = _list_ids(
        service,
        "in:inbox newer_than:60d -label:memo-processed",
        MAX_INBOX_LIST,
    )
    random.seed(42)  # deterministic sample for reproducibility
    pool_a_ids = (random.sample(inbox_ids, POOL_A_TARGET)
                  if len(inbox_ids) > POOL_A_TARGET else inbox_ids)
    sys.stderr.write(f"corpus: Pool A = {len(pool_a_ids)} (from {len(inbox_ids)} inbox ids)\n")

    # Pool B: messages Bernard replied to.
    replied = _build_replied_msgid_set(service)
    sys.stderr.write(f"corpus: collected {len(replied)} replied Message-IDs from Sent\n")

    # Scan Inbox ids again to find ones whose Message-ID is in `replied`.
    pool_b_rows: list[dict] = []
    pool_a_set = set(pool_a_ids)
    sys.stderr.write("corpus: scanning Inbox for Bernard-replied seeds…\n")
    for i, mid in enumerate(inbox_ids, 1):
        if len(pool_b_rows) >= POOL_B_TARGET:
            break
        if i % 500 == 0:
            sys.stderr.write(f"corpus: inbox-scan {i}/{len(inbox_ids)} (B so far {len(pool_b_rows)})…\n")
        if mid in pool_a_set:
            continue  # avoid pool-overlap; A is the precision pool
        msg = _get_metadata(service, mid, ["Message-ID"])
        if not msg:
            continue
        raw = _header(msg, "Message-ID").strip().strip("<>").strip()
        if raw and raw in replied:
            row = _row_for(service, mid, "B", replied)
            if row:
                pool_b_rows.append(row)

    # Pool A rows.
    sys.stderr.write(f"corpus: fetching Pool A details ({len(pool_a_ids)})…\n")
    pool_a_rows: list[dict] = []
    for i, mid in enumerate(pool_a_ids, 1):
        if i % 50 == 0:
            sys.stderr.write(f"corpus: A {i}/{len(pool_a_ids)}…\n")
        row = _row_for(service, mid, "A", replied)
        if row:
            pool_a_rows.append(row)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in pool_a_rows + pool_b_rows:
            w.writerow(r)

    sys.stderr.write(
        f"corpus: extracted {len(pool_a_rows)} from Pool A + {len(pool_b_rows)} from Pool B, "
        f"wrote to {OUT_PATH}\n"
    )
    sys.stderr.write(
        "\nNext step (Bernard):\n"
        "  Open the CSV in Numbers/Excel.\n"
        "  For each row, set label_required_action to YES or NO.\n"
        "  YES = if you saw this email today, you'd need to do something (reply, click, sign, pay attention).\n"
        "  NO = noise / promo / receipt / FYI / done-without-action.\n"
        "  Save the file. Slice 5 reads it.\n"
        f"Estimated time: ~25-35 min for {len(pool_a_rows) + len(pool_b_rows)} rows.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
