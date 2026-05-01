# Realization Checks — universal Phase 4 LAND additions

Loaded by every `phases/<route>/04-land.md`. These checks run BEFORE the route-specific verdict gate (`/debug check` for bot, skill-invocation for skill, etc).

Iron Law: build passing is the LOWEST bar. Every check below must produce evidence, not just exit 0.

---

## RC-1 — Universal stub-marker scan (T1.3)

For ANY shipped artifact (bot, app, skill, hook, doc, mcp, dashboard-mac), grep the changeset for stub markers. Any hit BLOCKS phase close.

```bash
# In the repo root (or staging dir):
git diff <base>..HEAD --name-only | xargs grep -nE \
    '\[stub\]|TODO[: ]|FIXME[: ]|skeleton|NotImplementedError|raise NotImplemented|# stub|# placeholder|step [0-9]+: <[a-z]+>' 2>/dev/null
```

Block list (any match REFUSES close):
- `[stub]` / `# stub` / `// stub`
- `TODO:` / `FIXME:` (in code, not in docs/comments declaring future work)
- `skeleton` / `placeholder` / `not implemented`
- `raise NotImplementedError` / `pass  # implement later`
- `step N: <name>` placeholder pattern (matches `/upskill` v1's failure mode)

Override: `.ship/<slug>/state/04-stub-override.md` with Bernard ack string. Auto-mode CANNOT approve.

---

## RC-2 — SPEC-drift scan (T2.1)

For ANY artifact with a README, SKILL.md, or SPEC file, run a mini ship-auditor on the changeset:
- Extract claims from the README/SPEC (what the artifact "does")
- Cite each claim against code (file:line)
- BLOCK on `SPEC_DRIFT` verdict (claim has no implementation), `RISK` (claim contradicts code)
- WARN on `MISSING_CITATION` (cannot find evidence either way)

Mini ship-auditor brief:
```
Read <artifact>/README.md (or SKILL.md). Extract numbered claims.
For each claim, cite file:line that implements it. If absent → SPEC_DRIFT.
If implementation contradicts → RISK. Otherwise → OK.
Return verdict (PASS / NEEDS_FIX / REWORK) + top-3 risks.
```

Cheaper than full ship-auditor: only scans files in `<base>..HEAD` diff + the README/SPEC, not the whole repo.

---

## RC-3 — Idempotency check (T2.2)

For changes that touch installer scripts (`install.sh`, `setup.sh`, `*.plist` template, `package.json` scripts.install):

```bash
SANDBOX1=$(mktemp -d) && SANDBOX2=$(mktemp -d)
HOME=$SANDBOX1 bash install.sh > /dev/null 2>&1
HOME=$SANDBOX1 bash install.sh > /dev/null 2>&1   # 2nd run
diff -r $SANDBOX1 $SANDBOX2  # any diff = idempotency violation
```

BLOCK on:
- 2nd run produces different file content than 1st
- 2nd run duplicates settings.json entries
- 2nd run errors out (assumes clean state)

---

## RC-4 — Sync-hook allowlist audit (T2.3)

If the changeset adds or modifies any auto-commit / auto-sync / publish-pipeline script:

```bash
git diff <base>..HEAD -- '*sync*' '*commit*' '*publish*' | grep -nE 'git add -A|git add \.|git add \-\-all'
```

BLOCK if any sync hook uses `git add -A`. Required pattern:
- Allowlist: `git add <each-file-explicitly>`
- Blocklist guard: scan staged diff for hook-output state files (`.router_log.jsonl`, `.cache/`, etc.) before commit
- Reference implementation: `~/telegram-claude-bot/scripts/sync_public_repos.py` Step 4 (post-2026-04-27 fix)

Source: 2026-04-27 leak forensics — `git add -A` bypassed the cfg["files"] allowlist and pushed `.router_log.jsonl` (13.6MB session log) + `claude-mcp-proxy/` (private repo mirror) to public repos.

---

## RC-5 — Cross-host smoke (T2.4)

If the changeset names ≥2 hosts (Mac/Hel/London) in code or config, smoke each host's surface:

```bash
# For each declared host:
ssh <host> "<smoke command>"   # e.g. systemctl is-active <unit>
```

BLOCK if any host's smoke fails. Required for PM-bot changes (Hel + London), bigd changes (3-host), shared-state changes (Mac + Hel via bare repo).

---

## RC-6 — Cross-repo cross-link audit (T2.5)

If the changeset is in a public repo with a README, scan the README for `github.com/<user>/<repo>` links and verify each target is PUBLIC at close time:

```bash
links=$(grep -oE 'github\.com/[^/]+/[^/) ]+' README.md | sort -u)
for link in $links; do
    repo=${link#github.com/}
    vis=$(gh repo view "$repo" --json visibility --jq '.visibility' 2>/dev/null)
    [ "$vis" = "PRIVATE" ] && echo "BROKEN: README links to private $repo"
done
```

BLOCK on any private-target match. Caught manually 2026-04-27 in `memory-wiki-graph-stack` (linked to private `claude-skills`).

---

## RC-7 — Hook-output blocklist (cross-cuts RC-1 + RC-3)

For ANY changeset, scan the working tree for hook-output state files that should never be committed:

```
.router_log.jsonl | *.router_log.jsonl | **/router_log*.jsonl
.cache | .cache/ | *.cache
.session.json | .session/ | *.session.*
hook_state* | .hook_state.*
auto_*.log | auto_*.state
```

BLOCK if any of these are tracked (i.e. `git ls-files | grep <pattern>` returns matches). Source: 2026-04-27 simply-quality-gate leak.

---

## RC-8 — Cross-skill dependency check (T3.4 — stub for now)

When shipping a skill that depends on another skill's output schema, declare the dependency in `~/.claude/skills/<name>/SKILL.md` frontmatter:

```yaml
depends_on:
  - skill: extractskill
    contract: "writes ~/.claude/skills/<imported>/SKILL.md"
  - skill: github-publish
    contract: "writes .ship/<slug>/01-spec.md"
```

Phase 4 reads `depends_on`, runs `/debug check <each>`. If any returns `not_wired`, BLOCK.

v1: declarative only — no runtime graph. v2 (future): build a graph + propagate breakage.

---

## RC-9 — Comment-vs-code clause audit (T2.6 — added 2026-05-02)

For ANY shipped artifact whose changeset adds multi-clause comment blocks (e.g. "if X AND Y, then Z"), grep the same diff for matching boolean operators on the named conditions. Mismatch BLOCKS phase close.

Trigger: `git diff <base>..HEAD` produces hunks where added comment lines contain " AND " / " OR " in clause-joining context AND added code lines lack `&&` / `||` (or `and` / `or` keywords).

Method (cheap, runs in ~1s):
```bash
# Same logic as ~/.claude/hooks/comment_code_audit.py but scoped to changeset.
# Pilot hook is log-only on commit; this is the hard gate at phase close.
python3 ~/.claude/hooks/comment_code_audit.py --diff "<base>..HEAD" --strict
```

Override: `.ship/<slug>/state/04-comment-clause-override.md` citing why the comment is intentionally broader than the code (e.g. "comment describes intent for next slice; this slice ships only the X clause; tracker issue #N").

Why this exists: vps_sync.sh ship 2026-05-01 added P2 comment block with "if ahead>200 AND no successful push in last hour" but code only checked `ahead>200`. /s snapshot read the comment label, claimed "P2 hardened". Detected 2026-05-02. RC-9 catches this shape at phase close.

---

## RC-10 — Enforcement-clause citation audit (T2.7 — added 2026-05-02)

Every Phase 4 LAND verdict bullet using enforcement verbs ("hardened", "wired", "shipped", "gated", "enforced", "blocked", "guarded", "fixed") MUST end with `[file:line-or-range]` pointing at the actual enforcement clause — not the label, the comment block, the rule name, or the function declaration.

Verification (during LAND):
1. For each enforcement-verb bullet in `04-land.md`, extract the cited file:line range
2. Read those lines via Read tool
3. Confirm the cited line(s) contain the keyword/symbol/condition the bullet claims (per CLAUDE.md §Citation precision: ≤5 lines, keyword must be on cited line)
4. If the cite points at a comment that DESCRIBES the rule rather than ENFORCES it → BLOCK with reason "label-vs-code drift: cite must point at enforcement, not description"

Override: only when the enforcement is genuinely declarative (a config value rather than a code branch); state explicitly in the override file.

Why this exists: same incident as RC-9. /s snapshot read "P2 hardened" without verifying which line enforced P2. Citation rule prevents the same drift in /ship's own outputs. Mirrors O1 rule extended to /s skill on 2026-05-02.

---

---

## RC-11 — Discipline Detection (T3.5 — added 2026-05-02)

Runs the structured `detection_runner:` block declared by each discipline cited in the slice's §Discipline Impact `disciplines:` block. BLOCKS phase close on any violation. Implements the auto-grader for the per-slice axis (the bigd daemon-side detector layer is the codebase-wide cousin per `~/.ship/bigd-discipline-detector-mapping/goals/01-spec.md`).

Source: 2026-05-02 ship-discipline-detector-runner slice. Closes the gap between paperwork enforcement (discipline-impact-gate.py) and actual code-level enforcement.

### How it runs

```bash
python3 ~/.claude/scripts/discipline-detector-runner.py \
    --slug <slice-slug> \
    --repo <repo-root> \
    --scope diff \
    [--base <sha>] \
    [--paths <path,path,...>]
```

Behavior:
1. Reads §Discipline Impact `disciplines:` from PLAN §6.3 first, falls back to SPEC §5.3, else emits `trivial_tier_no_grading` (advisory).
2. For each declared D-code:
   - If artifact contains `[skip-detector: D-X reason=<text>]` marker → log to `~/.claude/scripts/state/detector-skips.jsonl`, mark SKIP.
   - Else load `detection_runner:` YAML block from `~/.claude/rules/disciplines/<file>.md`.
   - Missing block → verdict UNRUNNABLE → BLOCK phase close.
   - Execute per `type:` (grep | shell_command | ssh_command | ts_morph stub).
   - Compare violations vs `max_violations:` threshold.
3. Writes `<slice>/state/04-discipline-detection-results.md` (markdown) + JSON to stdout.
4. Exit 0 = all PASS/SKIP, 1 = any FAIL, 2 = any UNRUNNABLE, 3 = arg/parse error.

### Block semantics

Any FAIL or UNRUNNABLE blocks Phase 4 LAND from closing. Phase author must:
- Fix the violation (re-execute Phase 3) and re-run RC-11, OR
- Add `[skip-detector: D-X reason=<rationale>]` to plan/spec for UNRUNNABLE disciplines that lack a `detection_runner:` block (transitional period).

Receipts are appended ONLY for disciplines with verdict PASS in this run. SKIPs are logged to `detector-skips.jsonl` but no D-receipt; they don't count toward ratchet promotion.

### Schema reference

Discipline files house the `detection_runner:` block. See `~/.claude/rules/disciplines/ssot.md` (D1) and `~/.claude/rules/disciplines/lifecycle-pair.md` (D5) for the canonical format. Allowed types: `grep | shell_command | ssh_command | ts_morph`.

`D14` quantitative invariants are OUT OF SCOPE for RC-11 — those are runtime assertions in bot code, not Phase 4 detections.

### Override path

Strict bypass: add `[skip-detector: D-X reason=<text>]` per discipline. Logged to `detector-skips.jsonl`; daemon-side ratchet visibility preserved.

---

## Application order

For each Phase 4 LAND closure:

1. Run RC-1 (stub markers) — fastest, catches most failures
2. Run RC-7 (hook-output) — fastest, catches privacy regressions
3. Run RC-9 (comment-vs-code) — fast, catches label-vs-code drift
4. Run RC-2 (SPEC drift) — moderate cost, catches doc lies
5. Run RC-3 (idempotency) — only if installer-shape change
6. Run RC-4 (sync-hook) — only if sync-script-shape change
7. Run RC-5 (cross-host) — only if multi-host change
8. Run RC-6 (cross-repo links) — only if public-repo README change
9. Run RC-8 (deps) — only if SKILL with declared deps
10. Run RC-10 (enforcement-cite audit) — runs against `04-land.md` itself before close
11. **Run RC-11 (discipline detection) — runs declared `detection_runner:` blocks per slice §Discipline Impact**
12. Then run route-specific check (`/debug check` for bot, skill-invocation for skill, etc.)

ALL must PASS or have an explicit override before phase close.

**RC-11 ordering note:** RC-11 runs BEFORE the discipline-receipts.jsonl append (per ship-discipline-detector-runner REQ-17). Receipts append only for D-codes with verdict PASS in RC-11; FAIL/UNRUNNABLE blocks close + skips receipt-append for those D-codes.
