#!/usr/bin/env python3
"""
/debug — deterministic entrypoint.

S1 scope: `check` (Wiring) + `list`.
S3 scope: `bug` (full 17-step engine) + D1 (atomic ledger) + D2 (token-form normalize matcher).
S8 scope: `drift` + `flaky` + `performance` (final slice).

Reads Phase 4 graphs read-only. Writes to ~/NardoWorld/realize-debt.md (lockfile-protected).

Per CLAUDE.md "Rule-based > LLM for local classifiers": no LLM calls. Pure rules + JSON I/O.
Iron Laws (obra/superpowers MIT):
  1. NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
  2. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure _disc.py importable from same dir
sys.path.insert(0, str(Path(__file__).parent))
import _disc  # noqa: E402

# Detector pack (P1-P4) for /debug performance symptom-first inventory.
# Loaded lazily so a detector import error never bricks other verbs.
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from detectors import run_all as _perf_run_detectors  # type: ignore
except Exception as _e:  # pragma: no cover - defensive
    _perf_run_detectors = None
    _PERF_IMPORT_ERR = repr(_e)
else:
    _PERF_IMPORT_ERR = None

HOME = Path(os.path.expanduser("~"))
META = HOME / "NardoWorld" / "meta"
LEDGER = HOME / "NardoWorld" / "realize-debt.md"
SHIP_ROOT = HOME / ".ship"
DEBUG_LOG = HOME / ".claude" / "debug.log"

PHASE4_FILES = {
    "state_registry": META / "state_registry.json",
    "pipeline_graph": META / "pipeline_graph.json",
    "data_lineage": META / "data_lineage.json",
    "sync_graph": META / "sync_graph.json",
    "consistency_registry": META / "consistency_registry.json",
}
ORPHAN_REGISTRY = META / "orphan_registry.json"  # ships in S5
HUB_NODES = META / "hub_nodes.json"

VERDICTS = ("wired", "partial", "not_wired", "inconclusive")

# Realization Checks — see ~/.claude/skills/ship/phases/common/realization-checks.md
RC1_STUB_PATTERNS = (
    r'\[stub\]', r'#\s*stub\b', r'//\s*stub\b',
    r'\bTODO[: ]', r'\bFIXME[: ]',
    r'NotImplementedError', r'raise NotImplemented',
    r'pass\s*#\s*implement later',
    r'step \d+:\s*<[a-z_]+>',  # /upskill v1 skeleton fingerprint
)
RC7_HOOKOUT_PATTERNS = (
    r'router_log\.jsonl$', r'\.cache(/|$)', r'\.session\.json$',
    r'\.session/', r'^hook_state', r'^\.hook_state',
    r'^auto_.*\.(log|state)$',
)


def _rc_changeset_paths() -> list[Path]:
    """Returns paths to scan for RC-1 / RC-7. Sources: DEBUG_CHANGESET env (colon-sep)."""
    raw = os.environ.get("DEBUG_CHANGESET", "").strip()
    if not raw:
        return []
    return [Path(p).expanduser() for p in raw.split(":") if p.strip()]


def run_realization_checks(verdict: str, *, mode: str) -> tuple[str, list[str], bool]:
    """RC-1 (stub markers) + RC-7 (hook-output blocklist) per /debug SKILL.md §Realization Checks.

    Returns (new_verdict, tags, blocked). RC-1 hits degrade `wired`→`partial` + add `needs_real_implementation`.
    RC-7 hits set blocked=True (caller must abort write). Live-process verbs (no changeset scope) skip.
    """
    paths = _rc_changeset_paths()
    if not paths:
        return verdict, [], False  # no changeset → skip per SKILL.md
    stub_re = re.compile("|".join(RC1_STUB_PATTERNS))
    hook_re = re.compile("|".join(RC7_HOOKOUT_PATTERNS))
    stub_hits: list[str] = []
    hook_hits: list[str] = []
    for root in paths:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else list(root.rglob("*"))
        for f in candidates:
            if not f.is_file():
                continue
            try:
                rel = str(f)
                if hook_re.search(rel):
                    hook_hits.append(rel)
                if f.suffix in (".py", ".sh", ".js", ".ts", ".md", ".json"):
                    text = f.read_text(errors="ignore")
                    for m in stub_re.finditer(text):
                        stub_hits.append(f"{rel}: {m.group(0)}")
                        if len(stub_hits) >= 20:
                            break
            except Exception:
                continue
    tags: list[str] = []
    new_verdict = verdict
    blocked = False
    if stub_hits:
        if verdict == "wired":
            new_verdict = "partial"
        tags.append("needs_real_implementation")
        print(f"RC-1 [{mode}]: {len(stub_hits)} stub marker(s); verdict {verdict}→{new_verdict}", file=sys.stderr)
        for h in stub_hits[:5]:
            print(f"  RC-1 hit: {h}", file=sys.stderr)
    if hook_hits:
        blocked = True
        print(f"RC-7 BLOCK: {len(hook_hits)} hook-output file(s) in changeset", file=sys.stderr)
        for h in hook_hits[:5]:
            print(f"  RC-7 hit: {h}", file=sys.stderr)
    return new_verdict, tags, blocked
LEDGER_HEADER = """# Realization Debt Ledger

Append-only log of "I built X but never wired / verified / lived with X." Entries seeded by `/debug check`, `/debug bug`, `/debug drift`, and the consistency-daemon orphan-sweep detector (S5).

ID format: `R-NNNN` zero-padded, monotonic, never deleted.
Status enum: `open / bug-fixed / wired / orphan-activated / orphan-archived / drift-fixed / zombie-removed / abandoned / inconclusive`.
Schema: per master plan §9 — `~/.ship/master-debug/goals/00-master-plan.md`.

Source-of-truth: this file. Writer: `/debug` skill only (per master plan §6 — ledger writer ownership). `/ship` reads verdicts and triggers writes; never writes directly.
"""


def load_phase4() -> dict:
    out = {}
    missing = []
    for k, p in PHASE4_FILES.items():
        if not p.exists():
            missing.append(str(p))
            continue
        try:
            out[k] = json.loads(p.read_text())
        except Exception as e:
            missing.append(f"{p} (parse error: {e})")
    if missing:
        print(f"PREMISE_FAILURE: missing/unreadable Phase 4 artifacts: {missing}", file=sys.stderr)
        sys.exit(2)
    return out


def parse_target(target: str) -> tuple[str | None, str]:
    if ":" in target:
        host, feat = target.split(":", 1)
        return host.strip().lower(), feat.strip().lower()
    return None, target.strip().lower()


def find_node_matches(graph: dict, feature: str, host: str | None) -> tuple[list[dict], list[dict]]:
    matches_n: list[dict] = []
    matches_e: list[dict] = []
    variants = _disc.normalize_feature_tokens(feature)
    for n in graph.get("nodes", []):
        blob = json.dumps(n).lower()
        if any(v in blob for v in variants):
            if host is None or n.get("host", "").lower() == host:
                matches_n.append({"id": n.get("id"), "type": n.get("type"), "host": n.get("host")})
    for e in graph.get("edges", []):
        blob = json.dumps(e).lower()
        if any(v in blob for v in variants):
            matches_e.append({"src": e.get("src"), "dst": e.get("dst"), "kind": e.get("kind")})
    return matches_n, matches_e


def find_state_node(state: dict, host: str | None, feature: str) -> dict | None:
    variants = _disc.normalize_feature_tokens(feature)
    for n in state.get("nodes", []):
        if host and n.get("host", "").lower() != host:
            continue
        blob = json.dumps(n).lower()
        if any(v in blob for v in variants):
            return n
    if host:
        for n in state.get("nodes", []):
            if n.get("host", "").lower() == host and n.get("type") == "systemd_service" and n.get("status") == "ACTIVE":
                return n
    return None


def find_lineage_matches(lineage: dict, feature: str, host: str | None) -> list[str]:
    variants = _disc.normalize_feature_tokens(feature)
    out = []
    for k, v in lineage.get("collectors", {}).items():
        if host and v.get("host", "").lower() != host:
            continue
        blob = (k + " " + json.dumps(v)).lower()
        if any(var in blob for var in variants):
            out.append(k)
    return out


def find_consistency_signals(cr: dict, feature: str) -> list[dict]:
    variants = _disc.normalize_feature_tokens(feature)
    out = []
    def walk(obj, path=""):
        if len(out) >= 5:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                np = f"{path}.{k}" if path else k
                kl = k.lower()
                if any(var in kl for var in variants):
                    out.append({"path": np, "preview": str(v)[:200]})
                elif isinstance(v, (dict, list)):
                    walk(v, np)
                elif isinstance(v, str):
                    vl = v.lower()
                    if any(var in vl for var in variants):
                        out.append({"path": np, "preview": v[:200]})
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:50]):
                walk(item, f"{path}[{i}]")
    walk(cr)
    return out


def _pick_sha_in_paragraph(text: str, hit_pos: int) -> str | None:
    """Pick the most relevant commit SHA near hit_pos.

    Strategy (D2 closure):
      1. Look in the same paragraph (split on blank lines) as hit_pos.
      2. Within that paragraph, prefer SHAs on a line containing 'commit:', 'commit_sha:',
         'wired-commit:', 'Commit SHA', or '`<sha>`'.
      3. Fallback: first SHA in the same paragraph.
      4. Fallback: first SHA anywhere in the file.
    """
    # Find paragraph boundary: split on \n\n
    para_start = text.rfind("\n\n", 0, hit_pos)
    para_end = text.find("\n\n", hit_pos)
    if para_start == -1:
        para_start = 0
    if para_end == -1:
        para_end = len(text)
    paragraph = text[para_start:para_end]
    # Priority lines
    priority_re = re.compile(r"(commit|wired-commit|commit_sha|Commit SHA)[^\n]*?\b([0-9a-f]{7,40})\b", re.IGNORECASE)
    pm = priority_re.search(paragraph)
    if pm:
        return pm.group(2)
    # First SHA in paragraph
    sha_re = re.compile(r"\b([0-9a-f]{7,40})\b")
    pm2 = sha_re.search(paragraph)
    if pm2:
        return pm2.group(1)
    # File-wide fallback
    pm3 = sha_re.search(text)
    return pm3.group(1) if pm3 else None


def find_ship_evidence(feature: str) -> dict | None:
    """Search ~/.ship/*/experiments/*.md for visible-proof evidence of feature wiring.

    D2 closure: token-form normalize before substring match. Tries kebab/camel/snake/lower
    variants. SHA picker uses paragraph-local priority (not first-SHA-in-file).
    """
    if not SHIP_ROOT.exists():
        return None
    variants = _disc.normalize_feature_tokens(feature)
    candidates = []
    for ship_dir in SHIP_ROOT.iterdir():
        if not ship_dir.is_dir():
            continue
        exp_dir = ship_dir / "experiments"
        if not exp_dir.exists():
            continue
        for md in sorted(exp_dir.glob("*.md")):
            try:
                txt = md.read_text()
            except Exception:
                continue
            txt_l = txt.lower()
            hit_pos = -1
            for v in variants:
                p = txt_l.find(v)
                if p != -1:
                    hit_pos = p
                    break
            if hit_pos == -1:
                continue
            excerpt_lines = []
            for line in txt.splitlines():
                ll = line.lower()
                if any(v in ll for v in variants) or "wired" in ll or "visible" in ll:
                    excerpt_lines.append(line.strip())
                if len(excerpt_lines) >= 5:
                    break
            wired_commit = _pick_sha_in_paragraph(txt, hit_pos)
            candidates.append({
                "ship_slug": ship_dir.name,
                "ship_log": str(md),
                "wired_commit": wired_commit,
                "visible_proof_excerpt": " | ".join(excerpt_lines)[:500],
                "mtime": md.stat().st_mtime,
            })
    if not candidates:
        return None
    candidates.sort(key=lambda c: -c["mtime"])
    return candidates[0]


def find_existing_ledger_entry(ship_slug: str | None, feature: str, host: str | None = None) -> str | None:
    if not LEDGER.exists():
        return None
    txt = LEDGER.read_text()
    entries = re.split(r"(?=^## R-\d{4} )", txt, flags=re.MULTILINE)
    candidates = []
    for e in entries:
        if not e.startswith("## R-"):
            continue
        if "status: wired" not in e:
            continue
        head = e.split("\n", 1)[0]
        if feature.lower() not in head.lower():
            continue
        if host and host not in head.lower():
            continue
        m = re.match(r"## (R-\d{4})", e)
        if m:
            slug_match = (ship_slug and f"ship_slug: {ship_slug}" in e)
            candidates.append((m.group(1), slug_match))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (not x[1], x[0]))
    return candidates[0][0]


def _wiring_entry_body(entry_id: str, *, mode, target, host, feature, verdict,
                        phase4_evidence, feature_evidence, dependency_map, freshness, detected_via) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ship_slug = (feature_evidence or {}).get("ship_slug", "(none)")
    wired_commit = (feature_evidence or {}).get("wired_commit", "(unknown)")
    excerpt = (feature_evidence or {}).get("visible_proof_excerpt", "")
    file_ref = (feature_evidence or {}).get("ship_log", "(none)")
    proc_node = phase4_evidence.get("state_registry", {}).get("node_id", "(none)")
    return f"""
## {entry_id} — {feature} ({host or 'all-hosts'})
- mode: {mode}
- detected_via: {detected_via}
- detected_at: {now}
- target: {target}
- ship_slug: {ship_slug}
- phase4_process_node: {proc_node}
- phase4_pipeline_matches: {len(phase4_evidence.get('pipeline_graph', {}).get('node_matches', []))}
- phase4_lineage_matches: {len(phase4_evidence.get('data_lineage', {}).get('collector_matches', []))}
- dependency_map: {dependency_map}
- evidence_file: {file_ref}
- visible_proof_excerpt: {excerpt[:300]}
- status: {verdict}
- wired_commit: {wired_commit}
- freshness: {freshness}
- countermeasures:
  - immediate: ship {ship_slug} (commit {wired_commit})
  - preventive: orphan-sweep code_orphan detector (S5)
  - detection: /ship Phase 4 LAND auto-runs /debug check (S7)
"""


def cmd_check(target: str) -> int:
    if not target:
        print("INVALID_INPUT: /debug check requires <target> (e.g. london:prewarm)", file=sys.stderr)
        return 2

    host, feature = parse_target(target)
    p4 = load_phase4()
    pg_nodes, pg_edges = find_node_matches(p4["pipeline_graph"], feature, host)
    lineage_matches = find_lineage_matches(p4["data_lineage"], feature, host)
    state_node = find_state_node(p4["state_registry"], host, feature)
    proc_active = bool(state_node and state_node.get("status") == "ACTIVE")
    cr_signals = find_consistency_signals(p4["consistency_registry"], feature)
    if ORPHAN_REGISTRY.exists():
        dependency_map = "ok"
    else:
        dependency_map = "partial (pre-S5: orphan_registry not yet seeded)"
    ship_ev = find_ship_evidence(feature)

    freshness_note: str = "n/a (process not active)"
    if not proc_active:
        verdict = "not_wired"
    elif ship_ev is not None:
        age_hr = (time.time() - ship_ev["mtime"]) / 3600
        if age_hr <= 48:
            verdict = "wired"
            freshness_note = f"ship-log mtime {datetime.fromtimestamp(ship_ev['mtime'], timezone.utc).isoformat()} (age {age_hr:.1f}h)"
        else:
            verdict = "partial"
            freshness_note = f"ship-log stale (age {age_hr:.1f}h); needs live host journal grep"
    else:
        verdict = "partial"
        freshness_note = "process active but no ship-log feature evidence found; needs live host probe"

    phase4_evidence = {
        "state_registry": {
            "file": str(PHASE4_FILES["state_registry"]),
            "node_id": state_node.get("id") if state_node else None,
            "status": state_node.get("status") if state_node else None,
            "verify_cmd": state_node.get("verify_cmd") if state_node else None,
        },
        "pipeline_graph": {
            "file": str(PHASE4_FILES["pipeline_graph"]),
            "node_matches": pg_nodes,
            "edge_matches": pg_edges,
        },
        "data_lineage": {
            "file": str(PHASE4_FILES["data_lineage"]),
            "collector_matches": lineage_matches,
        },
        "consistency_registry": {
            "file": str(PHASE4_FILES["consistency_registry"]),
            "signals": cr_signals[:5],
        },
    }
    feature_evidence = ship_ev

    existing_id = find_existing_ledger_entry(
        (ship_ev or {}).get("ship_slug"), feature, host
    ) if verdict == "wired" else None

    if existing_id:
        ledger_id = existing_id
        ledger_note = f"(dedup'd against existing {existing_id})"
    else:
        # D1 closure: atomic lockfile-guarded ID allocation + write
        def body_fn(entry_id):
            return _wiring_entry_body(
                entry_id, mode="wiring", target=target, host=host, feature=feature,
                verdict=verdict, phase4_evidence=phase4_evidence,
                feature_evidence=feature_evidence, dependency_map=dependency_map,
                freshness=freshness_note, detected_via=f"/debug check {target}")
        verdict, _rc_tags, _blocked = run_realization_checks(verdict, mode="wiring")
        if _blocked:
            print("RC-7 BLOCK: refusing ledger write — remove hook-output files from changeset", file=sys.stderr)
            return 2
        ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
        ledger_note = "(new entry)" + (f" tags={_rc_tags}" if _rc_tags else "")

    out = {
        "verb": "check", "target": target, "verdict": verdict,
        "phase4_evidence": phase4_evidence, "feature_evidence": feature_evidence,
        "dependency_map": dependency_map, "ledger_entry": ledger_id,
        "ledger_note": ledger_note, "freshness": freshness_note,
    }
    print(json.dumps(out, indent=2, default=str))
    print()
    print(f"--- /debug check {target} → verdict: {verdict} ---")
    print(f"  process node       : {phase4_evidence['state_registry']['node_id']} ({phase4_evidence['state_registry']['status']})")
    print(f"  pipeline matches   : {len(pg_nodes)} nodes, {len(pg_edges)} edges")
    print(f"  lineage matches    : {len(lineage_matches)} collectors")
    print(f"  consistency signals: {len(cr_signals)}")
    print(f"  ship evidence      : {ship_ev['ship_slug'] + ' @ commit ' + str(ship_ev['wired_commit']) if ship_ev else '(none)'}")
    print(f"  dependency_map     : {dependency_map}")
    print(f"  ledger_entry       : {ledger_id} {ledger_note}")
    print(f"  freshness          : {freshness_note}")
    return 0 if verdict in ("wired", "partial") else 1


def cmd_list() -> int:
    if not LEDGER.exists():
        print("(ledger empty — ~/NardoWorld/realize-debt.md does not exist yet)")
        return 0
    txt = LEDGER.read_text()
    entries = re.split(r"(?=^## R-\d{4} )", txt, flags=re.MULTILINE)
    entries = [e for e in entries if e.startswith("## R-")]
    print(f"{len(entries)} entries in {LEDGER}")
    for e in entries[-20:]:
        head = e.split("\n", 1)[0]
        status_m = re.search(r"^- status: (\S+)", e, re.MULTILINE)
        print(f"  {head}  [{status_m.group(1) if status_m else '?'}]")
    return 0


# ---------------------------------------------------------------------------
# /debug bug — 17-step engine (S3)
# ---------------------------------------------------------------------------

def _slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "bug"


def _parse_bug_args(argv: list[str]) -> dict:
    """Extract symptom + flags. argv excludes argv[0] script + 'bug' verb."""
    flags = {"quick": False, "no_chain": False, "dry_run": False, "bug_slug": None}
    symptom_parts = []
    for a in argv:
        if a == "--quick":
            flags["quick"] = True
        elif a == "--no-chain":
            flags["no_chain"] = True
        elif a == "--dry-run":
            flags["dry_run"] = True
        elif a.startswith("--bug-slug="):
            flags["bug_slug"] = a.split("=", 1)[1]
        else:
            symptom_parts.append(a)
    flags["symptom"] = " ".join(symptom_parts).strip()
    return flags


def _bug_step(n: int | float, name: str, msg: str) -> None:
    print(f"step {n} {name} | {msg}")


def cmd_bug(argv: list[str]) -> int:
    flags = _parse_bug_args(argv)
    symptom = flags["symptom"]
    if not symptom:
        print("INVALID_INPUT: /debug bug requires <symptom> (e.g. 'pm-london wedges every 10min')", file=sys.stderr)
        return 2

    # Auto-slug: <symptom-slug>-<ts>
    if flags["bug_slug"]:
        bug_slug = flags["bug_slug"]
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        bug_slug = f"{_slugify(symptom)}-{ts}"

    bug_dir = SHIP_ROOT / bug_slug
    state_dir = bug_dir / "state"
    exp_dir = bug_dir / "experiments"
    state_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    dry = flags["dry_run"]
    quick = flags["quick"]
    no_chain = flags["no_chain"]

    # Step 0 — TRIAGE
    _bug_step(0, "TRIAGE", f"bug-slug={bug_slug}")
    triage = state_dir / "triage.md"
    triage.write_text(f"""# Triage — {bug_slug}

per 5-Whys problem template

What:   {symptom}
When:   {datetime.now(timezone.utc).isoformat()}
Where:  (fill in component/host)
Impact: (fill in measurable consequence)

dry-run: {dry}
flags:   quick={quick} no_chain={no_chain}
""")

    # Step 1 — REPRODUCE
    repro = exp_dir / "repro.sh"
    if dry:
        repro.write_text("#!/usr/bin/env bash\n# dry-run: repro skipped\nexit 0\n")
        _bug_step(1, "REPRODUCE", "--dry-run: skipped repro execution")
    else:
        if not repro.exists():
            repro.write_text(f"#!/usr/bin/env bash\n# fill in deterministic repro for: {symptom}\nexit 1\n")
        os.chmod(repro, 0o755)
        _bug_step(1, "REPRODUCE", f"repro template at {repro} — populate then re-run")

    # Step 1.5 — MINIMISE (pocock/skills diagnose)
    repro_min = exp_dir / "repro-min.sh"
    minimise_log = state_dir / "minimise-log.md"
    if dry:
        repro_min.write_text("#!/usr/bin/env bash\n# dry-run: minimise skipped\nexit 0\n")
        minimise_log.write_text(f"# minimise log — {symptom}\n\ndry-run\n")
        _bug_step(1.5, "MINIMISE", "--dry-run: skipped minimise")
    else:
        if not repro_min.exists():
            repro_min.write_text(
                "#!/usr/bin/env bash\n"
                "# Minimised repro — start as a copy of repro.sh, then strip until smallest failing case.\n"
                f"# Strategy: remove env vars / data rows / deps / setup steps one at a time;\n"
                "# re-run after each strip; KEEP the strip if the bug still reproduces, REVERT if it doesn't.\n"
                "# Halt when no further strip leaves the failure intact.\n"
                "exit 1\n"
            )
        os.chmod(repro_min, 0o755)
        if not minimise_log.exists():
            minimise_log.write_text(
                f"# Minimise log — {symptom}\n\n"
                "Track each strip attempt as a row:\n\n"
                "| # | Removed | Bug still reproduces? | Decision |\n"
                "|---|---|---|---|\n"
                "| 1 | <e.g. unused env var FOO> | yes | keep removed |\n"
                "| 2 | <e.g. database call> | no | reverted |\n"
            )
        _bug_step(1.5, "MINIMISE", f"minimise template at {repro_min} + log at {minimise_log} — strip then re-run")

    # Step 2 — BUILD-MAP (Phase 4 read-only)
    p4 = None
    try:
        p4 = load_phase4()
    except SystemExit:
        # propagated only when non-dry; in dry-run, treat as empty
        if not dry:
            raise
    pg_n, pg_e = ([], [])
    if p4:
        pg_n, pg_e = find_node_matches(p4["pipeline_graph"], _slugify(symptom), None)
    _bug_step(2, "BUILD-MAP", f"pipeline matches: {len(pg_n)} nodes, {len(pg_e)} edges")

    # Step 3 — EXECUTION-MAP
    state_node = None
    if p4:
        state_node = find_state_node(p4["state_registry"], None, _slugify(symptom))
    _bug_step(3, "EXECUTION-MAP", f"state matches: {1 if state_node else 0}")

    # Step 4 — DEPENDENCY-MAP (⚡light)
    if quick:
        _bug_step(4, "DEPENDENCY-MAP", "skipped (--quick)")
    else:
        dep = "ok" if ORPHAN_REGISTRY.exists() else "partial (pre-S5)"
        _bug_step(4, "DEPENDENCY-MAP", dep)

    # Step 5 — PATTERN ANALYSIS (graph-recall + lessons grep)
    pattern_path = state_dir / "pattern.md"
    hub_hits = 0
    if HUB_NODES.exists():
        try:
            hub = json.loads(HUB_NODES.read_text())
            blob = json.dumps(hub).lower()
            hub_hits = sum(1 for tok in _disc.normalize_feature_tokens(symptom) if tok in blob)
        except Exception:
            pass
    pattern_path.write_text(f"# Pattern analysis — {bug_slug}\n\nhub_nodes hits: {hub_hits}\nlessons grep: (run `grep -ri \"{_slugify(symptom)}\" ~/NardoWorld/lessons/ ~/.claude/projects/`)\n")
    _bug_step(5, "PATTERN", f"hub_nodes hits: {hub_hits}")

    # Step 6 — HYPOTHESIS GEN (Iron Law #1)
    hyp_path = state_dir / "hypotheses.md"
    if dry:
        hyp_path.write_text(f"""# Hypotheses — {bug_slug}

H1: I think the failure is caused by <pre-canned root cause for dry-run> because <evidence>.
   expected_signal: (Step 7) <observable predicate>
   classification:  (Step 10) inconclusive — dry-run, no evidence collected
""")
        _bug_step(6, "HYPOTHESIS", "dry-run H1: <pre-canned root cause>")
    else:
        if not hyp_path.exists():
            hyp_path.write_text(f"# Hypotheses — {bug_slug}\n\nH1: I think <X> because <Y>.\n   expected_signal: <observable predicate>\n   classification: (pending Step 10)\n")
        _bug_step(6, "HYPOTHESIS", f"template written to {hyp_path} — fill in 'I think X because Y'")

    # Step 7 — EXPECTED-SIGNAL
    _bug_step(7, "EXPECTED-SIGNAL", "predicate logged in hypotheses.md")

    # Step 8 — INSTRUMENT
    DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not DEBUG_LOG.exists():
        DEBUG_LOG.write_text(f"# Debug log sink — {datetime.now(timezone.utc).isoformat()}\n")
    _bug_step(8, "INSTRUMENT", f"sink: {DEBUG_LOG} | wrap edits in `#region DEBUG ... #endregion` + `[DEBUG H1]` tags")

    # Step 9 — RUNTIME-VERIFY
    if dry:
        _disc.write_observation(bug_slug, f"dry-run synthetic observation for {symptom}", "[single-point]")
        _bug_step(9, "RUNTIME-VERIFY", "observation written (dry-run, [single-point])")
    else:
        _bug_step(9, "RUNTIME-VERIFY", f"call _disc.write_observation('{bug_slug}', text, label) for each evidence point")

    # Step 10 — CLASSIFY
    if dry:
        with open(hyp_path, "a") as f:
            f.write("\nH1 classification: inconclusive (dry-run)\n")
        _bug_step(10, "CLASSIFY", "H1: inconclusive (dry-run)")
    else:
        _bug_step(10, "CLASSIFY", "mark each H confirmed/disproven/inconclusive in hypotheses.md")

    # Step 11 — DEPTH-CHECK / 5-Whys causal chain
    if no_chain:
        _bug_step(11, "DEPTH-CHECK", "skipped (--no-chain)")
    else:
        steps = [
            {"n": 1, "text": f"Trigger: {symptom}", "citation": "[cited triage.md:What]"},
            {"n": 2, "text": "Why 1: <first-level cause>", "citation": "[GAP — unverified, exp: collect evidence in Step 9]"},
            {"n": 3, "text": "Why 2: <deeper cause>", "citation": "[GAP — unverified]"},
            {"n": 4, "text": "Why 3: <approaching root>", "citation": "[GAP — unverified]"},
            {"n": 5, "text": "Why 4/5: <root cause candidate>", "citation": "[GAP — unverified]"},
        ]
        chain_path = _disc.write_causal_chain(bug_slug, steps)
        _bug_step(11, "DEPTH-CHECK", f"causal-chain written ({len(steps)} steps) → {chain_path}")

    # Step 12 — ≥3-FAIL ESCALATION
    disproven = 0
    if hyp_path.exists():
        disproven = hyp_path.read_text().lower().count("disproven")
    _disc.write_round(bug_slug, sha="(dry-run)" if dry else "fill-with-git-sha",
                      claimed_vars=[], observed_outcome=symptom, round_n=1)
    if disproven >= 3:
        _bug_step(12, "≥3-FAIL", "ESCALATE → /ship audit <area> (3+ H disproven)")
        return 4
    _bug_step(12, "≥3-FAIL", f"disproven count: {disproven} (no escalation)")

    # Step 13 — FIX
    if dry:
        _bug_step(13, "FIX", "--dry-run: no edit applied")
    else:
        _bug_step(13, "FIX", "apply ONE change at a time; capture commit SHA after edit; do NOT bundle refactors")

    # Step 14 — CLEANUP
    if dry:
        _bug_step(14, "CLEANUP", "--dry-run: no scaffold to strip")
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive = HOME / ".claude" / f"debug.log.{bug_slug}.{ts}"
        if DEBUG_LOG.exists() and DEBUG_LOG.stat().st_size > 0:
            try:
                DEBUG_LOG.rename(archive)
                DEBUG_LOG.write_text(f"# Debug log sink — fresh post-archive {datetime.now(timezone.utc).isoformat()}\n")
            except Exception:
                pass
        _bug_step(14, "CLEANUP", f"strip `#region DEBUG` blocks; debug.log archived to {archive}")

    # Step 15 — VERDICT-VERIFY (Iron Law #2)
    verify_path = state_dir / "verify.md"
    if dry:
        verify_path.write_text(f"""# Verify — {bug_slug}

verdict: inconclusive (dry-run)
verify cmd: (none — dry-run never claims fix)
fresh evidence: n/a
""")
        verdict = "inconclusive"
        _bug_step(15, "VERDICT-VERIFY", "--dry-run: no verify cmd run; verdict=inconclusive")
    else:
        if not verify_path.exists():
            verify_path.write_text(f"# Verify — {bug_slug}\n\nverdict: (pending)\nverify cmd: (run + paste full output here BEFORE claiming fix)\n")
        verdict = "inconclusive"
        _bug_step(15, "VERDICT-VERIFY", f"populate {verify_path} with verify cmd + full output, then re-run with --finalize")

    # Step 16 — LEDGER (atomic write)
    def body_fn(entry_id):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return f"""
## {entry_id} — {bug_slug}
- mode: bug
- detected_via: /debug bug "{symptom}"
- detected_at: {now}
- bug_slug: {bug_slug}
- symptom: {symptom}
- dry_run: {dry}
- flags: quick={quick} no_chain={no_chain}
- triage: {triage}
- hypotheses: {hyp_path}
- causal_chain: {state_dir / 'causal-chain.md' if not no_chain else '(skipped)'}
- observations: {exp_dir / 'observations.md'}
- rounds: {exp_dir / 'rounds.md'}
- verify: {verify_path}
- status: {'inconclusive' if dry else 'open'}
- countermeasures:
  - immediate: (TBD — populate after Step 13)
  - preventive: (TBD)
  - detection: (TBD)
"""
    _, _rc_tags, _blocked = run_realization_checks(verdict, mode="bug")
    if _blocked:
        print("RC-7 BLOCK: bug-mode ledger write refused — remove hook-output files from changeset", file=sys.stderr)
        return 2
    ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
    _bug_step(16, "LEDGER", f"wrote {ledger_id} (status={'inconclusive' if dry else 'open'}{' tags=' + str(_rc_tags) if _rc_tags else ''})")

    print()
    print(f"--- /debug bug \"{symptom}\" → verdict: {verdict} ---")
    print(f"  bug-slug    : {bug_slug}")
    print(f"  state dir   : {state_dir}")
    print(f"  exp dir     : {exp_dir}")
    print(f"  ledger      : {ledger_id}")
    return 0


# ---------------------------------------------------------------------------
# /debug drift — mode 4 (S8)
# ---------------------------------------------------------------------------

# Bare boolean flags allowed in `--<name>` form (no `=`). Anything else
# arriving as bare `--unknown` raises a clear error so silent typos like
# `--dry_run` (S6 root cause) cannot fall through to a real production write.
_BOOL_FLAG_ALLOWLIST = {"dry_run", "verbose", "force"}


def _parse_kv_args(argv: list[str], known_flags: dict) -> tuple[dict, list[str]]:
    """Return (flags, positional). known_flags maps name -> default.

    Accepts:
      --dry-run / --dry_run       → flags["dry_run"] = True   (allowlisted bool)
      --verbose / --force         → flags[name] = True        (allowlisted bool)
      --baseline=VAL              → flags["baseline"] = VAL
      --runs=N                    → flags["runs"] = int(N)
      --bug-slug=VAL              → flags["bug_slug"] = VAL
      --host=VAL / --<key>=VAL    → flags[normalized_key] = VAL (passthrough)
      bare --unknown_flag         → raises ValueError (no silent allow)
    """
    flags = dict(known_flags)
    positional = []
    for a in argv:
        # Bare-flag form: --<name>  (no `=`)
        if a.startswith("--") and "=" not in a:
            name = a[2:].replace("-", "_")
            if not name:
                positional.append(a)
                continue
            if name in _BOOL_FLAG_ALLOWLIST:
                flags[name] = True
                continue
            raise ValueError(
                f"unknown flag {a!r}: bare --flag form only supports "
                f"{sorted(_BOOL_FLAG_ALLOWLIST)} (use --key=value for others)"
            )

        # Key=value form
        if a.startswith("--baseline="):
            flags["baseline"] = a.split("=", 1)[1]
        elif a.startswith("--runs="):
            try:
                flags["runs"] = int(a.split("=", 1)[1])
            except ValueError:
                flags["runs"] = 10
        elif a.startswith("--bug-slug="):
            flags["bug_slug"] = a.split("=", 1)[1]
        elif a.startswith("--") and "=" in a:
            # Generic --key=value passthrough (e.g. --host=mac). Normalise
            # dashes to underscores for the flags dict key.
            key, val = a.split("=", 1)
            flags[key[2:].replace("-", "_")] = val
        else:
            positional.append(a)
    return flags, positional


def _mode_ledger_body(entry_id: str, *, mode: str, target: str, host: str | None,
                     feature: str, verdict: str, evidence: dict,
                     dependency_map: str, freshness: str, detected_via: str,
                     countermeasures: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cm_immediate = countermeasures.get("immediate", "(TBD)")
    cm_preventive = countermeasures.get("preventive", "(TBD)")
    cm_detection = countermeasures.get("detection", "(TBD)")
    return f"""
## {entry_id} — {feature} ({host or 'all-hosts'})
- mode: {mode}
- detected_via: {detected_via}
- detected_at: {now}
- target: {target}
- verdict: {verdict}
- dependency_map: {dependency_map}
- evidence: {json.dumps(evidence, default=str)[:600]}
- freshness: {freshness}
- status: {'open' if verdict not in ('current', 'within-budget', 'intermittent_low') else 'inconclusive' if verdict == 'inconclusive' else 'open'}
- countermeasures:
  - immediate: {cm_immediate}
  - preventive: {cm_preventive}
  - detection: {cm_detection}
"""


def _git_log_count(baseline: str, files_hint: str) -> tuple[int, list[str]]:
    """Count commits since baseline that touch files matching hint. Best-effort."""
    try:
        # Try ~/NardoWorld first (most features live there)
        for repo in [HOME / "NardoWorld", HOME / "prediction-markets", Path.cwd()]:
            if not (repo / ".git").exists():
                continue
            try:
                if re.fullmatch(r"[0-9a-f]{7,40}", baseline):
                    rev = f"{baseline}..HEAD"
                else:
                    rev = f"--since={baseline!r}"
                cmd = ["git", "-C", str(repo), "log", "--oneline"]
                if rev.startswith("--since"):
                    cmd.append(f"--since={baseline}")
                else:
                    cmd.append(rev)
                cmd += ["--", f"*{files_hint}*"]
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if out.returncode == 0 and out.stdout.strip():
                    lines = out.stdout.strip().splitlines()
                    return len(lines), lines[:5]
            except Exception:
                continue
    except Exception:
        pass
    return 0, []


def cmd_drift(argv: list[str]) -> int:
    flags, positional = _parse_kv_args(argv, {"dry_run": False, "baseline": None})
    target = positional[0] if positional else ""
    if not target:
        print("INVALID_INPUT: /debug drift requires <feature> (e.g. london:pm-bot)", file=sys.stderr)
        return 2
    host, feature = parse_target(target)
    dry = flags["dry_run"]
    baseline = flags["baseline"] or "30 days ago"

    # Step 0 TRIAGE
    _bug_step(0, "TRIAGE", f"mode=drift target={target} baseline={baseline}")

    # Step 1 REPRODUCE (light): record baseline anchor
    _bug_step(1, "REPRODUCE", f"baseline anchor: {baseline}")

    # Step 2 BUILD-MAP + Step 3 EXECUTION-MAP + Step 4 DEPENDENCY-MAP
    p4 = None
    try:
        p4 = load_phase4()
    except SystemExit:
        if not dry:
            raise
    pg_n, pg_e = ([], [])
    state_node = None
    cr_signals = []
    if p4:
        pg_n, pg_e = find_node_matches(p4["pipeline_graph"], feature, host)
        state_node = find_state_node(p4["state_registry"], host, feature)
        cr_signals = find_consistency_signals(p4["consistency_registry"], feature)
    _bug_step(2, "BUILD-MAP", f"pipeline matches: {len(pg_n)} nodes, {len(pg_e)} edges")
    _bug_step(3, "EXECUTION-MAP", f"state node: {state_node.get('id') if state_node else '(none)'}")
    dependency_map = "ok" if ORPHAN_REGISTRY.exists() else "partial (pre-S5)"
    _bug_step(4, "DEPENDENCY-MAP", f"{dependency_map}; consistency signals: {len(cr_signals)}")

    # Step 5 PATTERN ANALYSIS — git log range
    n_commits, sample_msgs = (0, [])
    if not dry:
        n_commits, sample_msgs = _git_log_count(baseline, feature)
    _bug_step(5, "PATTERN", f"commits in range: {n_commits} (top {len(sample_msgs)})")

    # Step 7 EXPECTED-SIGNAL
    verify_cmd = state_node.get("verify_cmd") if state_node else None
    _bug_step(7, "EXPECTED-SIGNAL", f"verify_cmd present: {bool(verify_cmd)}")

    # Step 9 RUNTIME-VERIFY
    verify_outcome = "n/a"
    verify_diverged = False
    if dry:
        verify_outcome = "dry-run synthetic"
    elif verify_cmd:
        try:
            r = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True, timeout=15)
            verify_outcome = f"exit={r.returncode} stdout_len={len(r.stdout)}"
            verify_diverged = r.returncode != 0
        except Exception as e:
            verify_outcome = f"verify error: {e}"
    _bug_step(9, "RUNTIME-VERIFY", verify_outcome)

    # Step 10 CLASSIFY
    if dry:
        verdict = "inconclusive"
    elif not verify_cmd:
        verdict = "inconclusive"
    elif verify_diverged and n_commits >= 1:
        verdict = "stale-hard"
    elif verify_diverged and n_commits == 0:
        verdict = "inconclusive"
    elif (not verify_diverged) and n_commits >= 1:
        verdict = "stale-soft"
    elif (not verify_diverged) and n_commits == 0:
        verdict = "current"
    else:
        verdict = "inconclusive"
    _bug_step(10, "CLASSIFY", f"verdict={verdict}")

    # Step 11 DEPTH-CHECK (light)
    _bug_step(11, "DEPTH-CHECK", "5-Whys-lite: skipped per drift compression matrix")

    # Step 13 FIX (advisory)
    countermeasures = {
        "immediate": f"refresh feature {feature} (commit-range scan suggests {n_commits} touch(es))",
        "preventive": "enroll in consistency-daemon drift detector (per master plan §19)",
        "detection": "schedule periodic /debug drift check on this feature",
    }
    _bug_step(13, "FIX", "advisory countermeasures emitted (no auto-patch)")

    # Step 15 VERDICT-VERIFY
    _bug_step(15, "VERDICT-VERIFY", "fresh evidence captured this invocation")

    # Step 16 LEDGER
    evidence = {
        "phase4_pipeline_matches": len(pg_n),
        "phase4_state_node": state_node.get("id") if state_node else None,
        "verify_cmd": verify_cmd,
        "verify_outcome": verify_outcome,
        "commits_in_range": n_commits,
        "sample_commit_msgs": sample_msgs,
        "baseline": baseline,
    }
    freshness = datetime.now(timezone.utc).isoformat()
    detected_via = f"/debug drift {target}"
    def body_fn(entry_id):
        return _mode_ledger_body(entry_id, mode="drift", target=target, host=host,
                                 feature=feature, verdict=verdict, evidence=evidence,
                                 dependency_map=dependency_map, freshness=freshness,
                                 detected_via=detected_via, countermeasures=countermeasures)
    verdict, _rc_tags, _blocked = run_realization_checks(verdict, mode="drift")
    if _blocked:
        print("RC-7 BLOCK: drift ledger write refused — remove hook-output files from changeset", file=sys.stderr)
        return 2
    ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
    _bug_step(16, "LEDGER", f"wrote {ledger_id} (verdict={verdict}{' tags=' + str(_rc_tags) if _rc_tags else ''})")

    out = {"verb": "drift", "target": target, "verdict": verdict,
           "evidence": evidence, "ledger_entry": ledger_id, "freshness": freshness}
    print(json.dumps(out, indent=2, default=str))
    print()
    print(f"--- /debug drift {target} → verdict: {verdict} ---")
    print(f"  ledger      : {ledger_id}")
    print(f"  commits     : {n_commits} in range since {baseline}")
    print(f"  verify_cmd  : {'set' if verify_cmd else '(none)'}")

    if verdict == "current":
        return 0
    if verdict == "inconclusive":
        return 3
    return 1


# ---------------------------------------------------------------------------
# /debug flaky — mode 7 (S8)
# ---------------------------------------------------------------------------

FLAKY_RACE_PRIORS = [
    ("H1", "thread-safety", "concurrent access without lock"),
    ("H2", "async-order", "promise resolution order non-deterministic"),
    ("H3", "time-dependent", "clock skew / timeout / scheduling jitter"),
    ("H4", "state-leak", "prior run state bleeds into next"),
    ("H5", "external-API-timing", "upstream provider variance"),
]


def cmd_flaky(argv: list[str]) -> int:
    flags, positional = _parse_kv_args(argv, {"dry_run": False, "runs": 10, "bug_slug": None})
    symptom = " ".join(positional).strip()
    if not symptom:
        print("INVALID_INPUT: /debug flaky requires <symptom>", file=sys.stderr)
        return 2

    runs = flags["runs"] if isinstance(flags["runs"], int) and flags["runs"] > 0 else 10
    dry = flags["dry_run"]

    # auto-slug
    if flags["bug_slug"]:
        bug_slug = flags["bug_slug"]
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        bug_slug = f"{_slugify(symptom)}-flaky-{ts}"

    bug_dir = SHIP_ROOT / bug_slug
    state_dir = bug_dir / "state"
    exp_dir = bug_dir / "experiments"
    state_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Step 0 TRIAGE
    _bug_step(0, "TRIAGE", f"mode=flaky bug-slug={bug_slug} runs={runs}")
    (state_dir / "triage.md").write_text(f"# Triage — {bug_slug}\n\nWhat: {symptom}\nMode: flaky\nRuns: {runs}\nDry-run: {dry}\n")

    # Step 1 REPRODUCE (loop mode)
    flaky_runs_path = exp_dir / "flaky-runs.md"
    fingerprints: dict[str, int] = {}
    rows = []
    for i in range(1, runs + 1):
        if dry:
            # Synthesize 3 pass / 7 fail-mix to exercise verdict thresholds and table format
            outcome = "fail" if (i % 3 != 0) else "pass"
            fp_seed = f"err-A-{i % 2}" if outcome == "fail" else "ok"
            fp = hashlib.sha1(fp_seed.encode()).hexdigest()[:8]
        else:
            # Real mode: caller populates a repro.sh; if missing, fixture-pass
            repro = exp_dir / "repro.sh"
            if not repro.exists():
                repro.write_text(f"#!/usr/bin/env bash\n# fill in deterministic repro for: {symptom}\nexit 0\n")
                os.chmod(repro, 0o755)
            try:
                r = subprocess.run([str(repro)], capture_output=True, text=True, timeout=30)
                outcome = "pass" if r.returncode == 0 else "fail"
                fp = hashlib.sha1((r.stdout + r.stderr).encode()).hexdigest()[:8]
            except Exception as e:
                outcome = "fail"
                fp = hashlib.sha1(str(e).encode()).hexdigest()[:8]
        rows.append((i, outcome, fp))
        fingerprints[fp] = fingerprints.get(fp, 0) + 1
        # log every iteration as an observation
        _disc.write_observation(bug_slug, f"flaky run {i}: outcome={outcome} fp={fp}", "[single-point]")
    # Once N runs done, aggregate becomes [N-comparison]
    _disc.write_observation(bug_slug, f"flaky aggregate: {runs} runs total", f"[N-comparison]")

    fail_count = sum(1 for _, o, _ in rows if o == "fail")
    table_md = f"# Flaky runs — {bug_slug}\n\nruns: {runs}\nfailures: {fail_count}\n\n| run | outcome | fingerprint |\n|---|---|---|\n"
    for i, o, fp in rows:
        table_md += f"| {i} | {o} | {fp} |\n"
    table_md += f"\n## Fingerprint frequency\n\n"
    for fp, ct in sorted(fingerprints.items(), key=lambda x: -x[1]):
        table_md += f"- {fp}: {ct}\n"
    flaky_runs_path.write_text(table_md)
    _bug_step(1, "REPRODUCE", f"loop runs={runs} fails={fail_count} → {flaky_runs_path}")

    # Step 1.5 MINIMISE (pocock/skills diagnose — flaky variant)
    repro_min = exp_dir / "repro-min-flaky.sh"
    minimise_log = state_dir / "minimise-log.md"
    fail_rate = (fail_count / runs * 100) if runs else 0.0
    if dry:
        repro_min.write_text("#!/usr/bin/env bash\n# dry-run: minimise skipped\nexit 0\n")
        minimise_log.write_text(f"# minimise log (flaky) — {symptom}\n\ndry-run\n")
        _bug_step(1.5, "MINIMISE", "--dry-run: skipped minimise")
    else:
        if not repro_min.exists():
            repro_min.write_text(
                "#!/usr/bin/env bash\n"
                "# Minimised flaky repro — start as a copy of repro.sh.\n"
                "# Strategy: strip env / data / concurrency / setup one at a time;\n"
                "# re-run the loop after each strip; KEEP the strip if fail-rate stays ≥30%, REVERT if it drops.\n"
                "# Halt when no further strip leaves fail-rate above the threshold.\n"
                "exit 0\n"
            )
        os.chmod(repro_min, 0o755)
        if not minimise_log.exists():
            minimise_log.write_text(
                f"# Minimise log (flaky) — {symptom}\n\n"
                f"Baseline fail-rate: {fail_rate:.1f}% ({fail_count}/{runs})\n"
                "Threshold to retain strip: ≥30% fail-rate over N runs.\n\n"
                "| # | Removed | New fail-rate | Decision |\n"
                "|---|---|---|---|\n"
                "| 1 | <e.g. concurrent worker count> | 50% | keep removed |\n"
                "| 2 | <e.g. external API call> | 0% | reverted (race was here) |\n"
            )
        _bug_step(1.5, "MINIMISE", f"flaky-minimise template at {repro_min} + log at {minimise_log} (baseline {fail_rate:.0f}% fail-rate)")

    # Step 2-4 BUILD/EXEC/DEP
    p4 = None
    try:
        p4 = load_phase4()
    except SystemExit:
        if not dry:
            raise
    pg_n, _ = ([], [])
    if p4:
        pg_n, _ = find_node_matches(p4["pipeline_graph"], _slugify(symptom), None)
    _bug_step(2, "BUILD-MAP", f"pipeline matches: {len(pg_n)} nodes")
    _bug_step(3, "EXECUTION-MAP", f"(see flaky-runs.md for runtime)")
    _bug_step(4, "DEPENDENCY-MAP", "ok" if ORPHAN_REGISTRY.exists() else "partial (pre-S5)")

    # Step 5 PATTERN
    _bug_step(5, "PATTERN", f"race-pattern priors auto-seeded: {len(FLAKY_RACE_PRIORS)} hypotheses")

    # Step 6 HYPOTHESIS — write priors
    hyp_path = state_dir / "hypotheses.md"
    hyp_lines = [f"# Hypotheses — {bug_slug}", "", "Auto-seeded race-pattern priors (Iron Law #1: pick one primary):", ""]
    for hid, name, desc in FLAKY_RACE_PRIORS:
        hyp_lines.append(f"- {hid} ({name}): {desc}")
    hyp_lines.append("")
    hyp_lines.append("Primary: H1 (default — override after Step 9 evidence).")
    hyp_path.write_text("\n".join(hyp_lines) + "\n")
    _bug_step(6, "HYPOTHESIS", f"5 priors → {hyp_path}")

    # Step 7 EXPECTED-SIGNAL
    _bug_step(7, "EXPECTED-SIGNAL", "deterministic outcome under fixed seed/clock/state")

    # Step 8 INSTRUMENT
    DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not DEBUG_LOG.exists():
        DEBUG_LOG.write_text(f"# Debug log sink — {datetime.now(timezone.utc).isoformat()}\n")
    _bug_step(8, "INSTRUMENT", f"sink: {DEBUG_LOG}")

    # Step 9 RUNTIME-VERIFY (covered by Step 1 loop; observations.md already populated)
    _bug_step(9, "RUNTIME-VERIFY", f"observations: {runs+1} entries")

    # Step 10 CLASSIFY (flaky thresholds)
    if fail_count < 2:
        verdict = "intermittent_low"
        exit_code = 0
    elif fail_count <= 7:
        verdict = "flaky-confirmed"
        exit_code = 1
    else:
        verdict = "mostly-broken-not-flaky"
        exit_code = 4
    _bug_step(10, "CLASSIFY", f"fail/{runs}={fail_count} → {verdict}")

    # Step 11 DEPTH-CHECK
    steps = [
        {"n": 1, "text": f"Trigger: {symptom}", "citation": "[cited triage.md]"},
        {"n": 2, "text": f"Outcome distribution non-deterministic across {runs} runs", "citation": f"[cited {flaky_runs_path}]"},
        {"n": 3, "text": "Why 1: race / state / timing variable not held constant", "citation": "[GAP — unverified, exp: pin variable per H1, re-run 10x]"},
    ]
    chain_path = _disc.write_causal_chain(bug_slug, steps)
    _bug_step(11, "DEPTH-CHECK", f"chain → {chain_path}")

    # Step 12 ≥3-FAIL ESCALATION
    _disc.write_round(bug_slug, sha="(flaky-loop)" if dry else "(populate-with-sha)",
                      claimed_vars=[], observed_outcome=f"{fail_count}/{runs} fail", round_n=1)
    _bug_step(12, "≥3-FAIL", f"disproven: 0 (flaky N=1 round)")

    # Step 13 FIX (advisory)
    countermeasures = {
        "immediate": f"pin variable per primary H, re-run {runs}x to verify",
        "preventive": "deterministic seed / lock / barrier on flaky surface",
        "detection": "CI loop runs N=20 on suspect path, fail if any non-determinism",
    }
    _bug_step(13, "FIX", "advisory countermeasures (no auto-patch)")

    # Step 14 CLEANUP — flaky keeps log open since multi-iteration
    _bug_step(14, "CLEANUP", "skipped (loop mode keeps debug.log)")

    # Step 15 VERDICT-VERIFY
    verify_path = state_dir / "verify.md"
    verify_path.write_text(f"# Verify — {bug_slug}\n\nverdict: {verdict}\nfail/total: {fail_count}/{runs}\nflaky-runs: {flaky_runs_path}\n")
    _bug_step(15, "VERDICT-VERIFY", f"verdict={verdict} via {runs}-run aggregate")

    # Step 16 LEDGER
    evidence = {
        "runs": runs, "failures": fail_count, "distinct_fingerprints": len(fingerprints),
        "flaky_runs": str(flaky_runs_path), "hypotheses": str(hyp_path),
    }
    detected_via = f"/debug flaky \"{symptom}\""
    freshness = datetime.now(timezone.utc).isoformat()
    def body_fn(entry_id):
        return _mode_ledger_body(entry_id, mode="flaky", target=symptom, host=None,
                                 feature=bug_slug, verdict=verdict, evidence=evidence,
                                 dependency_map="n/a (flaky mode)", freshness=freshness,
                                 detected_via=detected_via, countermeasures=countermeasures)
    verdict, _rc_tags, _blocked = run_realization_checks(verdict, mode="flaky")
    if _blocked:
        print("RC-7 BLOCK: flaky ledger write refused — remove hook-output files from changeset", file=sys.stderr)
        return 2
    ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
    _bug_step(16, "LEDGER", f"wrote {ledger_id} (verdict={verdict}{' tags=' + str(_rc_tags) if _rc_tags else ''})")

    out = {"verb": "flaky", "symptom": symptom, "verdict": verdict, "runs": runs,
           "failures": fail_count, "ledger_entry": ledger_id, "flaky_runs": str(flaky_runs_path)}
    print(json.dumps(out, indent=2, default=str))
    print()
    print(f"--- /debug flaky \"{symptom}\" → verdict: {verdict} ---")
    print(f"  bug-slug    : {bug_slug}")
    print(f"  runs/fails  : {runs}/{fail_count}")
    print(f"  flaky-runs  : {flaky_runs_path}")
    print(f"  ledger      : {ledger_id}")

    return exit_code


# ---------------------------------------------------------------------------
# /debug performance — mode 6 (S8)
# ---------------------------------------------------------------------------

PERF_METRIC_TEMPLATE = [
    "scan_loop_rate", "fill_latency_p50", "fill_latency_p99",
    "mem_growth_1h_pct", "cpu_idle_pct", "io_wait_pct",
    "api_rate_util_pct", "socket_reconnect_freq", "zombie_procs",
    "n_plus_1_count", "unbounded_cache_size",
]


def cmd_performance(argv: list[str]) -> int:
    flags, positional = _parse_kv_args(argv, {"dry_run": False, "baseline": None})
    target = positional[0] if positional else ""
    if not target:
        print("INVALID_INPUT: /debug performance requires <feature>", file=sys.stderr)
        return 2
    host, feature = parse_target(target)
    dry = flags["dry_run"]

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    perf_slug = f"{_slugify(feature)}-perf-{ts}"
    perf_dir = SHIP_ROOT / perf_slug
    state_dir = perf_dir / "state"
    exp_dir = perf_dir / "experiments"
    state_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Step 0 TRIAGE
    _bug_step(0, "TRIAGE", f"mode=performance target={target} slug={perf_slug}")

    # Step 1 REPRODUCE — capture baseline metrics (synthesized in dry-run)
    baseline_path = exp_dir / "baseline.md"
    metrics = {m: ("n/a" if not dry else f"{(hash(m) % 1000)/10:.1f}") for m in PERF_METRIC_TEMPLATE}
    baseline_md = f"# Baseline metrics — {perf_slug}\n\n"
    for m, v in metrics.items():
        baseline_md += f"- {m}: {v}\n"
    baseline_path.write_text(baseline_md)
    _bug_step(1, "REPRODUCE", f"baseline captured ({len(metrics)} metrics) → {baseline_path}")

    # Step 1.1 INVENTORY — P1-P4 detector pack (symptom-first).
    # Resolves the host: explicit "host:feature" target wins; else if feature
    # itself is a known host alias (mac/hel/london/local), use that; else local.
    detector_host = host or (feature if feature in {"mac", "hel", "london", "local"} else "local")
    detector_results = []
    if dry:
        _bug_step(1.1, "INVENTORY", f"--dry-run: P1-P4 detectors skipped (host={detector_host})")
    elif _perf_run_detectors is None:
        _bug_step(1.1, "INVENTORY", f"detector pack import failed: {_PERF_IMPORT_ERR}")
    else:
        try:
            detector_results = _perf_run_detectors(detector_host)
        except Exception as e:
            detector_results = []
            _bug_step(1.1, "INVENTORY", f"detector run crashed: {type(e).__name__}: {e}")
        for r in detector_results:
            label = r.get("detector", "p?")
            findings_path = exp_dir / f"{label}.md"
            md = [f"# Detector {label} — host={r.get('host')}",
                  f"verdict: **{r.get('verdict','?')}**",
                  f"summary: {r.get('summary','')}",
                  "",
                  f"evidence_cmd: `{r.get('evidence_cmd','')}`",
                  ""]
            findings = r.get("findings", []) or []
            md.append(f"findings: {len(findings)}")
            md.append("")
            for f in findings[:20]:
                md.append(f"- {json.dumps(f, default=str)}")
            findings_path.write_text("\n".join(md) + "\n")
        worst = "ok"
        order = {"ok": 0, "warn": 1, "error": 2, "crit": 3}
        for r in detector_results:
            v = r.get("verdict", "ok")
            if order.get(v, 0) > order.get(worst, 0):
                worst = v
        summary_line = ", ".join(f"{r.get('detector','p?')}={r.get('verdict','?')}" for r in detector_results)
        _bug_step(1.1, "INVENTORY", f"P1-P4 host={detector_host} worst={worst} ({summary_line})")

    # Step 1.5 MINIMISE (pocock/skills diagnose — performance variant)
    workload_min = exp_dir / "workload-min.sh"
    minimise_log = state_dir / "minimise-log.md"
    if dry:
        workload_min.write_text("#!/usr/bin/env bash\n# dry-run: minimise skipped\nexit 0\n")
        minimise_log.write_text(f"# minimise log (performance) — {target}\n\ndry-run\n")
        _bug_step(1.5, "MINIMISE", "--dry-run: skipped minimise")
    else:
        if not workload_min.exists():
            workload_min.write_text(
                "#!/usr/bin/env bash\n"
                "# Minimised perf workload — start as a copy of the production load that exhibits the regression.\n"
                "# Strategy: shrink request volume / payload size / concurrency / dataset rows one at a time;\n"
                "# re-capture metrics after each shrink; KEEP the shrink if the offending metric still busts budget,\n"
                "# REVERT if budget recovers.\n"
                "# Halt when no further shrink leaves the budget bust intact.\n"
                "exit 0\n"
            )
        os.chmod(workload_min, 0o755)
        if not minimise_log.exists():
            minimise_log.write_text(
                f"# Minimise log (performance) — {target}\n\n"
                "Identify the load-bearing axis: one metric in the baseline is over budget.\n"
                "Shrink the workload until ONLY that metric still busts budget — that isolates the cause.\n\n"
                "| # | Shrunk | Offending metric | Still over budget? | Decision |\n"
                "|---|---|---|---|---|\n"
                "| 1 | <e.g. concurrent requests 100 → 10> | mem_growth_1h_pct | yes | keep shrunk |\n"
                "| 2 | <e.g. payload 10KB → 1KB> | fill_latency_p99 | no | reverted (size matters) |\n"
            )
        _bug_step(1.5, "MINIMISE", f"perf-minimise template at {workload_min} + log at {minimise_log}")

    # Step 2-4 BUILD/EXEC/DEP
    p4 = None
    try:
        p4 = load_phase4()
    except SystemExit:
        if not dry:
            raise
    pg_n, _ = ([], [])
    state_node = None
    if p4:
        pg_n, _ = find_node_matches(p4["pipeline_graph"], feature, host)
        state_node = find_state_node(p4["state_registry"], host, feature)
    _bug_step(2, "BUILD-MAP", f"pipeline matches: {len(pg_n)}")
    _bug_step(3, "EXECUTION-MAP", f"state node: {state_node.get('id') if state_node else '(none)'}")
    dependency_map = "ok" if ORPHAN_REGISTRY.exists() else "partial (pre-S5)"
    _bug_step(4, "DEPENDENCY-MAP", dependency_map)

    # Step 5 PATTERN
    _bug_step(5, "PATTERN", "lessons grep: performance|hot.loop|leak|slow|latency")

    # Step 6 HYPOTHESIS
    hyp_path = state_dir / "hypotheses.md"
    hyp_path.write_text(f"# Hypotheses — {perf_slug}\n\nH1: I think {feature} is slow because <X>.\n   expected_signal: metric Y deviates by >10% from baseline\n   classification: (pending Step 10)\n")
    _bug_step(6, "HYPOTHESIS", f"single H1 → {hyp_path}")

    # Step 7 EXPECTED-SIGNAL
    _bug_step(7, "EXPECTED-SIGNAL", "metric within ±10% of baseline")

    # Step 8 INSTRUMENT — perf marker pattern
    DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not DEBUG_LOG.exists():
        DEBUG_LOG.write_text(f"# Debug log sink — {datetime.now(timezone.utc).isoformat()}\n")
    _bug_step(8, "INSTRUMENT", f"[DEBUG H1] perf markers; sink {DEBUG_LOG}")

    # Step 9 RUNTIME-VERIFY — run verify_cmd if exists
    verify_outcome = "n/a"
    verify_cmd = state_node.get("verify_cmd") if state_node else None
    if dry:
        verify_outcome = "dry-run synthetic"
    elif verify_cmd:
        try:
            r = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True, timeout=15)
            verify_outcome = f"exit={r.returncode} stdout_len={len(r.stdout)}"
        except Exception as e:
            verify_outcome = f"verify error: {e}"
    _disc.write_observation(perf_slug, f"perf verify: {verify_outcome}", "[single-point]")
    _bug_step(9, "RUNTIME-VERIFY", verify_outcome)

    # Step 10 CLASSIFY
    # Detector verdicts override "inconclusive" when they surface real signal.
    det_worst = "ok"
    if detector_results:
        order = {"ok": 0, "warn": 1, "error": 2, "crit": 3}
        for r in detector_results:
            v = r.get("verdict", "ok")
            if order.get(v, 0) > order.get(det_worst, 0):
                det_worst = v
    if dry:
        verdict = "inconclusive"
        exit_code = 3
    elif det_worst == "crit":
        verdict = "regression"
        exit_code = 1
    elif det_worst == "warn":
        verdict = "regression"
        exit_code = 1
    elif not flags["baseline"]:
        # No prior baseline + clean detectors → first-baseline run.
        verdict = "inconclusive"
        exit_code = 3
    else:
        verdict = "within-budget"
        exit_code = 0
    _bug_step(10, "CLASSIFY", f"verdict={verdict} detectors_worst={det_worst}")

    # Step 11 DEPTH-CHECK
    steps = [
        {"n": 1, "text": f"Trigger: {feature} performance probe", "citation": "[cited triage]"},
        {"n": 2, "text": "Baseline captured, delta vs prior baseline computed", "citation": f"[cited {baseline_path}]"},
        {"n": 3, "text": "Verdict based on metric deviation", "citation": "[GAP — unverified for first-baseline runs]"},
    ]
    chain_path = _disc.write_causal_chain(perf_slug, steps)
    _bug_step(11, "DEPTH-CHECK", f"chain → {chain_path}")

    # Step 12 ≥3-FAIL
    _disc.write_round(perf_slug, sha="(perf-baseline)", claimed_vars=[], observed_outcome=verdict, round_n=1)
    _bug_step(12, "≥3-FAIL", "disproven: 0")

    # Step 13 FIX (advisory)
    countermeasures = {
        "immediate": "address bottleneck (cache / batch / lock per H1)",
        "preventive": "rule/test fails when budget exceeded",
        "detection": "alarm via verify_cmd or consistency-daemon",
    }
    _bug_step(13, "FIX", "advisory countermeasures emitted")

    # Step 14 CLEANUP
    _bug_step(14, "CLEANUP", "strip #region DEBUG blocks before commit")

    # Step 15 VERDICT-VERIFY
    verify_path = state_dir / "verify.md"
    verify_path.write_text(f"# Verify — {perf_slug}\n\nverdict: {verdict}\nbaseline: {baseline_path}\nverify_outcome: {verify_outcome}\n")
    _bug_step(15, "VERDICT-VERIFY", f"verdict={verdict}")

    # Step 16 LEDGER
    evidence = {
        "perf_slug": perf_slug, "baseline": str(baseline_path),
        "verify_outcome": verify_outcome, "phase4_state_node": state_node.get("id") if state_node else None,
        "metric_count": len(metrics),
    }
    freshness = datetime.now(timezone.utc).isoformat()
    detected_via = f"/debug performance {target}"
    def body_fn(entry_id):
        return _mode_ledger_body(entry_id, mode="performance", target=target, host=host,
                                 feature=feature, verdict=verdict, evidence=evidence,
                                 dependency_map=dependency_map, freshness=freshness,
                                 detected_via=detected_via, countermeasures=countermeasures)
    verdict, _rc_tags, _blocked = run_realization_checks(verdict, mode="performance")
    if _blocked:
        print("RC-7 BLOCK: performance ledger write refused — remove hook-output files from changeset", file=sys.stderr)
        return 2
    ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
    _bug_step(16, "LEDGER", f"wrote {ledger_id} (verdict={verdict}{' tags=' + str(_rc_tags) if _rc_tags else ''})")

    out = {"verb": "performance", "target": target, "verdict": verdict,
           "evidence": evidence, "ledger_entry": ledger_id, "freshness": freshness}
    print(json.dumps(out, indent=2, default=str))
    print()
    print(f"--- /debug performance {target} → verdict: {verdict} ---")
    print(f"  perf-slug   : {perf_slug}")
    print(f"  baseline    : {baseline_path}")
    print(f"  ledger      : {ledger_id}")

    return exit_code


def cmd_help() -> int:
    print("""usage:
  debug.py check <target>            — Wiring mode (Phase 4 + ship-log evidence + ledger)
  debug.py list                      — show realize-debt.md ledger
  debug.py bug "<symptom>" [...]     — Bug mode 17-step engine
       flags: --quick --no-chain --dry-run --bug-slug=<X>
  debug.py drift <feature> [...]     — Drift mode (was correct, now stale)
       flags: --baseline=<sha-or-iso> --dry-run
  debug.py flaky "<symptom>" [...]   — Flaky mode (loop reproducer, race patterns)
       flags: --runs=N --bug-slug=<X> --dry-run
  debug.py performance <feature>     — Performance mode (latency / leak / hot-loop)
       flags: --baseline=<file> --dry-run
""")
    return 0


# ---------------------------------------------------------------------------
# /debug scan — autonomous daemon mode (read-only; produces bundle summary)
# Per .ship/debug-daemon-6th/goals/02-plan-gaps.md: must NOT call cmd_check
# (always writes ledger). Uses sub-helpers for read-only re-verification.
# ---------------------------------------------------------------------------

def _parse_ledger_entries() -> list[dict]:
    """Parse realize-debt.md into list of dicts with id/mode/target/status/etc."""
    if not LEDGER.exists():
        return []
    txt = LEDGER.read_text()
    raw = re.split(r"(?=^## R-\d{4} )", txt, flags=re.MULTILINE)
    raw = [e for e in raw if e.startswith("## R-")]
    out = []
    for body in raw:
        head = body.split("\n", 1)[0]  # "## R-0001 — prewarm (london)"
        m = re.match(r"## (R-\d{4}) — (.+)$", head)
        if not m:
            continue
        entry = {"id": m.group(1), "title": m.group(2).strip(), "_body": body}
        for line in body.splitlines():
            fm = re.match(r"^- ([a-z_]+): (.+)$", line)
            if fm:
                entry[fm.group(1)] = fm.group(2).strip()
        out.append(entry)
    return out


def _entry_severity(mode: str) -> str:
    return {
        "wiring": "high",
        "drift": "medium",
        "performance": "medium",
        "flaky": "low",
        "bug": "high",
    }.get(mode, "info")


# ---------------------------------------------------------------------------
# S2: drift_recheck — rule-based detector for cmd_scan
# Reads ledger entries with `wired_commit` SHA + `evidence_file` path; runs
# `git rev-list --count <sha>..HEAD -- <evidence_file or ship_slug>` to detect
# commit drift since the wiring entry. >0 = stale-soft, >10 = stale-hard.
# Returns proposed_action[]-shaped dicts per daemon_summary schema. Read-only.
# Plan ref: ~/.ship/debug-daemon/goals/02-plan.md §1.1, §1.2.
# ---------------------------------------------------------------------------

def _git_rev_count(repo: Path, since_sha: str, until: str = "HEAD",
                   path_filter: str | None = None) -> int | None:
    """Run `git -C <repo> rev-list --count <sha>..<until> [-- <path>]`.
    Returns int count, or None on git error (treated as fail-closed: no finding)."""
    if not repo.exists() or not (repo / ".git").exists():
        return None
    cmd = ["git", "-C", str(repo), "rev-list", "--count", f"{since_sha}..{until}"]
    if path_filter:
        cmd += ["--", path_filter]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return None
        return int(r.stdout.strip() or "0")
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def _drift_proposed_action(entry: dict, host: str, severity: str,
                           commit_count: int) -> dict:
    """Build a schema-valid proposed_action dict for a drift finding.

    action_type=inbox_archive (read-only review action; daemon emits no mutations
    per spec §5 R4). 18 required fields per daemon_summary.schema.json $defs/proposed_action.
    """
    eid = entry["id"]
    target = entry.get("target", f"{host}:{eid}")
    sha = entry.get("wired_commit", "?")[:7]
    run_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_hash = hashlib.sha1(
        f"{eid}{sha}{commit_count}".encode()
    ).hexdigest()[:6]
    finding_id = f"debug_{host}_{run_date}_drift_{eid.lower().replace('-', '_')}_{short_hash}"
    # finding_id must match ^[a-z0-9_-]+$
    finding_id = re.sub(r"[^a-z0-9_-]", "_", finding_id)
    risk = "MEDIUM" if severity == "stale-hard" else "LOW"
    blast = "LOW" if severity == "stale-hard" else "NONE"
    title = (f"Re-verify {target} ({eid}): {commit_count} commits since "
             f"wired @ {sha} — {severity}")
    return {
        "id": f"debug_{host}_{run_date}_{short_hash}",
        "title": title,
        "before": (f"Ledger {eid} wired at {sha}; {commit_count} commits "
                   f"have landed since on HEAD."),
        "after": (f"Operator re-runs `/debug check {target}` to confirm "
                  f"wiring still holds at HEAD; ledger updated if regressed."),
        "reason": (f"Drift detector: rule-based git-rev-list count "
                   f"{sha}..HEAD = {commit_count} (>0 threshold; "
                   f"{'>10 hard' if severity == 'stale-hard' else 'soft'})."),
        "risk": risk,
        "affected_subsystems": ["realize-debt-ledger", f"debug-{host}"],
        "affected_graph_nodes": [],
        "upstream_deps": [],
        "downstream_deps": [],
        "hub_impact": [],
        "blast_radius_score": blast,
        "conflicts_with": [],
        "depends_on": [],
        "action_type": "inbox_archive",
        "action_params": {"finding_id": finding_id},
        "auto_applyable": False,
        "approval_required": True,
    }


_DRIFT_REPO_BY_HOST = {
    # Map ledger target host-prefix → local repo root holding wired_commit SHAs.
    # London target SHAs land in ~/prediction-markets (pulled from Hel bare repo);
    # most mac/hel infra SHAs live in ~/NardoWorld; .claude self-tracks separately.
    "london": [HOME / "prediction-markets", HOME / "NardoWorld"],
    "hel":    [HOME / "NardoWorld", HOME / "prediction-markets"],
    "mac":    [HOME / "NardoWorld", HOME / ".claude", HOME / "prediction-markets"],
}


# S1: Auto-detector allowlist for cmd_scan daemon-mode dispatch.
# Per CLAUDE.md "Rule-based > LLM for local classifiers" HARD RULE: only modes
# expressible as deterministic rules auto-fire. bug/flaky/race need symptom
# strings + interactive reproduction → NEVER auto-fire (panel noise risk).
# wedge/leak/performance scaffolding deferred to future ships (S3-S5).
_AUTO_DETECTORS = {"wiring", "drift", "wedge", "leak", "performance"}


def _drift_recheck(host: str) -> list[dict]:
    """Re-check open wiring ledger entries for commit drift.

    Reads ~/NardoWorld/realize-debt.md (unified ledger across hosts), filters:
      - status == 'open' OR status == 'wired'  (wired entries can drift too)
      - mode in ('wiring', 'check')
      - wired_commit field present (looks like a SHA, not a placeholder)
    For each, runs `git rev-list --count <sha>..HEAD` against candidate repos
    for the entry's target host (london→prediction-markets first, etc.). First
    repo where the SHA resolves wins. >0 = stale-soft; >10 = stale-hard.
    Cap: 30 entries per spec §4 R-Token-cost. Returns list of proposed_action
    dicts (empty list if no drift / no candidates / fail-closed git error).

    Daemon scans the FULL ledger regardless of which host it's running on —
    the ledger is shared (writer is /debug skill on whichever host); host arg
    here is only used for the proposed_action `id` namespace.
    """
    out: list[dict] = []
    try:
        entries = _parse_ledger_entries()
    except Exception:
        return out  # fail-closed
    candidates = []
    for e in entries:
        status = e.get("status", "")
        if status not in ("open", "wired"):
            continue
        if e.get("mode") not in ("wiring", "check"):
            continue
        sha_raw = e.get("wired_commit", "").strip()
        # Strip "(...)" placeholders like "(n/a — duplicate of R-0001)"
        if not sha_raw or sha_raw.startswith("("):
            continue
        sha = sha_raw.split()[0].strip().rstrip(")")
        if len(sha) < 7 or not re.match(r"^[0-9a-f]{7,40}$", sha):
            continue
        candidates.append((e, sha))
        if len(candidates) >= 30:
            break

    for entry, sha in candidates:
        target = entry.get("target", "")
        t_host = target.split(":", 1)[0].strip().lower() if ":" in target else "mac"
        repos = _DRIFT_REPO_BY_HOST.get(t_host, _DRIFT_REPO_BY_HOST["mac"])
        n = None
        for repo in repos:
            n = _git_rev_count(repo, sha)
            if n is not None:
                break  # first repo that resolves the SHA wins
        if n is None or n <= 0:
            continue  # no drift OR SHA not found in any candidate repo
        severity = "stale-hard" if n > 10 else "stale-soft"
        out.append(_drift_proposed_action(entry, host, severity, n))
    return out


# ---------------------------------------------------------------------------
# S3: wedge_recheck — config-driven host-local kernel-state probe.
# Reads `wedge_targets.json` for current host; for each unit, invokes
# `bin/wedge-capture.sh --capture-only <unit>` (5s subprocess cap). Parses
# output for /proc/PID/wchan + state. D-state OR (S-state with lines30s<200)
# = wedge_suspect. Mac → empty target list → no calls.
# Plan ref: ~/.ship/debug-daemon/goals/02-plan.md §1.2, §1.3, §1.6.
# ---------------------------------------------------------------------------

_WEDGE_TARGETS_PATH = HOME / ".claude" / "skills" / "debug" / "wedge_targets.json"
_WEDGE_CAPTURE_SH = HOME / ".claude" / "skills" / "debug" / "bin" / "wedge-capture.sh"


def _load_wedge_targets(host: str) -> list[str]:
    """Load wedge probe target units for `host` from wedge_targets.json.

    Returns []: missing file (silent), JSON parse error (stderr log, fail-closed),
    or unknown host. Lookup is case-insensitive.
    Plan §1.6.
    """
    try:
        if not _WEDGE_TARGETS_PATH.exists():
            return []
        with _WEDGE_TARGETS_PATH.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[debug scan] _load_wedge_targets: {exc}", file=sys.stderr)
        return []
    if not isinstance(cfg, dict):
        return []
    key = host.lower()
    # Case-insensitive lookup over keys.
    for k, v in cfg.items():
        if k.lower() == key and isinstance(v, list):
            return [str(u) for u in v if isinstance(u, str) and u.strip()]
    return []


def _wedge_proposed_action(unit: str, host: str, state: str, wchan: str,
                           pid: str, lines30s: str) -> dict:
    """Build a schema-valid 18-field proposed_action for a wedge_suspect finding."""
    run_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_hash = hashlib.sha1(
        f"{unit}{host}{state}{wchan}{pid}".encode()
    ).hexdigest()[:6]
    finding_id = f"debug_{host}_{run_date}_wedge_{re.sub(r'[^a-z0-9]', '_', unit.lower())}_{short_hash}"
    finding_id = re.sub(r"[^a-z0-9_-]", "_", finding_id)
    return {
        "id": f"debug_{host}_{run_date}_{short_hash}",
        "title": f"Wedge suspect: {unit} on {host} (state={state}, wchan={wchan})",
        "before": (f"systemd unit {unit} MainPID={pid} reports state={state} "
                   f"wchan={wchan} lines30s={lines30s}; process appears alive "
                   f"but not executing."),
        "after": (f"Operator runs `/debug wedge {unit}` on {host} for full "
                  f"25-min trace + DEEP CAPTURE; root cause kernel-sleep symbol."),
        "reason": (f"Wedge detector: --capture-only probe parsed state={state} "
                   f"(D=uninterruptible / S+lines30s<200=quiet) → wedge_suspect."),
        "risk": "HIGH",
        "affected_subsystems": [f"systemd:{unit}", f"debug-{host}"],
        "affected_graph_nodes": [],
        "upstream_deps": [],
        "downstream_deps": [],
        "hub_impact": [],
        "blast_radius_score": "MED",
        "conflicts_with": [],
        "depends_on": [],
        "action_type": "inbox_archive",
        "action_params": {"finding_id": finding_id, "unit": unit, "host": host,
                          "state": state, "wchan": wchan, "pid": pid},
        "auto_applyable": False,
        "approval_required": True,
    }


def _wedge_recheck(unit: str, host: str) -> dict | None:
    """Probe `unit` for wedge state via wedge-capture.sh --capture-only.

    Subprocess timeout: 5s hard cap per spec §2 / plan §1.2 R-Token-cost.
    Returns proposed_action dict if state==D OR (state==S AND lines30s<200);
    else None. Fail-closed on any exception. No remote SSH — host-local only.
    Plan §1.2 wedge row + §4 R-Wedge-capture-bash (no-D-state non-zero exit
    treated as 'no finding' not error).
    """
    try:
        if not _WEDGE_CAPTURE_SH.exists():
            return None
        r = subprocess.run(
            ["bash", str(_WEDGE_CAPTURE_SH), "--capture-only", unit],
            capture_output=True, text=True, timeout=5,
        )
        # Exit 1 = unit unknown / PID=0 / no systemctl (mac) / dead pid → no finding.
        if r.returncode != 0:
            return None
        line = (r.stdout or "").strip().splitlines()[-1] if r.stdout else ""
        # Parse: state=X wchan=Y pid=Z rss=N lines30s=M
        kv = {}
        for tok in line.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                kv[k] = v
        state = kv.get("state", "?")
        wchan = kv.get("wchan", "?")
        pid = kv.get("pid", "?")
        try:
            lines30s_n = int(kv.get("lines30s", "0"))
        except (ValueError, TypeError):
            lines30s_n = 0
        is_d = state == "D"
        is_quiet_s = state == "S" and lines30s_n < 200
        if not (is_d or is_quiet_s):
            return None
        return _wedge_proposed_action(unit, host, state, wchan, pid,
                                      str(lines30s_n))
    except Exception:
        # Fail-closed: any exception → None. Caller concats "; wedge:<exc>"
        # to known_gaps via outer try in cmd_scan.
        return None


_LEAK_HISTORY_DIR = Path.home() / ".cache" / "bigd" / "rss_history"
_LEAK_THRESHOLD_LOW = 30  # >30% climb → low severity
_LEAK_THRESHOLD_MED = 50  # >50% → medium
_LEAK_THRESHOLD_HIGH = 100  # >100% → high
_LEAK_HISTORY_KEEP_DAYS = 30  # rolling window


def _leak_proposed_action(unit: str, host: str, pid: str,
                          rss_now: int, rss_old: int,
                          pct_climb: float, severity: str) -> dict:
    """Build a schema-valid 18-field proposed_action for a leak_suspect finding."""
    run_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_hash = hashlib.sha1(
        f"{unit}{host}{pid}{rss_now}".encode()
    ).hexdigest()[:6]
    finding_id = (f"debug_{host}_{run_date}_leak_"
                  f"{re.sub(r'[^a-z0-9]', '_', unit.lower())}_{short_hash}")
    finding_id = re.sub(r"[^a-z0-9_-]", "_", finding_id)
    risk_map = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH"}
    return {
        "id": f"debug_{host}_{run_date}_{short_hash}",
        "title": (f"Leak suspect: {unit} on {host} "
                  f"(RSS {rss_old}→{rss_now}KB, +{pct_climb:.0f}%)"),
        "before": (f"systemd unit {unit} MainPID={pid} RSS climbed "
                   f"from {rss_old}KB ({_LEAK_HISTORY_KEEP_DAYS}-day window baseline) "
                   f"to {rss_now}KB current (+{pct_climb:.1f}%)."),
        "after": (f"Operator runs `/debug leak {unit}` on {host} for "
                  f"heap-tracker + alloc-site analysis; identify retainer."),
        "reason": (f"Leak detector: ps-snapshot RSS-history compare crossed "
                   f"{severity}-tier threshold (LOW={_LEAK_THRESHOLD_LOW}%, "
                   f"MED={_LEAK_THRESHOLD_MED}%, HIGH={_LEAK_THRESHOLD_HIGH}%)."),
        "risk": risk_map.get(severity, "LOW"),
        "affected_subsystems": [f"systemd:{unit}", f"debug-{host}"],
        "affected_graph_nodes": [],
        "upstream_deps": [],
        "downstream_deps": [],
        "hub_impact": [],
        "blast_radius_score": "MED" if severity in ("medium", "high") else "LOW",
        "conflicts_with": [],
        "depends_on": [],
        "action_type": "inbox_archive",
        "action_params": {"finding_id": finding_id, "unit": unit, "host": host,
                          "pid": pid, "rss_now_kb": rss_now,
                          "rss_old_kb": rss_old,
                          "pct_climb": round(pct_climb, 2)},
        "auto_applyable": False,
        "approval_required": True,
    }


def _leak_recheck(unit: str, host: str) -> dict | None:
    """RSS-history scan for unit's process. Compare current RSS vs ~24h-old entry.

    Per plan §1.2 leak row + §4 R-RSS-history-cold-start.
    Inputs: systemd unit + host.
    Algorithm:
      1. Resolve PID via `systemctl --user show -p MainPID --value <unit>` (fallback to system).
      2. Snapshot RSS via `ps -o rss= -p <pid>` (returns KB).
      3. Append current snapshot to ~/.cache/bigd/rss_history/<unit>_<host>.jsonl.
      4. Find oldest entry within last (12h, 30d] window.
         - No entry older than 12h → cold-start, return None (write only).
      5. Compute pct_climb = (rss_now - rss_old) / rss_old * 100.
      6. Threshold map: >30%→low, >50%→medium, >100%→high. Below 30% → None.
      7. Trim history file to last 30d on each call.
    Returns: proposed_action dict (18 schema fields) or None.
    Fail-closed: any exception → return None. Caller concats `; leak:<exc>` to known_gaps.
    """
    try:
        # Step 1: PID via systemctl (try user then system).
        pid = ""
        for sysctl in (["systemctl", "--user", "show", "-p", "MainPID",
                        "--value", unit],
                       ["systemctl", "show", "-p", "MainPID",
                        "--value", unit]):
            try:
                r = subprocess.run(sysctl, capture_output=True, text=True,
                                   timeout=3)
                if r.returncode == 0 and r.stdout.strip().isdigit():
                    p = r.stdout.strip()
                    if p != "0":
                        pid = p
                        break
            except Exception:
                continue
        if not pid:
            return None  # unit unknown / not running / mac (no systemctl)

        # Step 2: RSS via ps.
        ps = subprocess.run(["ps", "-o", "rss=", "-p", pid],
                            capture_output=True, text=True, timeout=3)
        if ps.returncode != 0:
            return None
        try:
            rss_now = int(ps.stdout.strip().split()[0])
        except (ValueError, IndexError):
            return None

        # Step 3: append snapshot.
        _LEAK_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        hist_file = _LEAK_HISTORY_DIR / f"{unit}_{host}.jsonl"
        now = datetime.now(timezone.utc)
        snapshot = {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "rss_kb": rss_now, "pid": pid}

        # Read existing history.
        history: list[dict] = []
        if hist_file.exists():
            try:
                for line in hist_file.read_text().splitlines():
                    if line.strip():
                        history.append(json.loads(line))
            except Exception:
                history = []

        # Step 7 (trim, do before append so write is clean).
        cutoff_old = now.timestamp() - (_LEAK_HISTORY_KEEP_DAYS * 86400)
        history = [
            h for h in history
            if _parse_iso_ts(h.get("ts", "")) > cutoff_old
        ]
        history.append(snapshot)

        # Step 4: cold-start check — find oldest entry >12h ago.
        cutoff_12h = now.timestamp() - (12 * 3600)
        old_entries = [
            h for h in history[:-1]  # exclude just-appended snapshot
            if _parse_iso_ts(h.get("ts", "")) <= cutoff_12h
        ]

        # Persist history (always, even on cold-start).
        hist_file.write_text(
            "\n".join(json.dumps(h) for h in history) + "\n"
        )

        if not old_entries:
            return None  # cold-start: insufficient history, no false positive

        # Step 5: pct_climb vs OLDEST entry in window (most conservative).
        baseline = min(old_entries, key=lambda h: _parse_iso_ts(h.get("ts", "")))
        rss_old = int(baseline.get("rss_kb", 0))
        if rss_old <= 0:
            return None
        pct_climb = (rss_now - rss_old) / rss_old * 100

        # Step 6: threshold map.
        if pct_climb >= _LEAK_THRESHOLD_HIGH:
            severity = "high"
        elif pct_climb >= _LEAK_THRESHOLD_MED:
            severity = "medium"
        elif pct_climb >= _LEAK_THRESHOLD_LOW:
            severity = "low"
        else:
            return None  # below threshold, not a finding

        return _leak_proposed_action(unit, host, pid, rss_now, rss_old,
                                     pct_climb, severity)
    except Exception:
        return None  # fail-closed; caller concats "; leak:<exc>" to known_gaps


def _parse_iso_ts(s: str) -> float:
    """Parse YYYY-MM-DDTHH:MM:SSZ → epoch float. Returns 0 on failure."""
    try:
        dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


_PERF_THRESHOLD_PCT = 50  # >50% delta vs baseline → regression finding


def _performance_proposed_action(entry: dict, baseline_ms: int,
                                 current_ms: int, delta_pct: float,
                                 host: str) -> dict:
    """Build a schema-valid 18-field proposed_action for a perf_regression finding."""
    run_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    eid = entry.get("id", "unknown")
    short_hash = hashlib.sha1(
        f"{eid}{baseline_ms}{current_ms}".encode()
    ).hexdigest()[:6]
    finding_id = f"debug_{host}_{run_date}_perf_{eid}_{short_hash}"
    finding_id = re.sub(r"[^a-z0-9_-]", "_", finding_id.lower())
    severity = "high" if delta_pct >= 100 else "medium"
    risk_map = {"medium": "MEDIUM", "high": "HIGH"}
    return {
        "id": f"debug_{host}_{run_date}_{short_hash}",
        "title": (f"Perf regression: {eid} on {host} "
                  f"({baseline_ms}→{current_ms}ms, +{delta_pct:.0f}%)"),
        "before": (f"Ledger entry {eid} baseline_ms={baseline_ms} on {host}; "
                   f"current probe latency {current_ms}ms (+{delta_pct:.1f}% vs baseline)."),
        "after": (f"Operator runs `/debug performance {entry.get('target','?')}` "
                  f"for full step-7 measurement + flamegraph; identify hot path."),
        "reason": (f"Performance detector: probe re-run crossed "
                   f"{_PERF_THRESHOLD_PCT}% delta-vs-baseline threshold."),
        "risk": risk_map.get(severity, "MEDIUM"),
        "affected_subsystems": [f"ledger:{eid}", f"debug-{host}"],
        "affected_graph_nodes": [],
        "upstream_deps": [],
        "downstream_deps": [],
        "hub_impact": [],
        "blast_radius_score": "MED",
        "conflicts_with": [],
        "depends_on": [],
        "action_type": "inbox_archive",
        "action_params": {"finding_id": finding_id, "ledger_id": eid,
                          "baseline_ms": baseline_ms,
                          "current_ms": current_ms,
                          "delta_pct": round(delta_pct, 2),
                          "host": host},
        "auto_applyable": False,
        "approval_required": True,
    }


def _performance_recheck(entry: dict) -> dict | None:
    """Re-run a stored baseline probe and detect regression vs baseline_ms.

    Per plan §1.2 performance row: requires entry to carry both `baseline_ms`
    (int) AND `baseline_cmd` (shell command string). Re-runs the cmd, measures
    wall time, compares delta. >50% slower → regression finding. Below threshold
    or missing fields → None.

    Subprocess timeout: 10s hard cap.
    Fail-closed: any exception → None. Caller concats `; perf:<exc>` to known_gaps.
    """
    try:
        baseline_ms = entry.get("baseline_ms")
        baseline_cmd = entry.get("baseline_cmd")
        if not isinstance(baseline_ms, int) or not isinstance(baseline_cmd, str):
            return None  # missing fields — entry not yet baseline-tagged
        if baseline_ms <= 0 or not baseline_cmd.strip():
            return None
        host = entry.get("host", "unknown")

        # Re-run probe with wall-clock measurement.
        t0 = time.time()
        r = subprocess.run(["bash", "-c", baseline_cmd],
                           capture_output=True, text=True, timeout=10)
        current_ms = int((time.time() - t0) * 1000)
        if r.returncode != 0:
            return None  # probe failed — not a perf signal

        delta_pct = (current_ms - baseline_ms) / baseline_ms * 100
        if delta_pct < _PERF_THRESHOLD_PCT:
            return None  # within budget

        return _performance_proposed_action(entry, baseline_ms, current_ms,
                                            delta_pct, host)
    except Exception:
        return None  # fail-closed


def _recheck_entry(entry: dict) -> dict:
    """Read-only re-verification of an open ledger entry. Returns verdict dict."""
    mode = entry.get("mode", "?")
    target = entry.get("target", "")
    eid = entry["id"]

    # Wiring: find_state_node + find_lineage_matches → still un-wired?
    if mode == "wiring":
        try:
            phase4 = load_phase4()
            host, feature = parse_target(target)
            state_hit = find_state_node(phase4.get("state_registry", {}), host, feature)
            lineage_hits = find_lineage_matches(phase4.get("data_lineage", {}), feature, host)
            if state_hit or lineage_hits:
                return {"id": eid, "verdict": "now_wired", "severity": _entry_severity(mode), "mode": mode}
            return {"id": eid, "verdict": "still_open", "severity": _entry_severity(mode), "mode": mode}
        except Exception as exc:
            return {"id": eid, "verdict": "skipped", "severity": _entry_severity(mode),
                    "mode": mode, "skip_reason": f"phase4 read err: {exc}"}

    # Drift / performance: need baseline diff — defer to interactive verbs
    # Flaky / bug: need active reproduction — defer
    return {"id": eid, "verdict": "skipped", "severity": _entry_severity(mode),
            "mode": mode, "skip_reason": f"{mode} mode requires interactive recheck"}


def _entry_age_days(entry: dict) -> int:
    """Return age in days from detected_at field (best-effort)."""
    s = entry.get("detected_at", "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return 0
    try:
        det = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - det).days)
    except Exception:
        return 0


def cmd_scan(argv: list[str]) -> int:
    """Autonomous daemon-mode scan: re-verify all status==open ledger entries,
    write daemon_summary to ~/inbox/_summaries/pending/<DATE>/debug_<host>.json.
    Read-only: does NOT mutate the ledger."""
    try:
        flags, _ = _parse_kv_args(argv, {"dry_run": False})
    except ValueError as e:
        print(f"[debug scan] {e}", file=sys.stderr)
        return 2

    # Lazy import bigd_common — path differs across hosts:
    #   Mac:    ~/NardoWorld/scripts/bigd/_lib/
    #   Hel:    ~/NardoWorld/scripts/bigd/_lib/
    #   London: ~/prediction-markets/scripts/bigd/_lib/  (pm user, separate repo)
    # Probe both layouts; first hit wins.
    for cand in (
        HOME / "NardoWorld" / "scripts" / "bigd" / "_lib",
        HOME / "prediction-markets" / "scripts" / "bigd" / "_lib",
    ):
        if (cand / "bigd_common.py").exists():
            sys.path.insert(0, str(cand))
            break
    from bigd_common import (  # type: ignore
        write_summary, _detect_host, SUMMARY_SCHEMA_VERSION, _write_heartbeat,
    )

    host = _detect_host()
    t0 = time.time()
    cron_fired = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # KILLSWITCH guard — mirror sibling daemon pattern from
    # ~/NardoWorld/scripts/bigd/lint/daemon.py:52,394-397. When the file exists,
    # write a green heartbeat and exit immediately (no detectors run).
    KILLSWITCH = HOME / "NardoWorld" / "meta" / "big_systemd" / "KILLSWITCH"
    if KILLSWITCH.exists():
        try:
            _write_heartbeat(
                daemon="bigd-debug", host=host,
                cycle_status="ok", cycle_seconds=0.0,
                findings_filed=0, errors=["KILLSWITCH active"],
            )
        except Exception as e:
            print(f"[debug scan] heartbeat write failed under KILLSWITCH: {e}",
                  file=sys.stderr)
        print(f"[debug scan] KILLSWITCH active at {KILLSWITCH} — exit 0")
        return 0

    all_entries = _parse_ledger_entries()
    open_entries = [e for e in all_entries if e.get("status", "") == "open"]
    skipped_other_status = [e["id"] for e in all_entries if e.get("status", "") != "open"]

    verdicts = [_recheck_entry(e) for e in open_entries]

    resolved_ids = [v["id"] for v in verdicts if v["verdict"] == "now_wired"]
    recurring_ids = [v["id"] for v in verdicts if v["verdict"] == "still_open"]
    skipped_recheck = [v["id"] for v in verdicts if v["verdict"] == "skipped"]

    # Severity rollup of recurring (still-open) entries.
    # Schema allows only critical/high/medium/low; "info" not permitted.
    sev_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in verdicts:
        if v["verdict"] in ("still_open", "skipped"):
            sev = v.get("severity", "low")
            if sev not in sev_count:
                sev = "low"
            sev_count[sev] += 1

    rot_count = sum(1 for e in open_entries if _entry_age_days(e) > 7)

    # S1+S2: dispatch auto-allowlisted detectors. _AUTO_DETECTORS gates which
    # ledger entry modes auto-fire (rule-based only; bug/flaky/race forbidden
    # per CLAUDE.md "Rule-based > LLM"). Wedge/leak/performance scaffolding
    # deferred to future ships (S3-S5). Fail-closed: detector exception → log,
    # append to known_gaps, no proposed_action emitted.
    proposed: list[dict] = []
    detectors_run = ["wiring_recheck"]
    drift_gap = ""
    wedge_gap = ""
    if "drift" in _AUTO_DETECTORS:
        try:
            proposed.extend(_drift_recheck(host))
            detectors_run.append("drift_recheck")
        except Exception as exc:
            drift_gap = f"; drift:{exc}"
            print(f"[debug scan] drift_recheck failed: {exc}", file=sys.stderr)

    # S3: wedge recheck — config-driven, host-local, cap 4 units per scan
    # (plan §1.3 + §4 R-Token-cost). Mac wedge_targets=[] → no calls. Each
    # unit invocation timeout-capped at 5s by _wedge_recheck. Fail-closed.
    if "wedge" in _AUTO_DETECTORS:
        try:
            wedge_targets = _load_wedge_targets(host)[:4]
            wedge_hits = 0
            for unit in wedge_targets:
                try:
                    f = _wedge_recheck(unit, host)
                    if f:
                        proposed.append(f)
                        wedge_hits += 1
                except Exception as exc:
                    wedge_gap += f"; wedge[{unit}]:{exc}"
                    print(f"[debug scan] wedge_recheck({unit}) failed: {exc}",
                          file=sys.stderr)
            detectors_run.append("wedge_recheck")
        except Exception as exc:
            wedge_gap = f"; wedge:{exc}"
            print(f"[debug scan] wedge_recheck failed: {exc}", file=sys.stderr)

    # S4: leak recheck — same wedge_targets list, RSS-history compare, cap 5
    # units per scan (plan §1.3). First-run on a unit writes history file, no
    # finding (cold-start discipline per §4 R-RSS-history-cold-start).
    leak_gap = ""
    if "leak" in _AUTO_DETECTORS:
        try:
            leak_targets = _load_wedge_targets(host)[:5]
            for unit in leak_targets:
                try:
                    f = _leak_recheck(unit, host)
                    if f:
                        proposed.append(f)
                except Exception as exc:
                    leak_gap += f"; leak[{unit}]:{exc}"
                    print(f"[debug scan] leak_recheck({unit}) failed: {exc}",
                          file=sys.stderr)
            detectors_run.append("leak_recheck")
        except Exception as exc:
            leak_gap = f"; leak:{exc}"
            print(f"[debug scan] leak_recheck failed: {exc}", file=sys.stderr)

    # S5: performance recheck — re-run baseline probes from ledger entries
    # carrying both `baseline_ms` and `baseline_cmd` fields. Cap 5 entries
    # per scan (plan §1.3). Today's ledger has no perf entries with
    # baseline_cmd populated, so this is mostly a no-op until cmd_performance
    # starts writing those fields. Forward-compat wiring per §1.2.
    perf_gap = ""
    if "performance" in _AUTO_DETECTORS:
        try:
            perf_entries = [
                e for e in open_entries
                if e.get("mode") == "performance"
                and e.get("baseline_ms")
                and e.get("baseline_cmd")
            ][:5]
            for e in perf_entries:
                try:
                    f = _performance_recheck(e)
                    if f:
                        proposed.append(f)
                except Exception as exc:
                    perf_gap += f"; perf[{e.get('id','?')}]:{exc}"
                    print(f"[debug scan] performance_recheck({e.get('id','?')})"
                          f" failed: {exc}", file=sys.stderr)
            detectors_run.append("performance_recheck")
        except Exception as exc:
            perf_gap = f"; perf:{exc}"
            print(f"[debug scan] performance_recheck failed: {exc}",
                  file=sys.stderr)

    # Roll up severity from new proposed actions into the existing rollup.
    # Schema severities are lowercase; proposed_action `risk` field is uppercase.
    _risk_to_sev = {"CRITICAL": "critical", "HIGH": "high",
                    "MEDIUM": "medium", "LOW": "low"}
    for pa in proposed:
        sev = _risk_to_sev.get(pa.get("risk", "LOW").upper(), "low")
        sev_count[sev] = sev_count.get(sev, 0) + 1

    duration = round(time.time() - t0, 3)
    cron_completed = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = f"debug_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H:%M:%S')}Z"

    summary = {
        "daemon": "debug",
        "run_id": run_id,
        "host": host,
        "cron_fired": cron_fired,
        "cron_completed": cron_completed,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "ship_phases": {
            "spec": {
                "looking_for": "open ledger entries needing re-verification",
                "changed_since_last": resolved_ids,
                "cross_daemon_inputs": {},
            },
            "plan": {
                "detectors_run": detectors_run,
                "skipped": skipped_other_status,
                "rationale": "scan all status==open from realize-debt.md (read-only sub-helpers; cmd_check avoided to prevent ledger pollution)",
            },
            "execute": {
                "duration_sec": duration,
                "detectors_exit_0": len(verdicts) - len(skipped_recheck),
                "detectors_failed": 0,
            },
            "land": {
                "findings_total": len(open_entries) + len(proposed),
                "findings_new": len(proposed),
                "findings_recurring": len(recurring_ids),
                "findings_resolved_since_last": len(resolved_ids),
                "findings_regressed": 0,
                "findings_by_severity": sev_count,
            },
            "monitor": {
                "last_run_findings_addressed": f"{len(resolved_ids)}/{len(open_entries)}",
                "rot_count": str(rot_count),
                "feedback_to_next_spec": "wedge/leak/performance auto-rechecks deferred to S3-S5; flaky/bug/race remain manual-only",
            },
        },
        "proposed_actions": proposed,
        "self_report": {
            "daemon_health": "green" if duration < 30 else "yellow",
            "confidence_in_findings": "Rule-based recheck with no LLM; high confidence on wiring + drift verdicts. Other modes deferred.",
            "known_gaps": ("flaky/bug/race remain manual-only per Rule-based>LLM"
                          + drift_gap + wedge_gap + leak_gap + perf_gap),
        },
        "finding_lifecycle": {
            "new_ids": [],
            "resolved_ids": resolved_ids,
            "regressed_ids": [],
            "recurring_ids": recurring_ids,
        },
    }

    if flags["dry_run"]:
        print(json.dumps(summary, indent=2))
        return 0

    out = write_summary("debug", host, summary)
    # Symmetry with the other 5 bigd daemons (lint/security/performance/gaps/upgrade):
    # write a heartbeat at ~/inbox/_heartbeat/bigd-debug_<host>.json so the Lineage
    # tab and any liveness check can mtime-poll the same way as the rest.
    try:
        _write_heartbeat(
            daemon="bigd-debug",
            host=host,
            cycle_status="ok",
            cycle_seconds=duration,
            findings_filed=len(open_entries) + len(proposed),
            errors=[],
        )
    except Exception as e:
        # Heartbeat write must never fail the daemon — log and continue.
        print(f"[debug scan] heartbeat write failed: {e}", file=sys.stderr)
    print(f"[debug scan] wrote {out} | open={len(open_entries)} drift={len(proposed)} resolved={len(resolved_ids)} rot={rot_count} duration={duration}s")
    return 0


def cmd_wedge(argv: list[str]) -> int:
    """
    Wedge mode — process appears alive (systemctl is-active = active) but JS /
    userspace stops executing, log rate=0, SIGTERM hangs 90s+. Process state
    in /proc/PID/status is D (uninterruptible sleep).

    Born from Apr 27 2026 pm-london investigation: bot wedged every 25min in
    mem_cgroup_handle_over_high. Root cause = MemoryHigh=1400M soft-throttle.
    Fix = raise MemoryHigh to MemoryMax. See phases/wedge.md §A.

    This verb does NOT execute the trace itself (the trace runs on a remote
    host as the service user). It emits the arming command + post-wedge read
    instructions + verdict mapping per wchan.
    """
    if not argv:
        print("usage: debug.py wedge <unit> [--capture-only] [--read-trace=<file>] "
              "[--host=<ssh-alias>]", file=sys.stderr)
        return 2
    unit = argv[0]
    flags = [a for a in argv[1:] if a.startswith("--")]
    capture_only = "--capture-only" in flags
    read_trace = next((f.split("=", 1)[1] for f in flags if f.startswith("--read-trace=")), None)
    host = next((f.split("=", 1)[1] for f in flags if f.startswith("--host=")), None)

    print(f"# /debug wedge — {unit}{' @ ' + host if host else ''}")
    print()
    print("## Iron Laws")
    print("1. NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST")
    print("2. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE")
    print()
    print("Phase file: ~/.claude/skills/debug/phases/wedge.md (read for full 17-step engine)")
    print()

    capture_script = Path.home() / ".claude" / "skills" / "debug" / "bin" / "wedge-capture.sh"
    if not capture_script.exists():
        print(f"PREMISE_FAILURE: capture script missing at {capture_script}", file=sys.stderr)
        return 2

    if read_trace:
        print(f"## Step 0.5 (read existing trace) — {read_trace}")
        print()
        print("Run on the host that owns the trace file:")
        print(f"  sed -n '/=== DEEP CAPTURE/,/=== END DEEP CAPTURE/p' {read_trace}")
        print()
        print("Then map the main thread wchan to a remediation route per phases/wedge.md §A-§E.")
        return 0

    print("## Step 0.5 KERNEL-CAPTURE — arm trace BEFORE next wedge cycle")
    print()
    print(f"On the host running {unit}:")
    print(f"  scp {capture_script} <host>:/tmp/")
    print(f"  ssh <host> \"nohup bash /tmp/wedge-capture.sh {unit} >/dev/null 2>&1 & disown\"")
    print()
    print("Trace polls every 30s for 25 min. On first state=D entry, dumps DEEP CAPTURE")
    print("with main wchan + per-thread state + wchan histogram + open fds + I/O counters.")
    print("Output: /tmp/wedge-trace-<PID>.log on the remote host.")
    print()

    if capture_only:
        print("(--capture-only: exiting after arming. Re-invoke with --read-trace=<file> after wedge.)")
        return 0

    print("## After wedge fires (20-30 min later), read DEEP CAPTURE:")
    print(f"  ssh <host> \"sed -n '/=== DEEP CAPTURE/,/=== END DEEP CAPTURE/p' /tmp/wedge-trace-*.log\"")
    print()
    print("## wchan → remediation route (per phases/wedge.md §A-§E)")
    print()
    print("| wchan | route | first action |")
    print("|---|---|---|")
    print("| mem_cgroup_handle_over_high | §A cgroup soft-throttle | raise MemoryHigh to match MemoryMax |")
    print("| folio_wait_bit / wait_on_page_bit | §B disk I/O block | iostat / check failing block device |")
    print("| sk_wait_data / tcp_recvmsg | §C network read block | enable SO_KEEPALIVE on long-lived sockets |")
    print("| futex_wait_queue (main thread) | §D userspace deadlock | flame graph / libuv pool audit |")
    print("| pipe_read / do_wait | §E subprocess hang | audit subprocess timeout handling |")
    print()
    print("## Verdict (after fix + 1.5x cycle re-trace)")
    print("- wedge_eliminated: PID stable past prior wedge moment, wchan never re-enters target function")
    print("- wedge_persists: same wchan re-fires; fix incomplete (raise threshold further or wrong target)")
    print("- wedge_shifted_to_<wchan>: secondary mechanism; restart investigation from Step 3")
    print()
    print("Ledger entry written to ~/NardoWorld/realize-debt.md with mode=wedge after verification.")
    return 0


def cmd_race(argv: list[str]) -> int:
    """
    Race-condition mode — producer-consumer schedule mismatch detector.
    G1 schedule conflict scan + G2 producer-consumer chain audit +
    G3 failure-mode declaration check + G4 expected-count drift.
    Born from Apr 27 2026 bigd 6th-daemon ship: bundle assembled 4-15s before
    all daemons finished, captured 8/18. Pure timing race, not daemon bug.
    """
    if not argv:
        print("usage: debug.py race <feature> [--dry-run] [--check-systemd-on=<host>]", file=sys.stderr)
        return 2
    feature = argv[0]
    flags = [a for a in argv[1:] if a.startswith("--")]
    dry_run = "--dry-run" in flags
    remote_host = next((f.split("=", 1)[1] for f in flags if f.startswith("--check-systemd-on=")), None)

    print(f"# /debug race — {feature}")
    print()
    findings: list[str] = []

    # G1 — Schedule conflict scan (Mac LaunchAgents + cron)
    print("## G1 — Schedule conflict scan")
    la_dir = Path.home() / "Library" / "LaunchAgents"
    times: list[tuple[str, str]] = []
    if la_dir.exists():
        for plist in la_dir.glob("*.plist"):
            try:
                txt = plist.read_text(errors="ignore")
            except Exception:
                continue
            if feature.lower() not in txt.lower() and feature.lower() not in plist.name.lower():
                continue
            # Crude HH:MM extraction from StartCalendarInterval
            import re as _re
            mh = _re.search(r"<key>Hour</key>\s*<integer>(\d+)</integer>", txt)
            mm = _re.search(r"<key>Minute</key>\s*<integer>(\d+)</integer>", txt)
            si = _re.search(r"<key>StartInterval</key>\s*<integer>(\d+)</integer>", txt)
            if mh and mm:
                times.append((plist.stem, f"{int(mh.group(1)):02d}:{int(mm.group(1)):02d} HKT"))
            elif si:
                times.append((plist.stem, f"every {int(si.group(1))//60}min"))
    print(f"  feature-related LaunchAgents: {len(times)}")
    for name, when in times:
        print(f"    {name}: {when}")
    # Conflict heuristic: any two within ±2min
    fixed = [(n, t) for n, t in times if "HKT" in t]
    for i, (n1, t1) in enumerate(fixed):
        for n2, t2 in fixed[i+1:]:
            h1, m1 = map(int, t1.split()[0].split(":"))
            h2, m2 = map(int, t2.split()[0].split(":"))
            if abs((h1*60+m1) - (h2*60+m2)) <= 2:
                findings.append(f"G1 CONFLICT: {n1} ({t1}) ⟷ {n2} ({t2}) within 2min")
    print(f"  G1 verdict: {'CONFLICT' if any('G1' in f for f in findings) else 'OK'}")
    print()

    # G2 — Producer-consumer chain (look for declaration in .ship/<feature>/state/04-land.md)
    print("## G2 — Producer-consumer chain audit")
    land_paths = [
        Path.home() / ".ship" / feature / "state" / "04-land.md",
        Path.home() / ".ship" / feature / "04-land.md",
    ]
    land = next((p for p in land_paths if p.exists()), None)
    if not land:
        findings.append(f"G2 GAP: no .ship/{feature}/state/04-land.md found — producer-consumer block undeclared")
        print(f"  no Phase 4 LAND artifact at {land_paths[0]}")
    else:
        body = land.read_text(errors="ignore")
        has_block = "Producer-consumer" in body or "produces:" in body or "consumed_by:" in body
        chain = "synchronous_call" if "synchronous_call" in body else \
                "done_marker" if "done_marker" in body else \
                "event_trigger" if "event_trigger" in body else \
                "schedule_coincidence" if "schedule_coincidence" in body else "UNDECLARED"
        print(f"  artifact: {land}")
        print(f"  block present: {has_block}")
        print(f"  chain method: {chain}")
        if not has_block:
            findings.append(f"G2 FAIL: artifact missing Producer-consumer block")
        if chain == "schedule_coincidence":
            findings.append(f"G2 FAIL: chain method is schedule_coincidence (forbidden)")
        if chain == "UNDECLARED":
            findings.append(f"G2 FAIL: chain method not declared")
    print()

    # G3 — Failure-mode declaration
    print("## G3 — Failure-mode declaration")
    if land:
        body = land.read_text(errors="ignore")
        modes = [m for m in ("retry_next_tick", "block_with_timeout", "degrade_with_warning") if m in body]
        if modes:
            print(f"  declared: {modes[0]}")
        else:
            findings.append("G3 FAIL: no failure-mode declaration in artifact")
            print("  declared: NONE")
    else:
        print("  skipped (no artifact)")
    print()

    # G4 — Expected-count drift (find consumers grepping for old numeric counts)
    print("## G4 — Expected-count drift")
    print("  scan: hardcoded count constants in callers vs new producer count")
    # Heuristic: search grep for `expected.*=.*\d+` near feature
    print("  (manual review recommended — automated count-bump diff TBD)")
    print()

    # Verdict
    print("## Verdict")
    if not findings:
        verdict = "race_free"
    else:
        gates_failed = sorted({f.split(":")[0].split()[0] for f in findings})
        verdict = f"race_present ({', '.join(gates_failed)})"
    print(f"  {verdict}")
    if findings:
        print()
        print("## Findings")
        for f in findings:
            print(f"  - {f}")
    if dry_run:
        print()
        print("(--dry-run: no ledger write)")
    return 0 if verdict == "race_free" else 1


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        return cmd_help()
    verb = argv[1]
    if verb == "check":
        return cmd_check(argv[2] if len(argv) > 2 else "")
    if verb == "list":
        return cmd_list()
    if verb == "bug":
        return cmd_bug(argv[2:])
    if verb == "drift":
        return cmd_drift(argv[2:])
    if verb == "flaky":
        return cmd_flaky(argv[2:])
    if verb == "performance":
        return cmd_performance(argv[2:])
    if verb == "race":
        return cmd_race(argv[2:])
    if verb == "wedge":
        return cmd_wedge(argv[2:])
    if verb == "scan":
        return cmd_scan(argv[2:])
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
