#!/usr/bin/env python3
"""
Privacy Guard — scan files for personal/private details before publishing.

Blocks git push to public repos if personal identifiers are found.
Can also be used standalone: python3 privacy_guard.py /path/to/repo

Exit codes:
    0 = CLEAN (safe to publish)
    1 = BLOCKED (personal details found)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Personal identifiers to detect ──────────────────────────────────────
# Add your own patterns here. These are checked as case-insensitive regex.
PERSONAL_PATTERNS_FILE = Path.home() / ".claude" / "privacy_patterns.json"

DEFAULT_PATTERNS = {
    "names": [],           # e.g. ["bernard", "john doe"]
    "emails": [],          # e.g. ["me@example.com"]
    "paths": [],           # e.g. ["/Users/bernard", "/home/bernard"]
    "ips": [],             # e.g. ["157.180.28.14"]
    "hostnames": [],       # e.g. ["my-vps.example.com"]
    "usernames": [],       # e.g. ["mybot_username"]
    "keywords": [],        # e.g. ["my-company", "internal-project"]
}

# Always check for these generic patterns
GENERIC_PATTERNS = [
    r"/Users/\w+",                    # macOS home paths
    r"/home/\w+",                     # Linux home paths
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses (flagged for review)
    r"sk-[a-zA-Z0-9]{20,}",          # OpenAI keys
    r"ghp_[a-zA-Z0-9]{36}",          # GitHub PATs
    r"gho_[a-zA-Z0-9]{36}",          # GitHub OAuth
    r"AKIA[A-Z0-9]{16}",             # AWS keys
    r"xoxb-[a-zA-Z0-9-]+",           # Slack tokens
]

# Files to skip
SKIP_EXTENSIONS = {".gif", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".pyc", ".pyo"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv"}

# Known safe patterns (won't trigger on these)
SAFE_PATTERNS = [
    r"https?://github\.com/",         # GitHub URLs are fine
    r"https?://\w+\.shields\.io/",    # Badge URLs
    r"https?://api\.star-history\.com/", # Star history
    r"127\.0\.0\.1",                   # Localhost
    r"0\.0\.0\.0",                     # Bind all
    r"192\.168\.\d+\.\d+",            # Common private IPs in docs
]


def load_patterns() -> dict:
    """Load personal patterns from config file."""
    if PERSONAL_PATTERNS_FILE.exists():
        return json.loads(PERSONAL_PATTERNS_FILE.read_text())
    return DEFAULT_PATTERNS


def save_default_patterns():
    """Create the patterns file with defaults if it doesn't exist."""
    if not PERSONAL_PATTERNS_FILE.exists():
        PERSONAL_PATTERNS_FILE.write_text(json.dumps(DEFAULT_PATTERNS, indent=2))
        print(f"Created {PERSONAL_PATTERNS_FILE}")
        print("Edit this file to add your personal identifiers.")


def is_safe_match(line: str, match: str) -> bool:
    """Check if a match is a known safe pattern."""
    for safe in SAFE_PATTERNS:
        if re.search(safe, line):
            # Check if the match is INSIDE the safe pattern
            safe_match = re.search(safe, line)
            if safe_match and match in safe_match.group():
                return True
    return False


def scan_file(filepath: Path, patterns: dict) -> list:
    """Scan a single file for personal details. Returns list of findings."""
    findings = []

    if filepath.suffix.lower() in SKIP_EXTENSIONS:
        return findings

    try:
        content = filepath.read_text(errors="ignore")
    except (OSError, PermissionError):
        return findings

    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Check personal patterns
        for category, values in patterns.items():
            for value in values:
                if not value:
                    continue
                if re.search(re.escape(value), line, re.IGNORECASE):
                    if not is_safe_match(line, value):
                        findings.append({
                            "file": str(filepath),
                            "line": line_num,
                            "category": category,
                            "match": value,
                            "context": line.strip()[:120],
                        })

        # Check generic patterns
        for pattern in GENERIC_PATTERNS:
            match = re.search(pattern, line)
            if match:
                matched_text = match.group()
                if not is_safe_match(line, matched_text):
                    findings.append({
                        "file": str(filepath),
                        "line": line_num,
                        "category": "generic",
                        "match": matched_text,
                        "context": line.strip()[:120],
                    })

    return findings


def scan_directory(dirpath: Path, patterns: dict) -> list:
    """Scan all files in a directory."""
    all_findings = []

    for root, dirs, files in os.walk(dirpath):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            filepath = Path(root) / fname
            findings = scan_file(filepath, patterns)
            all_findings.extend(findings)

    return all_findings


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 privacy_guard.py /path/to/repo [--init]")
        print("       python3 privacy_guard.py --init  (create patterns file)")
        sys.exit(0)

    if sys.argv[1] == "--init":
        save_default_patterns()
        sys.exit(0)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Path not found: {target}")
        sys.exit(1)

    patterns = load_patterns()

    # Check if any personal patterns are configured
    has_patterns = any(bool(v) for v in patterns.values())
    if not has_patterns:
        print(f"⚠️  No personal patterns configured in {PERSONAL_PATTERNS_FILE}")
        print("Run: python3 privacy_guard.py --init")
        print("Then edit the file to add your identifiers.")
        # Still run generic patterns
        print("Running generic patterns only...\n")

    if target.is_file():
        findings = scan_file(target, patterns)
    else:
        findings = scan_directory(target, patterns)

    if not findings:
        print(f"✅ CLEAN — no personal details found in {target}")
        sys.exit(0)

    # Deduplicate
    seen = set()
    unique_findings = []
    for f in findings:
        key = (f["file"], f["line"], f["match"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    print(f"❌ BLOCKED — {len(unique_findings)} personal detail(s) found:\n")
    for f in unique_findings:
        rel_path = f["file"]
        if target.is_dir():
            try:
                rel_path = str(Path(f["file"]).relative_to(target))
            except ValueError:
                pass
        print(f"  {rel_path}:{f['line']} [{f['category']}]")
        print(f"    Match: {f['match']}")
        print(f"    Context: {f['context']}")
        print()

    sys.exit(1)


if __name__ == "__main__":
    main()
