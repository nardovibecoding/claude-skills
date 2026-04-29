#!/usr/bin/env python3
"""extract.py — /upskill v2 Phase 7 extract/install subroutine (S5 slice).

7-step sub-pipeline: clone → SHA capture → idempotency → security audit →
EXTRACT-vs-INSTALL decision → place files → ledger write.

Spec: ~/.ship/upskill/goals/01-spec.md A10b-e + A12 + A13 (lines 224-236).

Security exit code mapping (non-obvious, MUST match skill_security_auditor.py):
  0 = PASS  (safe to install)
  1 = FAIL  (critical findings — block unconditionally, no override)
  2 = WARN  (review findings — prompt [Y/n] confirm before continuing)

CLI:
  python3 extract.py --decision <decision.json> --out <result.json>
                     [--dry-run] [--mock-fail-security] [--mock-warn-security]
                     [--standalone-url <url>]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HKT = ZoneInfo("Asia/Hong_Kong")

LEDGER = Path.home() / ".claude/scripts/state/upskill-installs.jsonl"
SKILLS_DIR = Path.home() / ".claude/skills"
ATOMS_DIR = Path.home() / "NardoWorld/atoms/extracted-patterns"
AUDITOR = Path.home() / ".claude/skills/skill-security-auditor/scripts/skill_security_auditor.py"


def _now_hkt() -> str:
    return datetime.now(tz=HKT).isoformat(timespec="seconds")


def _write_ledger(row: dict, dry_run: bool) -> None:
    """Append one JSONL row. Append is atomic for rows < PIPE_BUF on POSIX.
    Ledger writes always happen even in dry-run (for auditability); only
    fs installs (clone/copy) are skipped in dry-run mode.
    """
    line = json.dumps(row) + "\n"
    if dry_run:
        print(f"[dry-run] ledger row appending (always): {line.rstrip()}", file=sys.stderr)
    with open(LEDGER, "a") as fh:
        fh.write(line)


def _write_out(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, indent=2))


def _slug_from_url(url: str) -> str:
    """Extract repo name from GitHub URL as slug."""
    return url.rstrip("/").split("/")[-1]


def _prompt(message: str, valid: set[str]) -> str:
    """Read one line from stdin. Returns stripped input or empty string on EOF."""
    try:
        return input(message).strip()
    except EOFError:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="/upskill v2 extract subroutine (Phase 7)")
    ap.add_argument("--decision", help="Path to adopt_gate.py output JSON")
    ap.add_argument("--standalone-url", dest="standalone_url", help="Manual entry: bypass decision file, use this URL")
    ap.add_argument("--out", required=True, help="Path to write result JSON")
    ap.add_argument("--dry-run", action="store_true", help="Skip fs writes; log what would happen; write dry_run ledger row")
    ap.add_argument("--mock-fail-security", action="store_true", help="Force security verdict FAIL without invoking auditor (testing only)")
    ap.add_argument("--mock-warn-security", action="store_true", help="Force security verdict WARN without invoking auditor (testing only)")
    args = ap.parse_args()

    if not args.decision and not args.standalone_url:
        print("ERROR: must provide --decision or --standalone-url", file=sys.stderr)
        sys.exit(1)

    # Step 0 — TTY guard (only matters if we reach any interactive prompt)
    # We check this lazily at each prompt site below to keep the TTY check tight.
    # A pre-check here catches the most obvious headless case before any fs work.
    tty_ok = sys.stdin.isatty()

    staging_dir: str | None = None
    slug: str = "unknown"
    url: str = ""
    sha: str = ""
    security_verdict: str | None = None
    install_path: str | None = None
    install_status: str = "unknown"
    ledger_appended: bool = False
    staged_cleaned: bool = False

    try:
        # ---------------------------------------------------------------
        # Resolve top1 from decision file or standalone URL
        # ---------------------------------------------------------------
        if args.standalone_url:
            url = args.standalone_url
            slug = _slug_from_url(url)
        else:
            decision_data = json.loads(Path(args.decision).read_text())
            if decision_data.get("decision") != "adopt":
                # Non-adopt decision (abort_user, skip, n/a, aborted_no_tty, etc.)
                # Write a no-op ledger row documenting the non-install.
                ts = _now_hkt()
                row = {
                    "ts": ts,
                    "slug": "n/a",
                    "source_url": "",
                    "source_sha": "",
                    "installed_at": "",
                    "install_path": "",
                    "security_verdict": None,
                    "install_status": f"no_op_{decision_data.get('decision', 'unknown')}",
                }
                _write_ledger(row, dry_run=False)
                ledger_appended = True
                install_status = row["install_status"]
                _write_out(
                    args.out,
                    {
                        "slug": "n/a",
                        "source_url": "",
                        "source_sha": "",
                        "install_status": install_status,
                        "security_verdict": None,
                        "install_path": None,
                        "ledger_row_appended": True,
                        "staging_cleaned": True,
                    },
                )
                return 0

            top1 = decision_data.get("top1") or {}
            url = top1.get("url") or ""
            slug = _slug_from_url(url) if url else top1.get("name") or top1.get("id") or "unknown"

        # ---------------------------------------------------------------
        # Step 1 — Clone
        # ---------------------------------------------------------------
        pid = os.getpid()
        staging_dir = f"/tmp/upskill_extract_{slug}_{pid}"

        if not args.dry_run:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, staging_dir],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                install_status = "aborted_clone_fail"
                ts = _now_hkt()
                row = {
                    "ts": ts, "slug": slug, "source_url": url, "source_sha": "",
                    "installed_at": "", "install_path": "", "security_verdict": None,
                    "install_status": install_status,
                }
                _write_ledger(row, dry_run=False)
                ledger_appended = True
                staging_dir = None  # already failed, no cleanup needed
                _write_out(args.out, {
                    "slug": slug, "source_url": url, "source_sha": "",
                    "install_status": install_status, "security_verdict": None,
                    "install_path": None, "ledger_row_appended": True, "staging_cleaned": True,
                })
                return 0
        else:
            print(f"[dry-run] would clone {url} → {staging_dir}", file=sys.stderr)

        # ---------------------------------------------------------------
        # Step 2 — SHA capture
        # ---------------------------------------------------------------
        if not args.dry_run:
            sha_result = subprocess.run(
                ["git", "-C", staging_dir, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            )
            sha = sha_result.stdout.strip() if sha_result.returncode == 0 else "unknown-sha"
        else:
            sha = "dryrun-sha"
            print(f"[dry-run] SHA placeholder: {sha}", file=sys.stderr)

        # ---------------------------------------------------------------
        # Step 3 — Idempotency
        # ---------------------------------------------------------------
        target_dir = SKILLS_DIR / slug
        manifest_path = target_dir / ".upskill-manifest.json"

        if manifest_path.exists():
            existing_manifest = json.loads(manifest_path.read_text())
            existing_sha = existing_manifest.get("source_sha", "")
            if existing_sha == sha:
                install_status = "already_installed"
                ts = _now_hkt()
                row = {
                    "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                    "installed_at": ts, "install_path": str(target_dir),
                    "security_verdict": None, "install_status": install_status,
                }
                _write_ledger(row, dry_run=args.dry_run)
                ledger_appended = True
                _write_out(args.out, {
                    "slug": slug, "source_url": url, "source_sha": sha,
                    "install_status": install_status, "security_verdict": None,
                    "install_path": str(target_dir), "ledger_row_appended": True,
                    "staging_cleaned": False,
                })
                return 0
            else:
                # Different SHA — need user choice
                if not tty_ok:
                    install_status = "aborted_no_tty"
                    ts = _now_hkt()
                    row = {
                        "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                        "installed_at": "", "install_path": "",
                        "security_verdict": None, "install_status": install_status,
                    }
                    _write_ledger(row, dry_run=args.dry_run)
                    ledger_appended = True
                    _write_out(args.out, {
                        "slug": slug, "source_url": url, "source_sha": sha,
                        "install_status": install_status, "security_verdict": None,
                        "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
                    })
                    return 0
                answer = _prompt(
                    f"Skill '{slug}' already installed (different SHA). "
                    f"[O]verwrite | install-as-{slug}-v2 | [a]bort: ",
                    {"O", f"install-as-{slug}-v2", "a"},
                )
                if answer == "O":
                    pass  # proceed; will overwrite at Step 6
                elif answer == f"install-as-{slug}-v2":
                    slug = f"{slug}-v2"
                    target_dir = SKILLS_DIR / slug
                    manifest_path = target_dir / ".upskill-manifest.json"
                else:
                    install_status = "aborted_user_idempotency"
                    ts = _now_hkt()
                    row = {
                        "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                        "installed_at": "", "install_path": "",
                        "security_verdict": None, "install_status": install_status,
                    }
                    _write_ledger(row, dry_run=args.dry_run)
                    ledger_appended = True
                    _write_out(args.out, {
                        "slug": slug, "source_url": url, "source_sha": sha,
                        "install_status": install_status, "security_verdict": None,
                        "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
                    })
                    return 0
        elif target_dir.exists():
            # Dir exists but no manifest — prompt overwrite or abort
            if not tty_ok:
                install_status = "aborted_no_tty"
                ts = _now_hkt()
                row = {
                    "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                    "installed_at": "", "install_path": "",
                    "security_verdict": None, "install_status": install_status,
                }
                _write_ledger(row, dry_run=args.dry_run)
                ledger_appended = True
                _write_out(args.out, {
                    "slug": slug, "source_url": url, "source_sha": sha,
                    "install_status": install_status, "security_verdict": None,
                    "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
                })
                return 0
            answer = _prompt(
                f"Directory '{target_dir}' exists but has no manifest. [O]verwrite | [a]bort: ",
                {"O", "a"},
            )
            if answer != "O":
                install_status = "aborted_user_idempotency"
                ts = _now_hkt()
                row = {
                    "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                    "installed_at": "", "install_path": "",
                    "security_verdict": None, "install_status": install_status,
                }
                _write_ledger(row, dry_run=args.dry_run)
                ledger_appended = True
                _write_out(args.out, {
                    "slug": slug, "source_url": url, "source_sha": sha,
                    "install_status": install_status, "security_verdict": None,
                    "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
                })
                return 0

        # ---------------------------------------------------------------
        # Step 4 — Security audit
        # ---------------------------------------------------------------
        if args.mock_fail_security:
            # Force FAIL path without calling auditor (testing only)
            audit_rc = 1
            audit_findings = [{"severity": "CRITICAL", "detail": "mock-fail-security flag set"}]
        elif args.mock_warn_security:
            # Force WARN path without calling auditor (testing only)
            audit_rc = 2
            audit_findings = [{"severity": "WARN", "detail": "mock-warn-security flag set"}]
        elif args.dry_run:
            # In dry-run without mock flags, skip auditor and assume PASS
            audit_rc = 0
            audit_findings = []
        else:
            audit_result = subprocess.run(
                ["python3", str(AUDITOR), "--json", staging_dir],
                capture_output=True,
                text=True,
            )
            audit_rc = audit_result.returncode
            try:
                audit_out = json.loads(audit_result.stdout)
                audit_findings = audit_out.get("findings") or []
            except Exception:
                audit_findings = []

        # Map exit codes: 0=PASS, 1=FAIL, 2=WARN
        if audit_rc == 0:
            security_verdict = "PASS"
        elif audit_rc == 1:
            security_verdict = "FAIL"
            print("SECURITY AUDIT: FAIL — critical findings, install blocked unconditionally:", file=sys.stderr)
            for f in audit_findings:
                print(f"  - {f}", file=sys.stderr)
            install_status = "aborted_security_fail"
            ts = _now_hkt()
            row = {
                "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                "installed_at": "", "install_path": "",
                "security_verdict": security_verdict, "install_status": install_status,
            }
            _write_ledger(row, dry_run=args.dry_run)
            ledger_appended = True
            _write_out(args.out, {
                "slug": slug, "source_url": url, "source_sha": sha,
                "install_status": install_status, "security_verdict": security_verdict,
                "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
            })
            return 0
        elif audit_rc == 2:
            security_verdict = "WARN"
            print("SECURITY AUDIT: WARN — review findings before installing:", file=sys.stderr)
            for f in audit_findings:
                print(f"  - {f}", file=sys.stderr)
            if not tty_ok:
                install_status = "aborted_no_tty"
                ts = _now_hkt()
                row = {
                    "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                    "installed_at": "", "install_path": "",
                    "security_verdict": security_verdict, "install_status": install_status,
                }
                _write_ledger(row, dry_run=args.dry_run)
                ledger_appended = True
                _write_out(args.out, {
                    "slug": slug, "source_url": url, "source_sha": sha,
                    "install_status": install_status, "security_verdict": security_verdict,
                    "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
                })
                return 0
            answer = _prompt("Install despite warnings? [Y/n]: ", {"Y", "y", "n"})
            if answer not in ("Y", "y"):
                install_status = "aborted_security_warn"
                ts = _now_hkt()
                row = {
                    "ts": ts, "slug": slug, "source_url": url, "source_sha": sha,
                    "installed_at": "", "install_path": "",
                    "security_verdict": security_verdict, "install_status": install_status,
                }
                _write_ledger(row, dry_run=args.dry_run)
                ledger_appended = True
                _write_out(args.out, {
                    "slug": slug, "source_url": url, "source_sha": sha,
                    "install_status": install_status, "security_verdict": security_verdict,
                    "install_path": None, "ledger_row_appended": True, "staging_cleaned": False,
                })
                return 0
            # Proceeded past WARN — continue with security_verdict = WARN

        # ---------------------------------------------------------------
        # Step 5 — EXTRACT-vs-INSTALL decision
        # ---------------------------------------------------------------
        # INSTALL if staging dir has scripts/ OR hooks/ OR lib/ subdir
        # EXTRACT if only SKILL.md + references/ + templates/ (pure playbook)
        staging_path = Path(staging_dir) if staging_dir else Path("/tmp/dryrun-staging")
        is_install = (
            (staging_path / "scripts").exists()
            or (staging_path / "hooks").exists()
            or (staging_path / "lib").exists()
        )

        if args.dry_run:
            # In dry-run: default to INSTALL path (more representative test)
            is_install = True
            print("[dry-run] assuming INSTALL path (scripts/ present)", file=sys.stderr)

        # ---------------------------------------------------------------
        # Step 6 — Place files
        # ---------------------------------------------------------------
        ts = _now_hkt()
        if is_install:
            install_path = str(target_dir)
            if not args.dry_run:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(staging_dir, target_dir)
                # Write manifest
                manifest_data = {
                    "source_url": url,
                    "source_sha": sha,
                    "installed_at": ts,
                }
                (target_dir / ".upskill-manifest.json").write_text(json.dumps(manifest_data, indent=2))
            else:
                print(f"[dry-run] would copytree {staging_dir} → {target_dir}", file=sys.stderr)
                print(f"[dry-run] would write manifest to {target_dir}/.upskill-manifest.json", file=sys.stderr)
            install_status = "dry_run" if args.dry_run else "installed"
        else:
            # EXTRACT — copy SKILL.md to atoms dir
            ATOMS_DIR.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now(tz=HKT).strftime("%Y-%m-%d")
            dest_file = ATOMS_DIR / f"{slug}-{date_str}.md"
            skill_md = staging_path / "SKILL.md"
            install_path = str(dest_file)
            if not args.dry_run:
                if skill_md.exists():
                    shutil.copy(skill_md, dest_file)
                else:
                    # No SKILL.md found — still record as extracted with note
                    dest_file.write_text(f"# {slug}\n\n(No SKILL.md found in source repo)\n")
            else:
                print(f"[dry-run] would copy SKILL.md → {dest_file}", file=sys.stderr)
            install_status = "dry_run" if args.dry_run else "extracted"

        # ---------------------------------------------------------------
        # Step 7 — Ledger write
        # ---------------------------------------------------------------
        row = {
            "ts": ts,
            "slug": slug,
            "source_url": url,
            "source_sha": sha,
            "installed_at": ts,
            "install_path": install_path or "",
            "security_verdict": security_verdict or "PASS",
            "install_status": install_status,
        }
        _write_ledger(row, dry_run=False)  # always write ledger, even for dry_run (with dry_run status)
        ledger_appended = True

        _write_out(args.out, {
            "slug": slug,
            "source_url": url,
            "source_sha": sha,
            "install_status": install_status,
            "security_verdict": security_verdict or "PASS",
            "install_path": install_path,
            "ledger_row_appended": True,
            "staging_cleaned": False,  # updated in finally block
        })

    finally:
        # Step 8 — Cleanup staging dir regardless of outcome
        if staging_dir and Path(staging_dir).exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
            staged_cleaned = True
        else:
            staged_cleaned = True

        # Patch staging_cleaned in output file if it exists
        out_path = Path(args.out)
        if out_path.exists():
            try:
                out_data = json.loads(out_path.read_text())
                out_data["staging_cleaned"] = staged_cleaned
                out_path.write_text(json.dumps(out_data, indent=2))
            except Exception:
                pass  # Don't crash cleanup on output patch failure

    return 0


if __name__ == "__main__":
    sys.exit(main())
