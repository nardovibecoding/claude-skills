#!/usr/bin/env python3
"""Phase 10: System-drift scanner.

Detects accumulation across four surfaces — hooks, agents, LaunchAgents, scripts.
Same drift pattern across all: .bak cruft, zombie .disabled, orphans, rescinded-but-wired,
stanza-merge candidates, dot-vs-dash collisions.

Rule-based per CLAUDE.md HARD RULE (no LLM). Reports findings; does not auto-fix.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
HOOKS_DIR = HOME / ".claude/hooks"
AGENTS_DIR = HOME / ".claude/agents"
SCRIPTS_DIR = HOME / ".claude/scripts"
LAUNCHAGENTS_DIR = HOME / "Library/LaunchAgents"
SETTINGS = HOME / ".claude/settings.json"
SETTINGS_LOCAL = HOME / ".claude/settings.local.json"

SEVERITIES = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


@dataclass
class Finding:
    surface: str
    severity: str
    code: str  # D1..D8
    path: str
    detail: str

    def line(self) -> str:
        return f"[{self.severity:6s}] {self.code} {self.surface:14s} {self.path}  — {self.detail}"


# ───────────────────────── helpers ─────────────────────────

def load_settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text())
    except Exception:
        return {}


def all_wired_hook_paths(settings: dict) -> set[str]:
    """Extract every hook command path referenced in settings.json."""
    out: set[str] = set()
    for stanzas in settings.get("hooks", {}).values():
        for s in stanzas:
            for h in s.get("hooks", []):
                cmd = h.get("command", "")
                # naive path extraction — first token that looks like a path
                for tok in cmd.split():
                    if "/.claude/hooks/" in tok or tok.endswith(".py") or tok.endswith(".sh") or tok.endswith(".js"):
                        out.add(tok.replace("~", str(HOME)))
                        break
    return out


def dispatcher_routed_files() -> set[str]:
    """Greps dispatcher_pre.py and dispatcher_post.py for filenames they
    importlib-load at runtime. Catches the B4-orphan-sweep gotcha."""
    out: set[str] = set()
    pat = re.compile(r"['\"]([a-zA-Z0-9_\-]+\.py)['\"]")
    for name in ("dispatcher_pre.py", "dispatcher_post.py"):
        p = HOOKS_DIR / name
        if not p.exists():
            continue
        try:
            text = p.read_text()
        except Exception:
            continue
        for m in pat.finditer(text):
            out.add(m.group(1))
    return out


def imports_inside_hooks() -> set[str]:
    """Files that other hooks import — these are libs, never delete."""
    out: set[str] = set()
    if not HOOKS_DIR.exists():
        return out
    pat_imp = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_]+)", re.M)
    for p in HOOKS_DIR.glob("*.py"):
        try:
            text = p.read_text()
        except Exception:
            continue
        for m in pat_imp.finditer(text):
            mod = m.group(1)
            cand = HOOKS_DIR / f"{mod}.py"
            if cand.exists() and cand.name != p.name:
                out.add(cand.name)
    return out


def launchctl_loaded() -> set[str]:
    """Labels currently registered with launchd for this user."""
    try:
        r = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, timeout=10,
        )
        return {ln.split()[-1] for ln in r.stdout.splitlines()[1:] if ln.strip()}
    except Exception:
        return set()


# ───────────────────────── per-surface scanners ─────────────────────────

def scan_dir_generic(
    surface: str,
    root: Path,
    extensions: tuple[str, ...],
    wired_set: set[str],
    routed_set: set[str] | None = None,
    imports_set: set[str] | None = None,
) -> list[Finding]:
    """D1 .bak; D2 zombie .disabled; D3 .disabled+live conflict; D4 orphan."""
    out: list[Finding] = []
    if not root.exists():
        return out
    files = [p for p in root.iterdir() if p.is_file()]

    # D1: .bak* files
    for p in files:
        if ".bak" in p.name:
            out.append(Finding(surface, "MEDIUM", "D1", str(p),
                               f".bak cruft ({p.stat().st_size}B); replaced=deleted rule"))

    # D2/D3: .disabled
    live_names = {p.name for p in files if not (".bak" in p.name or p.name.endswith(".disabled"))}
    for p in files:
        if not p.name.endswith(".disabled"):
            continue
        live_name = p.name[: -len(".disabled")]
        if live_name in live_names:
            out.append(Finding(surface, "HIGH", "D3", str(p),
                               f"both .disabled and live counterpart present — conflict"))

    # D4: orphans (per-extension)
    routed_set = routed_set or set()
    imports_set = imports_set or set()
    for p in files:
        if not any(p.name.endswith(e) for e in extensions):
            continue
        if p.name.startswith("_") or p.name in {"hook_base.py", "test_helpers.py", "telemetry.py", "hook_client.sh"}:
            continue
        if ".bak" in p.name or p.name.endswith(".disabled"):
            continue
        wired = any(p.name in w or str(p) in w for w in wired_set)
        if wired:
            continue
        if p.name in routed_set or p.name in imports_set:
            continue
        out.append(Finding(surface, "MEDIUM", "D4", str(p),
                           "orphan: not wired, not dispatcher-routed, not imported"))
    return out


def scan_hooks() -> list[Finding]:
    settings = load_settings()
    wired = all_wired_hook_paths(settings)
    routed = dispatcher_routed_files()
    imports = imports_inside_hooks()
    out = scan_dir_generic("hooks", HOOKS_DIR, (".py", ".js", ".sh"), wired, routed, imports)

    # D6: rescinded-but-still-wired — file body has empty rescinded marker but is wired
    rescind_pat = re.compile(r"FORBIDDEN_\w*\s*=\s*\[\s*\]|#\s*RESCINDED|rescinded\s+\d{4}-\d{2}-\d{2}", re.I)
    for hook_path in wired:
        p = Path(hook_path)
        if not p.exists() or p.suffix != ".py":
            continue
        try:
            text = p.read_text()
        except Exception:
            continue
        if rescind_pat.search(text):
            out.append(Finding("hooks", "HIGH", "D6", str(p),
                               "wired but body marks itself rescinded"))

    # D7: stanza-merge candidates in settings.json
    for evt, stanzas in settings.get("hooks", {}).items():
        bucket = defaultdict(int)
        for s in stanzas:
            bucket[s.get("matcher", "")] += 1
        dups = {m: c for m, c in bucket.items() if c > 1}
        if dups:
            detail = ", ".join(f"matcher='{m}' x{c}" for m, c in dups.items())
            out.append(Finding("hooks", "MEDIUM", "D7", str(SETTINGS),
                               f"{evt}: mergeable stanzas — {detail}"))
    return out


def grep_refs(needle: str, roots: list[Path]) -> int:
    """Count references to `needle` across roots. Returns 0 fast on no-match."""
    args = ["grep", "-rl", "--binary-files=without-match", needle]
    for r in roots:
        if r.exists():
            args.append(str(r))
    if len(args) <= 4:
        return 0
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return len([ln for ln in r.stdout.splitlines() if ln.strip()])
    except Exception:
        return 0


def scan_agents() -> list[Finding]:
    """Agents are wired by name when subagent_type references them across
    skills, rules, CLAUDE.md, hooks. Grep filename stem across those trees."""
    out: list[Finding] = []
    if not AGENTS_DIR.exists():
        return out
    files = [p for p in AGENTS_DIR.iterdir() if p.is_file()]
    roots = [HOME / ".claude/skills", HOME / ".claude/rules",
             HOME / ".claude/CLAUDE.md", HOOKS_DIR]
    # D1/D2/D3 reusable from generic
    out.extend(scan_dir_generic("agents", AGENTS_DIR, ("__noop__",), set(), set(), set()))
    # D4 with proper wired detection
    for p in files:
        if not p.name.endswith(".md"):
            continue
        if p.name.startswith("_"):
            continue
        stem = p.name[:-3]
        # Exclude self-reference: subtract 1 if stem appears in own file (always)
        refs = grep_refs(stem, roots)
        if refs == 0:
            out.append(Finding("agents", "MEDIUM", "D4", str(p),
                               f"orphan: '{stem}' not referenced in skills/rules/CLAUDE.md/hooks"))
    return out


def scan_scripts() -> list[Finding]:
    """Scripts are wired when referenced from LaunchAgents plists, hooks,
    skills, or this skill's own dispatcher."""
    out: list[Finding] = []
    if not SCRIPTS_DIR.exists():
        return out
    files = [p for p in SCRIPTS_DIR.iterdir() if p.is_file()]
    roots = [LAUNCHAGENTS_DIR, HOOKS_DIR, HOME / ".claude/skills",
             HOME / ".claude/CLAUDE.md", HOME / ".claude/rules"]
    out.extend(scan_dir_generic("scripts", SCRIPTS_DIR, ("__noop__",), set(), set(), set()))
    for p in files:
        if not (p.name.endswith(".py") or p.name.endswith(".sh")):
            continue
        if p.name.startswith("_"):
            continue
        refs = grep_refs(p.name, roots)
        if refs == 0:
            out.append(Finding("scripts", "MEDIUM", "D4", str(p),
                               f"orphan: '{p.name}' not referenced in LaunchAgents/hooks/skills"))
    return out


def scan_launchagents() -> list[Finding]:
    """LaunchAgents — same patterns plus D5 dot-vs-dash collision."""
    out: list[Finding] = []
    if not LAUNCHAGENTS_DIR.exists():
        return out
    bernard = list(LAUNCHAGENTS_DIR.glob("com.bernard.*.plist*"))

    # D1: .bak / .disabled.<phase> cruft
    for p in bernard:
        if re.search(r"\.disabled\.[a-z0-9\-]+$", p.name) or ".bak" in p.name:
            out.append(Finding("launchagents", "MEDIUM", "D1", str(p),
                               "phase-suffix cruft; replaced=deleted rule"))

    # D2: .disabled (zombie or live)
    live = {p.name[: -len(".plist")] for p in bernard if p.name.endswith(".plist")}
    for p in bernard:
        if p.name.endswith(".plist.disabled"):
            stem = p.name[: -len(".plist.disabled")]
            if stem in live:
                out.append(Finding("launchagents", "HIGH", "D3", str(p),
                                   f"both .disabled and active .plist present — conflict"))

    # D5: dot-vs-dash collision (CLAUDE.md infra rule)
    stems = [p.name[: -len(".plist")] for p in bernard if p.name.endswith(".plist")]
    norm = defaultdict(list)
    for stem in stems:
        norm[stem.replace("-", ".").replace(".", "_")].append(stem)
    for group in norm.values():
        if len({s for s in group}) > 1 and any("." in s for s in group) and any("-" in s for s in group):
            out.append(Finding("launchagents", "HIGH", "D5", "+".join(group),
                               "dot-vs-dash naming collision — duplicate scheduling risk"))

    # D8: loaded-but-file-missing / file-but-not-loaded
    loaded = launchctl_loaded()
    if loaded:
        on_disk = {p.name[: -len(".plist")] for p in bernard if p.name.endswith(".plist")}
        bernard_loaded = {x for x in loaded if x.startswith("com.bernard.")}
        zombie = bernard_loaded - on_disk
        for z in zombie:
            out.append(Finding("launchagents", "HIGH", "D8", z,
                               "loaded in launchctl but plist file missing"))
    return out


# ───────────────────────── main ─────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 10 system-drift scanner")
    ap.add_argument("--surface", choices=["hooks", "agents", "scripts", "launchagents", "all"], default="all")
    ap.add_argument("--severity", choices=list(SEVERITIES), default="LOW")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    findings: list[Finding] = []
    if args.surface in ("hooks", "all"):
        findings.extend(scan_hooks())
    if args.surface in ("agents", "all"):
        findings.extend(scan_agents())
    if args.surface in ("scripts", "all"):
        findings.extend(scan_scripts())
    if args.surface in ("launchagents", "all"):
        findings.extend(scan_launchagents())

    minsev = SEVERITIES[args.severity]
    findings = [f for f in findings if SEVERITIES[f.severity] >= minsev]

    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        if not findings:
            print(f"phase-10: no drift at severity ≥ {args.severity}")
            return 0
        by_surface: dict[str, list[Finding]] = defaultdict(list)
        for f in findings:
            by_surface[f.surface].append(f)
        for surface, group in sorted(by_surface.items()):
            print(f"\n## {surface} ({len(group)})")
            for f in sorted(group, key=lambda x: (-SEVERITIES[x.severity], x.code)):
                print(f"  {f.line()}")
        print(f"\ntotal: {len(findings)} findings")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
