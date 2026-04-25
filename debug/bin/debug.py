#!/usr/bin/env python3
"""
/debug — deterministic entrypoint.

S1 scope: `check` (Wiring) + `list`.
S3 scope: `bug` (full 17-step engine) + D1 (atomic ledger) + D2 (token-form normalize matcher).

Reads Phase 4 graphs read-only. Writes to ~/NardoWorld/realize-debt.md (lockfile-protected).

Per CLAUDE.md "Rule-based > LLM for local classifiers": no LLM calls. Pure rules + JSON I/O.
Iron Laws (obra/superpowers MIT):
  1. NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
  2. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure _disc.py importable from same dir
sys.path.insert(0, str(Path(__file__).parent))
import _disc  # noqa: E402

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
        ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
        ledger_note = "(new entry)"

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


def _bug_step(n: int, name: str, msg: str) -> None:
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
    ledger_id = _disc.atomic_ledger_append(body_fn, header_if_new=LEDGER_HEADER)
    _bug_step(16, "LEDGER", f"wrote {ledger_id} (status={'inconclusive' if dry else 'open'})")

    print()
    print(f"--- /debug bug \"{symptom}\" → verdict: {verdict} ---")
    print(f"  bug-slug    : {bug_slug}")
    print(f"  state dir   : {state_dir}")
    print(f"  exp dir     : {exp_dir}")
    print(f"  ledger      : {ledger_id}")
    return 0


def cmd_stub(verb: str) -> int:
    print(f"MODE_NOT_YET_SHIPPED — `/debug {verb}` lands in master-debug ship S8.")
    print(f"S1+S3 scope = Wiring + Bug + ledger view. See ~/.ship/master-debug/goals/00-master-plan.md §13.")
    return 3


def cmd_help() -> int:
    print("""usage:
  debug.py check <target>          — Wiring mode (Phase 4 + ship-log evidence + ledger)
  debug.py list                    — show realize-debt.md ledger
  debug.py bug "<symptom>" [...]   — Bug mode 17-step engine
       flags: --quick --no-chain --dry-run --bug-slug=<X>
  debug.py drift|flaky|performance — stubbed for S8
""")
    return 0


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
    if verb in ("drift", "flaky", "performance"):
        return cmd_stub(verb)
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
