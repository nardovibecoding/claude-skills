#!/usr/bin/env python3
# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
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


def scan_filename(filepath: Path, patterns: dict) -> list:
    """Scan file/directory NAMES for personal details."""
    findings = []
    name = filepath.name.lower()
    for category, values in patterns.items():
        for value in values:
            if not value:
                continue
            if value.lower() in name:
                findings.append({
                    "file": str(filepath),
                    "line": 0,
                    "category": f"filename:{category}",
                    "match": value,
                    "context": f"Filename contains '{value}'",
                })
    return findings


def scan_base64_strings(filepath: Path, patterns: dict) -> list:
    """Detect base64-encoded personal details in file content."""
    import base64
    findings = []
    if filepath.suffix.lower() in SKIP_EXTENSIONS:
        return findings
    try:
        content = filepath.read_text(errors="ignore")
    except (OSError, PermissionError):
        return findings

    b64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
    for line_num, line in enumerate(content.split("\n"), 1):
        for match in b64_pattern.finditer(line):
            try:
                decoded = base64.b64decode(match.group()).decode("utf-8", errors="ignore")
                for category, values in patterns.items():
                    for value in values:
                        if value and value.lower() in decoded.lower():
                            findings.append({
                                "file": str(filepath),
                                "line": line_num,
                                "category": f"base64:{category}",
                                "match": f"base64 contains '{value}'",
                                "context": f"Decoded: {decoded[:80]}",
                            })
            except Exception:
                continue
    return findings


def scan_git_history(dirpath: Path, patterns: dict) -> list:
    """Scan git commit messages and author info for personal details."""
    findings = []
    git_dir = dirpath / ".git"
    if not git_dir.exists():
        return findings

    try:
        result = subprocess.run(
            ["git", "-C", str(dirpath), "log", "--all", "--format=%H|%an|%ae|%s"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue
            commit_hash, author, email, subject = parts
            for category, values in patterns.items():
                for value in values:
                    if not value:
                        continue
                    for field, field_name in [(author, "author"), (email, "email"), (subject, "subject")]:
                        if re.search(re.escape(value), field, re.IGNORECASE):
                            findings.append({
                                "file": f"git:{commit_hash[:8]}",
                                "line": 0,
                                "category": f"git-history:{category}",
                                "match": value,
                                "context": f"Commit {field_name}: {field[:80]}",
                            })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return findings


def scan_exif(dirpath: Path) -> list:
    """Check for images with EXIF data that could leak location/device info."""
    findings = []
    image_exts = {".jpg", ".jpeg", ".png", ".tiff", ".heic"}
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            filepath = Path(root) / fname
            if filepath.suffix.lower() not in image_exts:
                continue
            # Check file size — EXIF-stripped images are usually smaller
            try:
                with open(filepath, "rb") as f:
                    header = f.read(12)
                # JPEG with EXIF: starts with FF D8 FF E1
                if header[:4] == b'\xff\xd8\xff\xe1':
                    findings.append({
                        "file": str(filepath),
                        "line": 0,
                        "category": "exif",
                        "match": "JPEG with EXIF metadata",
                        "context": "May contain GPS coordinates, device name, or username. Strip with: exiftool -all= file.jpg",
                    })
            except (OSError, PermissionError):
                continue
    return findings


def check_gitignore(dirpath: Path) -> list:
    """Warn if .env or credential files are not in .gitignore."""
    findings = []
    gitignore = dirpath / ".gitignore"
    gitignore_content = ""
    if gitignore.exists():
        gitignore_content = gitignore.read_text()

    dangerous_files = [".env", "credentials.json", "*.pem", "*.key", "id_rsa"]
    for danger in dangerous_files:
        # Check if file exists but isn't gitignored
        if danger.startswith("*"):
            continue  # skip glob patterns for existence check
        if (dirpath / danger).exists() and danger not in gitignore_content:
            findings.append({
                "file": str(dirpath / danger),
                "line": 0,
                "category": "gitignore-missing",
                "match": danger,
                "context": f"'{danger}' exists but is NOT in .gitignore — will be published!",
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
            all_findings.extend(scan_filename(filepath, patterns))
            all_findings.extend(scan_file(filepath, patterns))
            all_findings.extend(scan_base64_strings(filepath, patterns))

    # Repo-level scans
    all_findings.extend(scan_git_history(dirpath, patterns))
    all_findings.extend(scan_exif(dirpath))
    all_findings.extend(check_gitignore(dirpath))

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
