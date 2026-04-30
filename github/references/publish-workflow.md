---
name: publish-workflow
description: |
  End-to-end publish workflow: pre-push safety, naming, installer, push with fallback,
  post-push verification. Complements readme-playbook.md (which covers README content only).

  USE FOR:
  - "publish to github", "push to github", "upload repo"
  - Any time a brand-new repo is being created
  - Always run this alongside readme-playbook when scaffolding a new project

allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(gh *)
  - Bash(git *)
  - Bash(grep *)
  - Bash(chmod *)
  - Glob
  - Grep
---

# GitHub Publish Workflow

Covers the publish pipeline the readme-playbook doesn't: safety checks before push,
repo creation with fallbacks, and post-push verification. Run this for every new repo.

---

## Phase 0 — Naming convention check

Before `gh repo create`, verify the name matches the author's convention.

For **nardovibecoding**:
- Claude Code plugins / skills / hooks → prefix `claudecode-*` (e.g. `claudecode-voice`, `claudecode-telegram-bridge`)
- General AI / MCP tools → no prefix (e.g. `nardo-stack`, `eval-loop`)
- **If the user proposes `claude-X` for a Claude Code tool, warn and suggest `claudecode-X`.** We renamed `claude-session-continuity` → `claudecode-session-continuity` for exactly this reason.

Universal rule: grep existing repos for naming patterns before creating.

```bash
gh repo list <user> --limit 50 --json name | python3 -c "import json,sys; [print(r['name']) for r in json.load(sys.stdin)]"
```

---

## Phase 0.5 — Fresh-init guard (MANDATORY)

A public repo must NEVER inherit history from a private workspace. Even one accidental commit with secrets remains forever in `git log`.

```bash
# If we are inside an existing git repo, refuse to publish in place.
if [ -d .git ]; then
  echo "❌ Existing .git history detected. For a public publish:"
  echo "   1. mkdir /tmp/publish-<repo>"
  echo "   2. cp -r <files-to-publish> /tmp/publish-<repo>/"
  echo "   3. cd /tmp/publish-<repo> && git init"
  echo "   4. Run privacy scan + commit + gh repo create from THERE."
  exit 1
fi
```

**The fresh-init pattern** — copy the files you want to publish into a clean dir, `git init` there, commit once, push. Never `gh repo create` from a directory whose `git log` you haven't audited line-by-line.

```bash
# Recommended fresh-init recipe
mkdir -p /tmp/publish-<repo>
cp -r <files-to-include> /tmp/publish-<repo>/
cd /tmp/publish-<repo>
git init
# Run privacy scan (Phase 1.1) HERE before first commit
git add <explicit-paths>           # never `git add -A` (sweeps untracked junk)
git commit -m "Initial commit"
gh repo create <user>/<repo> --public --source=. --push
```

### 0.5.1 History rewrite (only when fresh-init is impossible)

When a long git history must survive — open-source contribution lineage, multi-author credits, time-stamped audit trail — use `git filter-repo` to strip secrets from every commit before push. **Slower, more error-prone, irreversible — default to fresh-init unless the user explicitly asks for history preservation.**

```bash
# Install: pip install git-filter-repo (or brew install git-filter-repo)

# 1. Clone a fresh mirror to operate on (NEVER filter-repo your working tree)
git clone --mirror <local-path> /tmp/publish-<repo>-mirror.git
cd /tmp/publish-<repo>-mirror.git

# 2. Strip files that should never have been committed
git filter-repo --path .env --invert-paths
git filter-repo --path secrets/ --invert-paths

# 3. Strip strings (paths, IPs, identifiers) from EVERY blob in EVERY commit
cat > /tmp/replace-rules.txt <<'EOF'
/Users/bernard==>~
/home/pm/==>~
157.180.28.14==><HOST>
78.141.205.30==><HOST>
nardovibecoding==><AUTHOR>
okaybernard==><AUTHOR>
EOF
git filter-repo --replace-text /tmp/replace-rules.txt

# 4. Verify: log should show NO original strings
git log --all -p | grep -E '/Users/bernard|157\.180\.28\.14|nardovibecoding' && echo "❌ leftover hits" || echo "✅ clean"

# 5. Push the rewritten history to a fresh remote
gh repo create <user>/<repo> --public
git push --mirror git@github.com:<user>/<repo>.git
```

**Hard rules for filter-repo path:**
- Run on a `--mirror` clone, never the working tree.
- Wallet addresses, API keys, mnemonics — strip the FILE entirely (`--path X --invert-paths`), don't just replace strings. A leaked private key remains valuable even with one byte changed.
- After filter-repo, re-run the full Phase 1.1 privacy scan against the rewritten mirror BEFORE pushing.
- Force-push (`--mirror` push is force) means anyone who already cloned your private repo still has the old history. Rotate every secret that was ever in the old history, regardless of whether you stripped it.

---

## Phase 1 — Pre-push safety (MANDATORY — runs LAST, immediately before Phase 3 push)

**Ordering note:** This phase is numbered Phase 1 historically but runs as the FINAL gate after Phases 0/0.5/2/2.5/2.6 complete. Rationale: every earlier phase mutates the staging dir (README hook rewrites, install.sh edits, ship-auditor may suggest README fixes). An early privacy scan goes stale the moment hook archetype text is inserted with a placeholder, the moment a ship-auditor recommendation lands, or the moment a smoke test causes a README "After" rewrite. Run privacy scan at the moment of truth — right before `git add` for the single fresh-init commit.

### 1.1 Privacy scan

Run AFTER all README/code mutations are complete and BEFORE the first `git add`. Any hit = fix before committing.

**Author-specific identifier list** — define at top of scan, extend per author:

```bash
# Configurable per author. For nardovibecoding:
IDENTIFIERS=(
  'nardovibecoding'
  'okaybernard'
  'bernard@'
  '@bernard'
  'NardoWorld'
  '~/.claude/'
  '/Users/bernard'
  '/home/pm/'           # London bot user
  '/home/kalshi/'       # Hel bot user (if applicable)
  '157\.180\.28\.14'    # Hel
  '78\.141\.205\.30'    # London
  'admin_bot'           # personal TG bot
)
```

```bash
# Personal paths, emails, secrets — hits ANY file type, not just code
grep -rE '/Users/[a-z]+|/home/[a-z]+(?!/)' . --exclude-dir=.git --exclude-dir=node_modules
grep -rE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' . --exclude-dir=.git
grep -rE 'sk-ant-|sk-proj-|ANTHROPIC_API_KEY|OPENAI_API_KEY|Bearer [a-zA-Z0-9]+' . --exclude-dir=.git

# IP addresses (any v4)
grep -rE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' . --exclude-dir=.git | grep -vE '127\.0\.0\.1|0\.0\.0\.0|10\.|172\.|192\.168\.|255\.'

# Wallet patterns (BSC/ETH 0x + Solana base58 + private key hex)
grep -rE '0x[a-fA-F0-9]{40}\b' . --exclude-dir=.git
grep -rE '\b[1-9A-HJ-NP-Za-km-z]{32,44}\b' . --exclude-dir=.git --include='*.md' --include='*.json' | head -20
grep -rE 'POLY_PRIVATE_KEY|PRIVATE_KEY|MNEMONIC|SEED_PHRASE' . --exclude-dir=.git

# Author identifiers (loop through array)
for id in "${IDENTIFIERS[@]}"; do
  echo "=== $id ==="
  grep -rE "$id" . --exclude-dir=.git --exclude-dir=node_modules | head -5
done
```

### 1.1.1 Auto-rewrite helper

For confirmed safe rewrites (paths only, never secrets), batch-replace before the first commit:

```bash
# Show every rewrite + diff before applying. NEVER auto-apply on emails or wallet patterns.
SAFE_REWRITES=(
  's|/Users/bernard|~|g'
  's|/home/pm/|~|g'
  's|~/.claude/|<CLAUDE_HOME>/|g'
  's|~/NardoWorld/|<NARDOWORLD>/|g'
)

# Dry-run first
for pattern in "${SAFE_REWRITES[@]}"; do
  echo "=== $pattern ==="
  grep -rl "$(echo $pattern | cut -d'|' -f2)" . --exclude-dir=.git || true
done

# After Bernard confirms, apply (in-place):
# find . -type f \( -name '*.md' -o -name '*.sh' -o -name '*.py' -o -name '*.json' \) -not -path './.git/*' -exec sed -i '' "$pattern" {} \;
```

**Hard rule**: emails, IPs, wallet addresses, API keys are NEVER auto-rewritten. They must be manually redacted (`<EMAIL>`, `<HOST>`, `<WALLET>`) with human eyes confirming each hit. Auto-rewrite is for paths only.

Rewrite absolute paths → `$HOME`, `~/`, or config-driven. Redact emails. Move secrets to `.env.example`.

### 1.2 LICENSE file

If public and no LICENSE exists, create one. Default **MIT** for tools/libraries unless user specifies. Ask if unsure: "MIT, Apache-2.0, or other?"

Minimal MIT template at end of this file.

### 1.3 .gitignore

Ensure one exists. Minimal safe defaults:

```
.DS_Store
*.pyc
__pycache__/
.venv/
venv/
node_modules/
.env
.env.local
```

Add language-specific entries based on project type (Python → `dist/`, `*.egg-info/`; Node → `build/`, `.next/`; etc).

**HARDENED DEFAULTS — always include for any author with hooks/skills/auto-commit infra:**

```
# Hook state — auto-generated session telemetry, NEVER commit
.router_log.jsonl
*.router_log.jsonl
**/router_log*.jsonl
hook_state/
.hook_state.json
*.hook_log

# Auto-commit byproducts — files written by hook auto-commit / sync hooks
auto_*.log
auto_*.state
*.auto.cache

# Cache + temp
.cache/
*.cache
*.tmp
.DS_Store

# Personal session artifacts
.claude/
.session/
*.session.json
```

These are catch-alls for the common failure mode: a session-telemetry file gets created by a hook, an auto-commit hook sweeps it, and now your prompt history is on a public repo. The patterns above block every variant we've seen.

### 1.3.1 Mirrored-private-repo detection

If the staging dir contains a subdirectory whose NAME matches one of the author's PRIVATE GitHub repos, treat as a leak — vendored private content in a public repo.

```bash
# Get list of private repos for the author
gh repo list <author> --visibility=private --json name --jq '.[].name' > /tmp/priv-repos.txt

# Check staging for matching subdirs
for d in $(find <staging-dir> -maxdepth 2 -type d -printf '%f\n'); do
  if grep -qx "$d" /tmp/priv-repos.txt; then
    echo "LEAK: <staging-dir>/$d matches private repo $d"
  fi
done
```

Action on match: REFUSE to push. Either remove the subdir, or — if the vendoring is intentional (e.g. the public repo legitimately needs to ship the vendored library) — confirm the private repo's content has no secrets via `git filter-repo --analyze` first.

### 1.3.2 Public-history scan (Private → Public visibility flip ONLY)

When flipping a previously-private repo to public, the privacy scan MUST cover the FULL git history, not just the working tree:

```bash
# Scan every commit's tree for sensitive patterns
git log --all -p | grep -E 'BEGIN.*PRIVATE|sk-[A-Za-z0-9_-]{20}|0x[a-fA-F0-9]{40,}|api[_-]?key.*[A-Za-z0-9]{20}' | head
```

Past commits leak the same as current commits. Going public exposes ALL of git log, not just the working tree.

### 1.3.4 Spread-pattern privacy rules (added 2026-04-27 from leak forensics)

Source: 2 leaks shipped + 8 medium-severity findings discovered across 11 public repos. These 7 patterns extend the privacy scan beyond paths/emails/IPs/wallets covered by §1.1.

**[R1] Private-repo-name scan** — before publish, enumerate the author's private repos and grep the staging tree for any match.
```bash
PRIV=$(gh repo list <owner> --visibility=private --limit 100 --json name --jq '.[].name')
for name in $PRIV; do
    grep -rn -F "$name" <staging-dir> --exclude-dir=.git 2>/dev/null && echo "LEAK: $name found in staging"
done
```
Action on match: REFUSE push. Either remove the reference, or wrap as env var (e.g. `os.environ.get("PROJECT_ROOT")` instead of literal `~/telegram-claude-bot`).

**[R2] Personal-vault path scan** — block hardcoded references to private knowledge graphs / personal dirs:
```
NardoWorld | ~/NardoWorld | dagou | /home/pm | /root/pm | telegram-claude-bot
```
Allow only inside `.env.example` with placeholder syntax (`${VAULT_ROOT}`).

**[R3] VPS IP literals** — block hardcoded production IPs:
```
157.180.28.14 | 78.141.205.30 | <any other prod IP from author's infra>
```
Allow only in env-var defaults like `os.environ.get("VPS_HOST", "<placeholder>")`. Maintain an author-specific block list — extend per author.

**[R4] Wallet/key prefixes** — extend §1.1 patterns:
```
0x[a-fA-F0-9]{40,}        # EVM addresses + private keys
POLY_PRIVATE_KEY          # named private-key constants
KALSHI_API_KEY            # named provider keys
hex strings >32 chars in env-var values
```

**[R5] Hook-output state files (universal blocklist)** — block ANY of these committed regardless of size:
```
.router_log.jsonl | *router_log*.jsonl | *.cache | .cache/ | .session.json | *.session.* |
hook_state* | .hook_state.* | auto_*.log | auto_*.state
```
These are the patterns that caused leak #1 (simply-quality-gate router_log). Auto-include in every `.gitignore` (per §1.3 HARDENED DEFAULTS). Block at scan time even if `.gitignore` would also catch them — defense in depth.

**[R6] README cross-link audit** — every `github.com/<owner>/<repo>` link in committed README must resolve to PUBLIC at publish time:
```bash
# Extract all GitHub repo links
links=$(grep -oE 'github\.com/[^/]+/[^/)\s]+' <staging>/README.md | sort -u)
for link in $links; do
    repo=${link#github.com/}
    vis=$(gh repo view "$repo" --json visibility --jq '.visibility' 2>/dev/null)
    [ "$vis" = "PRIVATE" ] && echo "BROKEN: README links to private repo $repo"
done
```
Action on private match: REFUSE push. Stranger clicking the link gets 404.

**[R7] Project-keyword leak (warn, not block)** — flag domain-specific keywords in repos that aren't intended for that domain:
```
polymarket | kalshi | manifold (PM trading)
dagou | bsc | s5 (separate project)
```
If a repo named `simply-skills-curation` contains `polymarket`, that's a leak unless the skill intentionally serves PM traders. Require commit message tag `[intended-leak=<reason>]` to bypass. Warning, not blocker.

**Block sequence at scan time:**
1. Run §1.1 first (paths/emails/IPs/wallets)
2. Run [R1]-[R6] as a single combined sweep
3. Run [R7] as warn-only after blockers pass
4. ANY hit → REFUSE push, print the offending file:line + the rule that caught it

**[R8] Sync-hook audit (pre-publish for repos downstream of an auto-sync pipeline)** — when publishing a repo that's downstream of an auto-sync hook (e.g. `auto_hook_commit.py`, `sync_public_repos.py`, `auto_vps_sync.py`), audit the sync hook BEFORE the first publish:
```bash
# Find any sync script that targets the staging dir
grep -rln "$(basename <staging-dir>)" ~/.claude/hooks/ ~/*/scripts/ 2>/dev/null
# For each match, verify it does NOT use `git add -A` (use allowlist instead)
grep -n 'git add -A\|git add \.' <sync-script> && echo "WARN: sync uses git add -A; allowlist required"
```
Lesson: `git add -A` in any sync hook bypasses the file allowlist. ALL sync hooks must add only allowlisted files OR run a blocklist guard before commit. See `~/telegram-claude-bot/scripts/sync_public_repos.py` Step 4 for the canonical pattern (allowlist + blocklist + working-tree cleanup).

**[R9] Post-purge auto-flip back to PUBLIC** — PURGE-HISTORY mode MUST end with explicit visibility-restore step. Skipping leaves the repo PRIVATE indefinitely after the purge belt. Procedure: track the pre-purge visibility, flip private during purge, flip back at end. Without it, history-purged repos silently lose their public reach.

**[R10] Portfolio-wide rescan after PURGE** — when one leak is found in repo A, automatically scan ALL OTHER public repos by the same author for the SAME pattern. The leak source (a hook, a sync script, a shared config) often affects multiple repos. Running PURGE-HISTORY on A without rescanning B-Z leaves siblings leaking the same pattern.
```bash
# After purging leak X from repo A:
for r in $(gh repo list <owner> --visibility=public --json name --jq '.[].name'); do
    [ "$r" = "$A" ] && continue
    gh api repos/<owner>/$r/contents/X 2>/dev/null | grep -q '^200' && \
      echo "PORTFOLIO LEAK: same pattern $X exists in $r"
done
```
Trigger: every PURGE-HISTORY run includes Step 0 (portfolio rescan) before purging the named target.

**[R11] Source-isolation rule** — staging dir for any publish MUST NOT be the same path as a sync-source dir. If `~/.claude/hooks/` is a sync source AND a publish staging dir simultaneously, hook-output state files (`.router_log.jsonl`, `.cache/`, etc.) accumulate in the source dir and get auto-synced. Resolution: either (a) use a copy in `/tmp/publish-<repo>/` (per Phase 0.5 fresh-init), or (b) explicit `.gitignore` for the hook-output patterns (per §1.3 HARDENED DEFAULTS). The fresh-init pattern in Phase 0.5 already addresses this — make sure every NEW mode invocation actually performs the copy.

---

### 1.3.3 Diff-only scan (FORCE-UPDATE mode ONLY)

For incremental pushes to existing public repos (FORCE-UPDATE mode), scan only the staged diff — full repo scan is overkill on every push:

```bash
git diff --cached | grep -E '<patterns>'
```

If the change touches `install.sh` / `*.json` / `.env`-shaped files, fall back to full Phase 1.1 scan.

### 1.4 Platform declaration

For CLI tools, installers, or anything with shell scripts, declare supported OS in README right above Install:

```markdown
**Platform**: macOS + Linux. Requires <runtime> <version>.
```

Determine platforms by scanning:
- `.sh` or `bash` hooks → macOS + Linux (not Windows unless WSL)
- `osascript`, `afplay`, `pbcopy`, `launchd` references → macOS only
- `systemd`, `apt`, `yum` → Linux only
- `.ps1`, `.bat` → includes Windows
- Pure Python/JS with no OS calls → all major OSes

---

## Phase 2 — Installer (when applicable)

If the project has hooks, skills, or CLI binaries that live under a user config dir, ship `install.sh`:

```bash
#!/bin/bash
set -euo pipefail   # exit on error, unset var, pipefail — never skip

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.claude"      # or wherever

# 1. Copy files
mkdir -p "$TARGET_DIR/hooks"
cp "$REPO_DIR/hooks/foo.sh" "$TARGET_DIR/hooks/foo.sh"
chmod +x "$TARGET_DIR/hooks/foo.sh"

# 2. Patch settings.json IDEMPOTENTLY via python (not sed — JSON needs proper parsing)
python3 - "$TARGET_DIR/settings.json" << 'PYEOF'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
s = json.loads(p.read_text()) if p.exists() else {}
# mutate s safely, checking if entry already exists before appending
p.write_text(json.dumps(s, indent=2))
PYEOF

echo "✅ Installed"
```

Idempotency rule: running the installer twice must not duplicate entries, corrupt JSON, or create dup files.

---

## Phase 2.5 — SMOKE (default-on, skip with `--skip-smoke`)

Run the installer in a sandbox before push. Catches the embarrassing "works on my staging dir but breaks on a fresh clone" class of bugs.

### 2.5.1 Pre-conditions

Auto-skip (no warning) when:
- Project has no `install.sh` (libraries with `pip install` / `npm install` only)
- Project has fewer than 5 source files (overkill)
- User passed `--skip-smoke`

Otherwise run.

### 2.5.2 Procedure

```bash
SMOKE_HOME=$(mktemp -d -t publish-smoke-XXXXXX)
SMOKE_CACHE=$(mktemp -d -t publish-smoke-cache-XXXXXX)
SMOKE_LOG="$SMOKE_HOME/smoke.log"

# Copy the staging dir into a fresh location to simulate a clean clone
SMOKE_REPO="$SMOKE_HOME/repo"
cp -R "$STAGING_DIR" "$SMOKE_REPO"

# Run installer in isolation. Override any default home/inbox/cache paths.
cd "$SMOKE_REPO" && \
  HOME="$SMOKE_HOME" \
  BIGD_INBOX="$SMOKE_HOME/inbox" \
  BIGD_TMPDIR="$SMOKE_CACHE" \
  bash install.sh > "$SMOKE_LOG" 2>&1
```

### 2.5.3 Assert claimed outputs

For each claim the README's "After" / "Quickstart" section makes about post-install state, assert it:

- README says "creates ~/inbox/_summaries/..." → `test -d "$SMOKE_HOME/inbox/_summaries"`
- README shows a `bash run_parallel.sh` example → invoke it, assert exit 0
- README claims a done-marker / log / bundle is produced → `test -f` / `test -s` it
- README says "smoke test passes" → grep the install log for the success line

If any assert fails: print the smoke log path, REFUSE to push, exit 1. The user fixes and re-runs.

### 2.5.4 Cleanup

```bash
rm -rf "$SMOKE_HOME" "$SMOKE_CACHE"
```

Sandbox is preserved on failure (don't `rm -rf` if the assert chain failed) so the user can post-mortem.

---

## Phase 2.6 — SHIP-AUDIT (default-on, skip with `--skip-audit`)

Run `ship-auditor` (the strict-* agent) on the staging dir to catch SPEC drift between README claims and actual code.

### 2.6.1 Pre-conditions

Auto-skip (with one-line warning) when:
- Project has fewer than 5 source files (overkill, README is short enough to eyeball)
- User passed `--skip-audit`
- Project has no README claims to audit (rare; only utility scripts)

Otherwise run.

### 2.6.2 Procedure

Spawn the `ship-auditor` agent with this brief:

```
Task: Reverse-engineer SPEC from <STAGING_DIR>, run adversarial self-review, return verdict.

Inputs:
- Staging dir: $STAGING_DIR
- README: $STAGING_DIR/README.md
- Audience: public OSS, target = solo builders + Claude Code users

Required outputs:
1. .publish/<slug>/01-spec.md — extracted SPEC (numbered claims, each [cited file:line])
2. .publish/<slug>/01-spec-audit.md — adversarial review (per-claim verdict OK / SPEC_DRIFT / RISK / MISSING_CITATION)
3. Quantitative verdict: PASS / NEEDS_FIX / REWORK
4. Top-3 risks before public push

Discipline: every claim must cite file:line. No "looks fine" without a citation.
LSP-first for symbol navigation.
```

### 2.6.3 Verdict gating

- `PASS` → continue to Phase 3 push
- `NEEDS_FIX` → print top-3 risks, ask user "fix and rerun, or push anyway? [y/n]" — accept either
- `REWORK` → REFUSE to push, exit 1, print path to spec + audit files

### 2.6.4 Slug derivation

Slug = repo name with the brand prefix stripped. e.g. `simply-ops-prism` → slug `ops-prism`. Audit artifacts land at `.publish/ops-prism/` next to the staging dir, mirroring the `/ship` convention's `.ship/<slug>/`.

---

## Phase 3 — Push with fallback

### 3.1 Create + push

```bash
gh repo create <user>/<repo> --public --source=. --push --description "<≤350 char one-liner>"
```

### 3.2 If SSH fails (Permission denied publickey)

```bash
git remote set-url origin https://github.com/<user>/<repo>.git
git push -u origin main
```

(HTTPS via gh's cached token works when SSH keys aren't loaded.)

### 3.3 Repo-template flag (opt-in default)

If the repo is meant to be reused as a starting point — boilerplate, scaffold, agent-pack, skill-pack, ship-pipeline-template — flip GitHub's `is_template` flag so users get a one-click "Use this template" button on the repo page.

```bash
gh repo edit <user>/<repo> --template=true
```

**Default behaviour**: ASK before flipping. Most one-off tools/libraries are NOT templates; setting `is_template=true` on a regular repo confuses users (the green button changes from "Code" to "Use this template").

Decision matrix:

| Repo purpose | template? |
|---|---|
| Boilerplate, scaffold, starter | YES |
| Agent pack / skill pack / hook pack designed to be forked-and-customized | YES |
| Ship-pipeline / build-pipeline meant to be cloned per project | YES |
| Library, CLI tool, MCP server, end-user application | NO |
| Documentation site, blog | NO |

Opt-out flag at skill invocation: when the user passes `--no-template` or says "this is a regular repo, not a template", skip 3.3.

To revert later: `gh repo edit <user>/<repo> --template=false`.

---

## Phase 4 — Post-push verification (MANDATORY)

### 4.1 Topics

Add 5-10 relevant topics. See `topics-by-category.md` for picks.

```bash
gh repo edit <user>/<repo> --add-topic <topic1> --add-topic <topic2> ...
```

### 4.2 Verification checklist

Run all:

```bash
gh repo view <user>/<repo> --json url,description,repositoryTopics | python3 -m json.tool
gh repo view <user>/<repo> --web   # eyeball the rendered README
```

Confirm:
- [ ] Description present, ≤350 chars, no typos
- [ ] 5-10 topics attached
- [ ] README renders (no broken markdown, no missing images)
- [ ] LICENSE shows in repo badge
- [ ] install.sh / entry point marked executable (chmod +x pushed correctly)
- [ ] No `/Users/<name>`, no emails, no IPs, no wallet addresses, no author identifiers visible in any file (re-run **full Phase 1.1 expanded grep** against the working tree AND spot-check on github.com raw view)
- [ ] Comments + log strings + error messages also clean (the Phase 1.1 grep covers all file types — verify hits = 0)
- [ ] Template flag matches intent: `gh repo view <user>/<repo> --json isTemplate` shows `true` only if Phase 3.3 was run intentionally

### 4.3 Post-rename recovery

If the repo was renamed after push, check README + docs for stale references:

```bash
grep -r '<old-repo-name>' . --include='*.md'
```

Update any hits, commit, push.

---

## Credits section (when to include)

If the project builds on someone else's pattern, tool, or insight, add a Credits section:

```markdown
## Credits

- Structured template pattern from [hermes-agent](https://github.com/nousresearch/hermes-agent) by Nous Research
- Built with [Claude Code](https://claude.com/claude-code)
```

Triggers: the core idea came from another project, you're porting/simplifying someone else's work, or a specific reference shaped the design. Skip if the work is fully original.

---

## Sibling repo cross-linking

Same-author ecosystem repos should cross-link. Before writing README, run:

```bash
gh repo list <user> --limit 100 --json name,description | python3 -m json.tool
```

Scan for:
- Same topic area (e.g. all `claudecode-*` repos)
- Upstream/downstream relationships (this tool consumes X, or X consumes this)
- Companion repos (this is the auth layer, X is the UI)

Add a one-liner to the README intro: `"Pairs with [other-repo](...)."` and link back from the other repo's README when you next touch it.

---

## MIT LICENSE template

```
MIT License

Copyright (c) <YEAR> <AUTHOR>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Workflow summary

```
Naming check → Fresh-init guard → Privacy scan (paths/IPs/wallets/identifiers)
→ Auto-rewrite paths (paths only, manual for secrets) → LICENSE + .gitignore
→ Platform declaration → install.sh (if applicable)
→ gh repo create (with HTTPS fallback) → Template flag (if reusable scaffold)
→ Topics → Verification checklist → Rename recovery grep
```

Every new public repo. No exceptions.
