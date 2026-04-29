#!/usr/bin/env python3
"""bootstrap_allowlist.py — Slice 4 helper.

Reads Bernard's last-90d Sent folder, aggregates To:/Cc: recipients,
writes a review-then-merge proposal to email_allowlist.proposal.txt.

Reuses _load_credentials + _build_service from email_poller.py
(do not duplicate). Usage:

    python3 bootstrap_allowlist.py

No args. Prints summary to stderr.
"""
from __future__ import annotations

import sys
import time
from collections import defaultdict
from datetime import datetime
from email.utils import getaddresses
from pathlib import Path

# Reuse poller auth + service helpers (no duplication, per Slice 4 contract).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from email_poller import _build_service, _load_credentials  # type: ignore  # noqa: E402

PROPOSAL_PATH = _HERE / "email_allowlist.proposal.txt"

# Bernard's own addresses — never propose self.
SELF_ADDRESSES = {"bernard.ngb@gmail.com", "okaybernard@gmail.com"}

# Local-part substrings that mean "do not reply" — skip even as recipient.
NOREPLY_SUBSTRINGS = ("noreply", "no-reply", "donotreply", "do-not-reply",
                      "bounce", "mailer-daemon")

# Page cap: Gmail returns ~500/page; 4 pages × 500 = 2000 messages max.
MAX_MESSAGES = 2000
PAGE_SIZE = 500

# Promotional-replyto guard: if Bernard wrote >=10 messages to one address,
# it's likely a transactional reply-to, not a real correspondent.
SPAM_REPLY_THRESHOLD = 10

# Domain promotion threshold: >=3 distinct addresses at one domain → suggest @domain.
DOMAIN_PROMOTE_DISTINCT = 3


def _list_sent_message_ids(service) -> list[str]:
    """Page through Sent in last 90d, return message ids (capped)."""
    ids: list[str] = []
    page_token = None
    while len(ids) < MAX_MESSAGES:
        resp: dict = {}
        for attempt in range(2):
            try:
                resp = service.users().messages().list(
                    userId="me",
                    q="in:sent newer_than:90d",
                    maxResults=PAGE_SIZE,
                    pageToken=page_token,
                ).execute()
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 0:
                    sys.stderr.write(f"bootstrap: list retry after {e}\n")
                    time.sleep(2)
                    continue
                raise
        for m in resp.get("messages", []) or []:
            ids.append(m["id"])
            if len(ids) >= MAX_MESSAGES:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def _extract_recipients(service, msgid: str) -> list[str]:
    """Fetch To: + Cc: headers; return list of normalized email addresses."""
    for attempt in range(2):
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msgid,
                format="metadata",
                metadataHeaders=["To", "Cc"],
            ).execute()
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 0:
                time.sleep(1)
                continue
            sys.stderr.write(f"bootstrap: skip {msgid}: {e}\n")
            return []
    headers = msg.get("payload", {}).get("headers", []) or []
    raw = []
    for h in headers:
        if h.get("name", "").lower() in ("to", "cc"):
            raw.append(h.get("value", ""))
    out: list[str] = []
    for addr_name, addr in getaddresses(raw):
        addr = (addr or "").strip().lower()
        if "@" in addr:
            out.append(addr)
    return out


def _filter_addr(addr: str) -> bool:
    """True if the address should be considered for the allowlist."""
    if addr in SELF_ADDRESSES:
        return False
    local = addr.split("@", 1)[0]
    return all(s not in local for s in NOREPLY_SUBSTRINGS)


def main() -> int:
    creds = _load_credentials()
    service = _build_service(creds)

    sys.stderr.write("bootstrap: listing Sent (90d, cap 2000)…\n")
    ids = _list_sent_message_ids(service)
    sys.stderr.write(f"bootstrap: scanning {len(ids)} messages…\n")

    per_email: dict[str, int] = defaultdict(int)
    per_domain_addrs: dict[str, set[str]] = defaultdict(set)
    per_domain_msgs: dict[str, int] = defaultdict(int)

    for i, mid in enumerate(ids, 1):
        if i % 200 == 0:
            sys.stderr.write(f"bootstrap: {i}/{len(ids)}…\n")
        for addr in _extract_recipients(service, mid):
            if not _filter_addr(addr):
                continue
            per_email[addr] += 1
            try:
                domain = addr.split("@", 1)[1]
            except IndexError:
                continue
            per_domain_addrs[domain].add(addr)
            per_domain_msgs[domain] += 1

    # Promo-replyto filter: drop emails written >= SPAM_REPLY_THRESHOLD times.
    pruned = {a: c for a, c in per_email.items() if c < SPAM_REPLY_THRESHOLD}

    # Domain candidates: >=DOMAIN_PROMOTE_DISTINCT distinct addrs.
    domain_candidates = sorted(
        ((d, len(per_domain_addrs[d]), per_domain_msgs[d])
         for d in per_domain_addrs
         if len(per_domain_addrs[d]) >= DOMAIN_PROMOTE_DISTINCT),
        key=lambda t: t[2], reverse=True,
    )
    domain_set = {d for d, _, _ in domain_candidates}

    # Individual emails: written >=2 times AND domain not already suggested.
    indiv = sorted(
        ((a, c) for a, c in pruned.items()
         if c >= 2 and a.split("@", 1)[1] not in domain_set),
        key=lambda t: t[1], reverse=True,
    )

    ts = datetime.now().strftime("%Y-%m-%d %H:%M HKT")
    lines: list[str] = [
        f"# Bootstrap proposal generated {ts}",
        f"# Source: 90d Sent folder, {len(ids)} messages scanned",
        "# Review each line; uncomment to add to email_allowlist.txt",
        "# Then `cat email_allowlist.proposal.txt >> email_allowlist.txt` after manual review",
        "",
    ]

    if not ids:
        lines.append("# WARNING: Sent folder empty for 90d window; nothing to propose.")
    else:
        lines.append("# === domains (>=3 distinct addresses written) ===")
        if not domain_candidates:
            lines.append("# (none met threshold)")
        for d, distinct, msgs in domain_candidates:
            sample = sorted(per_domain_addrs[d])[:3]
            sample_s = ", ".join(a.split("@", 1)[0] + "@" for a in sample)
            lines.append(f"# @{d}   ({msgs} msgs across {distinct} addresses: {sample_s})")
        lines.append("")
        lines.append("# === individual emails (>=2 msgs, domain not above) ===")
        if not indiv:
            lines.append("# (none met threshold)")
        for addr, c in indiv:
            lines.append(f"# {addr}   ({c} msgs)")

    PROPOSAL_PATH.write_text("\n".join(lines) + "\n")

    sys.stderr.write(
        f"bootstrap: scanned {len(ids)} messages, found {len(per_email)} unique recipients, "
        f"{len(per_domain_addrs)} domains, wrote proposal to {PROPOSAL_PATH}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
