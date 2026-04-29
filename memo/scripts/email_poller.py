#!/usr/bin/env python3
"""
memo-v2 Email channel poller (Slice S5; rebuild Slice 3 — 4-layer classifier).

Polls Gmail using inbox-triage query (Gmail-side category suppress + label exclusion):
  is:unread newer_than:1d -category:promotions -category:social
  -category:updates -category:forums -label:memo-processed

For each fetched message a 4-layer classifier emits surface/suppress:
  L1 hard-suppress  — list-unsubscribe header / bulk-mail platform / promo subject
  L2 hard-surface   — allowlist email or @domain (email_allowlist.txt) / action subject
  L3 auto-noise     — receipt / OTP / calendar auto-confirm
  L4 default        — suppress (conservative; avoid memo flood)
Surface verdict -> parse #tags, strip HTML, truncate to 2KB,
_writer.write_memo(channel='email', source=<from-addr>), apply `memo-processed`
label. Suppress verdict -> apply label only (no memo, no UNREAD change).
The `memo-processed` Gmail label is non-destructive (UNREAD preserved); re-fetch
is blocked via `-label:memo-processed` in GMAIL_QUERY.

Auth: Direct Gmail API via google-api-python-client + OAuth2 refresh token
stored at ~/.claude/skills/memo/scripts/.gmail_token.json (gitignored).
First-run setup: python3 email_poller.py --auth (browser flow).
After that, --poll runs unattended in cron context.

Entry points:
  --auth     : launch browser OAuth flow, save refresh token
  --poll     : fetch unread, write memos, mark read
  --dry-run  : like --poll but does NOT mark read or write files

See ~/.ship/memo-v2/goals/01-spec.md §4.2 + 02-plan.md §2.5.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from email.utils import parseaddr
from pathlib import Path

# Path setup so we can import _writer + scribble's tag extractor
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# Gmail token + OAuth client config locations
TOKEN_PATH = _HERE / ".gmail_token.json"
CLIENT_SECRETS_PATH = _HERE / ".gmail_client_secrets.json"

# Gmail API scope: read messages + modify labels (mark read)
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Hard-surface allowlist file (Slice 3). Bernard-edited file with email + @domain
# entries; loaded on first classify, re-loaded on mtime change. Replaces
# Slice 1/2 ALLOWED_SENDERS frozenset (now removed).
ALLOWLIST_PATH = _HERE / "email_allowlist.txt"
_ALLOWLIST_CACHE: dict = {"mtime": 0.0, "emails": frozenset(), "domains": frozenset()}

# Gmail query — inbox-triage (Slice 1 rebuild). Gmail-side category suppress
# + label-based idempotency (label-add Slice 2). 4-layer classifier (L1 hard-
# suppress / L2 hard-surface / L3 auto-noise / L4 default-suppress) lands Slice 3.
GMAIL_QUERY = (
    "is:unread newer_than:1d "
    "-category:promotions -category:social -category:updates -category:forums "
    "-label:memo-processed"
)

# Body truncation cap (2KB per spec §4.2)
BODY_MAX_BYTES = 2048
TRUNCATED_MARKER = "\n\n[truncated]"

# Gmail label name applied to processed emails (Slice 2). Non-destructive:
# email's UNREAD state is preserved. Re-fetch suppression via -label:memo-processed
# in GMAIL_QUERY. Module-level cache keyed by label name → Gmail label id;
# survives across calls within one process invocation.
MEMO_PROCESSED_LABEL = "memo-processed"
_LABEL_ID_CACHE: dict[str, str] = {}

# ───────────────────────── Classifier regexes (Slice 3 — FROZEN) ─────────────────────────
# Authored from audit §A scenarios + §B taxonomy + general email-noise priors.
# DO NOT tune by sampling Bernard's inbox — tautological. Slice 4 extracts a
# held-out validation corpus; Slice 5 measures recall + FP rate. If Slice 5
# fails the gate, escalate to Bernard for a new authoring round; do not patch here.

# L1: bulk-mail platforms (sender domain). Common ESP / newsletter / drip platforms.
_SUPPRESS_DOMAIN_RE = re.compile(
    r"(?:mailchimp\.com|sendgrid\.net|mandrillapp\.com|mailgun\.org|amazonses\.com"
    r"|sparkpostmail\.com|mktomail\.com|marketo\.com|hubspot(?:email)?\.com"
    r"|intercom\.help|customer\.io|klaviyo\.com|substack\.com|convertkit\.com"
    r"|beehiiv\.com|mail\.beehiiv\.com)$",
    re.IGNORECASE,
)

# L1: promo subject keywords.
_PROMO_SUBJECT_RE = re.compile(
    r"(?i)\b(unsubscribe|sale|discount|% off|deal|webinar|whitepaper"
    r"|exclusive offer|limited time|free trial)\b"
)

# L2: action / urgency subject keywords.
_ACTION_SUBJECT_RE = re.compile(
    r"(?i)\b(urgent|action required|action needed|please review|please sign"
    r"|sign here|verify|confirm|deadline|due (?:today|tomorrow|by)"
    r"|by (?:friday|monday|tuesday|wednesday|thursday|saturday|sunday|EOD|EOW)"
    r"|past due|overdue|expir(?:es?|ing)|reminder:|response needed"
    r"|reply needed|important|critical)\b"
)

# L3: receipt / order confirmation subject keywords.
_RECEIPT_RE = re.compile(
    r"(?i)\b(receipt|order #?\w+|order confirmation|invoice"
    r"|payment (?:received|confirmation)|your (?:order|purchase)"
    r"|thanks for (?:your )?(?:order|purchase|subscription))\b"
)

# L3: OTP / 2FA verification body pattern (6-digit code AND verify keyword,
# either order). Two re.search calls cheaper than one alternation backtrack.
_OTP_DIGITS_RE = re.compile(r"\b\d{6}\b")
_OTP_VERB_RE = re.compile(r"(?i)(?:verif|confirm|2fa|two.factor|one.time (?:code|password)|otp\b|security code|access code)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s email_poller %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


# ───────────────────────── Tag parsing (mirrors scribble.py) ─────────────────────────

# Same regex as scribble._TAG_RE — keep in sync.
_TAG_RE = re.compile(r"(?:^|\s)#([a-z][a-z0-9-]{2,30})(?=\s|$)")


def _extract_tags(text: str) -> tuple[str, list[str]]:
    """Return (text_with_tags_removed, [tags...]).

    Mirrors scribble._extract_tags. Duplicated rather than imported to keep
    poller importable when scribble.py is refactored. Both files reference
    01-spec.md §4.2 / R3 for the canonical regex.
    """
    tags: list[str] = []
    seen: set[str] = set()
    for m in _TAG_RE.finditer(text):
        t = m.group(1)
        if t not in seen:
            seen.add(t)
            tags.append(t)

    def _sub(match: re.Match) -> str:
        leading = match.group(0)[: match.start(1) - match.start() - 1]
        return " " if leading else ""

    cleaned = _TAG_RE.sub(_sub, text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, tags


# ───────────────────────── HTML → plain text ─────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HTML_P_RE = re.compile(r"</p>", re.IGNORECASE)


def _html_to_text(html: str) -> str:
    """Lightweight HTML → plain text. No external dep.

    Replaces <br>/<br/> + </p> with newlines, strips other tags, decodes
    common entities. Sufficient for Gmail's mostly-clean HTML; not a full
    HTML5 parser. Falls back to html2text if installed (richer output).
    """
    try:
        import html2text  # type: ignore

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0  # don't wrap
        return h.handle(html).strip()
    except ImportError:
        pass

    # Pure-stdlib fallback
    text = _HTML_BR_RE.sub("\n", html)
    text = _HTML_P_RE.sub("\n", text)
    text = _HTML_TAG_RE.sub("", text)
    # Decode minimal entities
    import html as _html_mod
    text = _html_mod.unescape(text)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _truncate_body(body: str) -> str:
    """Truncate to BODY_MAX_BYTES, append TRUNCATED_MARKER if cut."""
    encoded = body.encode("utf-8")
    if len(encoded) <= BODY_MAX_BYTES:
        return body
    # Cut at byte boundary then back off to last whitespace to avoid mid-word
    cut = encoded[:BODY_MAX_BYTES].decode("utf-8", errors="ignore")
    # Trim back to last whitespace (best-effort)
    last_ws = max(cut.rfind(" "), cut.rfind("\n"))
    if last_ws > 0 and last_ws > BODY_MAX_BYTES - 200:
        cut = cut[:last_ws]
    return cut.rstrip() + TRUNCATED_MARKER


# ───────────────────────── Gmail message parsing ─────────────────────────

def _extract_header(headers: list[dict], name: str) -> str:
    target = name.lower()
    for h in headers:
        if h.get("name", "").lower() == target:
            return h.get("value", "")
    return ""


def _walk_parts_for_body(payload: dict) -> tuple[str, str]:
    """Return (plain_text, html). Either may be ''. Prefer plain over html."""
    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    def _walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")
        if data:
            import base64
            try:
                decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            except Exception:
                decoded = ""
            if mime == "text/plain":
                plain_chunks.append(decoded)
            elif mime == "text/html":
                html_chunks.append(decoded)
        for sub in part.get("parts", []) or []:
            _walk(sub)

    _walk(payload)
    return "\n".join(plain_chunks).strip(), "\n".join(html_chunks).strip()


def _parse_message(msg: dict) -> dict | None:
    """Return parsed dict {from_addr, subject, body, msg_id} or None to discard."""
    msg_id = msg.get("id", "")
    payload = msg.get("payload", {}) or {}
    headers = payload.get("headers", []) or []

    from_raw = _extract_header(headers, "From")
    subject = _extract_header(headers, "Subject")
    _, from_addr = parseaddr(from_raw)
    from_addr = from_addr.lower().strip()

    plain, html = _walk_parts_for_body(payload)
    if plain:
        body_text = plain
    elif html:
        body_text = _html_to_text(html)
    else:
        body_text = ""

    return {
        "msg_id": msg_id,
        "from_addr": from_addr,
        "subject": subject,
        "body_raw": body_text,
        "headers": headers,  # Slice 3: classifier reads List-Unsubscribe
    }


# ───────────────────────── Auth / Gmail service ─────────────────────────

def _load_credentials():
    """Load + refresh OAuth credentials. Exit 1 if no token (unless caller is --auth)."""
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
    except ImportError as e:
        sys.stderr.write(
            "email_poller: missing google auth deps — install with:\n"
            "  pip3 install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib html2text\n"
            f"(import error: {e})\n"
        )
        sys.exit(1)

    if not TOKEN_PATH.exists():
        sys.stderr.write(
            f"email_poller: no token at {TOKEN_PATH}\n"
            "run --auth first to complete one-time OAuth flow:\n"
            f"  python3 {Path(__file__).name} --auth\n"
        )
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
        os.chmod(TOKEN_PATH, 0o600)
    return creds


def _build_service(creds):
    from googleapiclient.discovery import build  # type: ignore
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _get_or_create_label(service, label_name: str = MEMO_PROCESSED_LABEL) -> str:
    """Return the Gmail label id for `label_name`, creating it if absent.

    Module-level cache (_LABEL_ID_CACHE) skips API calls on subsequent invocations
    within the same process. On cache miss, lists user labels and returns id if
    present; otherwise creates the label (visible in label list + message list)
    and returns the new id. `gmail.modify` scope covers both labels.list and
    labels.create. Raises googleapiclient.errors.HttpError on API failure with
    the original error context preserved.
    """
    cached = _LABEL_ID_CACHE.get(label_name)
    if cached:
        log.debug("label cache HIT: %s -> %s", label_name, cached)
        return cached

    from googleapiclient.errors import HttpError  # type: ignore

    try:
        existing = service.users().labels().list(userId="me").execute()
    except HttpError as e:
        raise RuntimeError(f"labels.list failed for {label_name!r}: {e}") from e

    for lab in existing.get("labels", []) or []:
        if lab.get("name") == label_name:
            label_id = lab.get("id", "")
            _LABEL_ID_CACHE[label_name] = label_id
            log.debug("label cache MISS, found existing: %s -> %s", label_name, label_id)
            return label_id

    try:
        created = service.users().labels().create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"labels.create failed for {label_name!r}: {e}") from e

    label_id = created.get("id", "")
    _LABEL_ID_CACHE[label_name] = label_id
    log.info("label created: %s -> %s", label_name, label_id)
    return label_id


# ───────────────────────── Classifier (Slice 3 — 4-layer, FROZEN) ─────────────────────────

def _load_allowlist(path: Path = ALLOWLIST_PATH) -> tuple[frozenset[str], frozenset[str]]:
    """Return (emails, domains) read from `path`. mtime-cached.

    Format: one entry per line. `@example.com` -> domain. `foo@bar.com` -> email.
    `#` starts a comment. Blank lines + comment lines ignored. Malformed lines
    (no `@` at all) are logged and skipped (never crash). On mtime change vs
    cached value, file is re-read; otherwise returns cached frozensets.
    Missing file -> empty sets (default-suppress for unknown senders is fine
    given L4 default).
    """
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        # File absent -> empty allowlist; refresh cache so we don't re-stat next call
        if _ALLOWLIST_CACHE.get("mtime") != -1.0:
            _ALLOWLIST_CACHE["mtime"] = -1.0
            _ALLOWLIST_CACHE["emails"] = frozenset()
            _ALLOWLIST_CACHE["domains"] = frozenset()
            log.warning("allowlist file absent at %s — using empty allowlist", path)
        return _ALLOWLIST_CACHE["emails"], _ALLOWLIST_CACHE["domains"]

    if mtime == _ALLOWLIST_CACHE.get("mtime"):
        return _ALLOWLIST_CACHE["emails"], _ALLOWLIST_CACHE["domains"]

    emails: set[str] = set()
    domains: set[str] = set()
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        log.error("allowlist read failed for %s: %s", path, e)
        return _ALLOWLIST_CACHE["emails"], _ALLOWLIST_CACHE["domains"]

    for lineno, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("@"):
            dom = s[1:].lower()
            if "@" in dom or "." not in dom:
                log.warning("allowlist line %d malformed domain %r — skipped", lineno, s)
                continue
            domains.add(dom)
        elif "@" in s:
            emails.add(s.lower())
        else:
            log.warning("allowlist line %d malformed (no '@') %r — skipped", lineno, s)

    _ALLOWLIST_CACHE["mtime"] = mtime
    _ALLOWLIST_CACHE["emails"] = frozenset(emails)
    _ALLOWLIST_CACHE["domains"] = frozenset(domains)
    log.info(
        "allowlist loaded from %s: %d emails, %d domains",
        path.name, len(emails), len(domains),
    )
    return _ALLOWLIST_CACHE["emails"], _ALLOWLIST_CACHE["domains"]


def _classify(parsed: dict) -> tuple[str, str]:
    """Return (verdict, reason) where verdict ∈ {'surface', 'suppress'}.

    4-layer evaluation in order: L1 hard-suppress -> L2 hard-surface ->
    L3 auto-noise -> L4 default-suppress. L2 BEATS L3 (allowlist sender with
    'Receipt' subject still surfaces). Reasons are human-readable strings
    suitable for log output + per-layer counters.
    """
    sender = parsed.get("from_addr", "") or ""
    subject = parsed.get("subject", "") or ""
    body = parsed.get("body_raw", "") or ""
    headers = parsed.get("headers", []) or []
    domain = sender.split("@", 1)[1].lower() if "@" in sender else ""

    # L1: hard-suppress
    for h in headers:
        if h.get("name", "").lower() == "list-unsubscribe":
            return ("suppress", "L1: list-unsubscribe header")
    if domain and _SUPPRESS_DOMAIN_RE.search(domain):
        return ("suppress", f"L1: bulk-mail platform {domain}")
    if subject and _PROMO_SUBJECT_RE.search(subject):
        return ("suppress", "L1: promo subject")

    # L2: hard-surface (overrides L3+L4)
    emails, domains = _load_allowlist()
    if sender and sender in emails:
        return ("surface", f"L2: allowlist email {sender}")
    if domain and domain in domains:
        return ("surface", f"L2: allowlist domain @{domain}")
    if subject and _ACTION_SUBJECT_RE.search(subject):
        return ("surface", "L2: action keyword")

    # L3: auto-noise
    if subject and _RECEIPT_RE.search(subject):
        return ("suppress", "L3: receipt")
    if body and _OTP_RE.search(body):
        return ("suppress", "L3: OTP")
    if domain == "calendar-notification.google.com" and "Invitation:" in subject:
        return ("suppress", "L3: calendar auto-confirm")

    # L4: default-suppress (conservative — avoid memo flood for unknown senders)
    return ("suppress", "L4: no rule fired (default-suppress)")


def _run_auth_flow() -> int:
    """One-time browser OAuth flow. Saves refresh token to TOKEN_PATH."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    except ImportError:
        sys.stderr.write(
            "email_poller: missing google-auth-oauthlib — install with:\n"
            "  pip3 install --user google-auth-oauthlib\n"
        )
        return 1

    if not CLIENT_SECRETS_PATH.exists():
        sys.stderr.write(
            f"email_poller: no client secrets at {CLIENT_SECRETS_PATH}\n"
            "create an OAuth2 Desktop client at https://console.cloud.google.com/apis/credentials\n"
            f"download the JSON and save it as: {CLIENT_SECRETS_PATH}\n"
            "then re-run --auth\n"
        )
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_PATH), GMAIL_SCOPES)
    # run_local_server opens browser, listens on a random port for redirect
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)
    log.info("auth complete — token saved to %s", TOKEN_PATH)
    return 0


# ───────────────────────── Poll loop ─────────────────────────

def _process_message(
    parsed: dict,
    *,
    dry_run: bool,
    service=None,
    label_id: str = "",
) -> str:
    """Process one parsed message. Returns one-word verdict for log.

    `label_id` (Slice 2) is the cached id of `memo-processed`; required when
    `service is not None` (i.e. live mode). Applied via addLabelIds — this is
    non-destructive (does NOT mark the email read).
    """
    from_addr = parsed["from_addr"]
    subject = parsed["subject"]
    body_raw = parsed["body_raw"]
    msg_id = parsed["msg_id"]

    # Slice 3: 4-layer classifier replaces sender allowlist gate.
    # L1 hard-suppress / L2 hard-surface / L3 auto-noise / L4 default-suppress.
    verdict, reason = _classify(parsed)
    log.info(
        "classify: %s (%s) — from=%s subj=%s",
        verdict, reason, from_addr, subject[:60],
    )
    if verdict == "suppress":
        # Apply label so we don't re-fetch this email next poll. Skip memo write.
        if not dry_run and service is not None and label_id:
            try:
                service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"addLabelIds": [label_id]},
                ).execute()
            except Exception as e:
                log.error("label-apply failed for suppressed %s: %s", msg_id, e)
        return f"suppress:{reason.split(':', 1)[0]}"  # e.g. "suppress:L1"

    # Combine subject + body for tag extraction. Subject:MEMO prefix gating
    # removed in Slice 1 rebuild — subject is no longer required to start with "MEMO".
    subject_for_tags = subject
    combined = subject_for_tags.strip() + "\n\n" + body_raw.strip()

    cleaned, tags = _extract_tags(combined)
    body_final = _truncate_body(cleaned.strip() or subject_for_tags or "(empty)")

    if dry_run:
        log.info("DRY: would write from=%s tags=%s len=%d", from_addr, tags, len(body_final))
        return "dry-write"

    # Late import — _writer pulls in index.py with its own paths
    from _writer import write_memo  # noqa: E402

    path = write_memo(
        body=body_final,
        channel="email",
        source=from_addr,
        tags=tags,
    )
    log.info("write: %s tags=%s from=%s", path.name, tags, from_addr)

    # Apply non-destructive `memo-processed` label (Slice 2). Email's UNREAD
    # state is preserved. Re-fetch suppressed via -label:memo-processed in
    # GMAIL_QUERY on next poll.
    if service is not None:
        if not label_id:
            log.error("label-apply skipped for %s: missing label_id (caller bug)", msg_id)
            return "write-but-not-labeled"
        try:
            service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"addLabelIds": [label_id]},
            ).execute()
        except Exception as e:
            log.error("label-apply failed for %s: %s", msg_id, e)
            return "write-but-not-labeled"
    return "write"


def _poll(*, dry_run: bool) -> int:
    creds = _load_credentials()
    service = _build_service(creds)

    # Slice 2: ensure label exists once per poll. Fail loud + exit 1 if cannot
    # ensure — without the label, dedup via -label:memo-processed cannot work
    # and every poll would re-process the same emails.
    label_id = ""
    if not dry_run:
        try:
            label_id = _get_or_create_label(service, MEMO_PROCESSED_LABEL)
        except Exception as e:
            log.error("FATAL: cannot ensure %s label: %s", MEMO_PROCESSED_LABEL, e)
            return 1

    resp = service.users().messages().list(userId="me", q=GMAIL_QUERY, maxResults=50).execute()
    msgs = resp.get("messages", []) or []
    log.info("poll: %d inbox candidates after Gmail-side suppress", len(msgs))

    # Slice 3: classifier emits suppress:L1 / L2 / L3 / L4 verdicts; per-layer
    # buckets seeded so log shows zero-fire layers explicitly.
    counts = {
        "write": 0, "dry-write": 0, "write-but-not-labeled": 0, "error": 0,
        "suppress:L1": 0, "suppress:L3": 0, "suppress:L4": 0,
    }
    for stub in msgs:
        try:
            full = service.users().messages().get(
                userId="me", id=stub["id"], format="full"
            ).execute()
            parsed = _parse_message(full)
            if parsed is None:
                continue
            verdict = _process_message(
                parsed,
                dry_run=dry_run,
                service=None if dry_run else service,
                label_id=label_id,
            )
            counts[verdict] = counts.get(verdict, 0) + 1
        except Exception as e:
            log.exception("error processing %s: %s", stub.get("id"), e)
            counts["error"] += 1

    log.info("poll done: %s", counts)
    return 0 if counts["error"] == 0 else 1


# ───────────────────────── Mock-poll for tests ─────────────────────────

def _mock_poll(mock_messages: list[dict], *, dry_run: bool = True) -> dict:
    """Run the parsing + dispatch logic against synthetic Gmail-shaped dicts.

    Used by RC-3 test. No network. mock_messages is a list of payload-shaped
    dicts matching `messages.get(format='full')` structure.
    """
    counts: dict[str, int] = {"write": 0, "dry-write": 0, "error": 0}
    written: list[str] = []

    for m in mock_messages:
        try:
            parsed = _parse_message(m)
            if parsed is None:
                continue
            verdict = _process_message(parsed, dry_run=dry_run, service=None)
            if verdict not in counts:
                counts[verdict] = 0
            counts[verdict] += 1
            if verdict == "write":
                # In non-dry mode we'd have a path; in dry we skip
                pass
        except Exception as e:
            log.exception("mock error: %s", e)
            counts["error"] += 1
    return counts


# ───────────────────────── Main ─────────────────────────

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="memo-v2 email channel poller")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--auth", action="store_true", help="run one-time browser OAuth flow")
    g.add_argument("--poll", action="store_true", help="fetch unread, write, apply memo-processed label")
    g.add_argument("--dry-run", action="store_true", help="like --poll but no writes/no label-apply")
    args = p.parse_args(argv)

    if args.auth:
        return _run_auth_flow()
    if args.poll:
        return _poll(dry_run=False)
    if args.dry_run:
        return _poll(dry_run=True)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
