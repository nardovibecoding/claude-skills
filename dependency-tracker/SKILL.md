---
name: dependency-tracker
description: Use when ANY change is made to the system — renamed files, moved configs, changed persona IDs, updated thread IDs, modified cron jobs, edited config.py, or restructured code. Automatically finds and updates ALL references across the entire codebase. Triggers on "check dependencies", "update references", "what references X", "sync dependencies", or after any rename/move/restructure operation.
---

# Dependency Tracker

## The Problem

Every change has downstream references scattered across 10+ files. Missing even one creates silent breakage:
- Renamed persona → stale references in config.py, auto_healer.py, admin_bot, cron, memory
- Changed thread ID → messages routed to wrong topic
- Moved file → imports break, cron paths break, start_all.sh breaks
- Changed env var → .env, .zshrc, systemd units, persona configs all need updating

## When to Use

**ALWAYS** after any of these actions:
- Rename/move/delete a file
- Change a persona ID or display name
- Modify thread IDs or chat IDs
- Change config.py values
- Update cron jobs
- Rename env variables
- Change model names or API endpoints
- Restructure directories

## The Dependency Map

### For ANY change, scan ALL of these locations:

#### Code Files
| File | Contains |
|------|----------|
| `config.py` | BOTS, BOT_THREADS, API keys, model config |
| `admin_bot.py` | Command handlers, bot references |
| `admin_bot/commands.py` | Digest schedules, flag files, bot lists |
| `admin_bot/callbacks.py` | Voting UI, persona display names |
| `bot_base.py` | Shared bot logic, persona loading |
| `run_bot.py` | Bot runner, persona ID usage |
| `start_all.sh` | Process management, restart logic |
| `auto_healer.py` | Health monitoring, flag files, port checks |
| `send_xdigest.py` | X_PERSONAS list, digest routing |
| `send_digest.py` | News/crypto digest routing |
| `x_curator.py` | X curation, scoring, persona config reads |
| `x_feedback.py` | Bookmark taste profiles |
| `news.py` | News sources, scraping |
| `crypto_news.py` | Crypto news sources |
| `reddit_digest.py` | Reddit config |
| `china_trends.py` | China trends sources |

#### Config Files
| File | Contains |
|------|----------|
| `personas/*.json` | All persona configs (names, threads, tokens, prompts) |
| `.env` | API keys, tokens, env vars |
| `domain_groups.json` | News domain groupings |
| `claude_sessions.json` | Active Claude sessions per bot |

#### Infrastructure
| Location | Contains |
|----------|----------|
| `crontab -l` | Scheduled jobs, file paths, script references |
| systemd units | Service definitions, paths, env vars |
| `.claude/settings.json` | MCP server config, env var references |

#### Memory & Docs
| File | Contains |
|------|----------|
| `CLAUDE.md` | Rules referencing specific files, bots, IDs |
| `ADMIN_HANDBOOK.md` | Operational docs, process names, paths |
| `TERMINAL_MEMORY.md` | Architecture docs |
| `memory/*.md` | Project/feedback memory files |
| `plans/*.md` | Active plans |

## Execution Process

### Step 1: Identify the Change
What was changed? Extract the OLD value and NEW value.

Example: persona `twitter` display name changed from "Twitter Curator" to "九院院长"

### Step 2: Full Grep Scan
Search for ALL occurrences of the old value across the entire project:

```bash
# Search code
grep -rn "OLD_VALUE" ~/telegram-claude-bot/ --include="*.py" --include="*.sh" --include="*.json" --include="*.md" --include="*.env"

# Search cron
crontab -l | grep "OLD_VALUE"

# Search systemd
grep -rn "OLD_VALUE" /etc/systemd/system/ 2>/dev/null

# Search claude config
grep -rn "OLD_VALUE" ~/.claude/ --include="*.json" --include="*.md" 2>/dev/null
```

### Step 3: Categorize Results

Sort findings into:
| Category | Action |
|----------|--------|
| **Must update** | Direct references that will break if not changed |
| **Should update** | Display names, comments, docs — won't break but misleading |
| **Skip** | Git history, logs, cache files — read-only/ephemeral |

### Step 4: Propose Changes (DO NOT EDIT YET)
For each "must update" and "should update" reference, prepare the exact edit:
```
📝 Proposed changes (8 total):

MUST UPDATE:
1. config.py:45 — "twitter" → "九院院长"
2. send_xdigest.py:12 — TELEGRAM_BOT_TOKEN_TWITTER → unchanged (still correct key name)
3. auto_healer.py:89 — "twitter" → "twitter" (persona ID unchanged, display name only)

SHOULD UPDATE:
4. memory/project_personas.md:13 — "Elon | X curation EN" → "九院院长 | XHS 医美"
5. CLAUDE.md:234 — "twitter (Elon)" → "twitter (九院院长)"

NO ACTION:
6. git history — read-only
7. .digest_sent_x_twitter — flag file, persona ID unchanged
```

### Step 5: User Confirmation
**STOP and show the proposed changes. Ask: "Approve all? Or select which to apply?"**

Options:
- "yes" / "approve" → execute all proposed edits
- "skip 3,5" → execute all except items 3 and 5
- "no" / "cancel" → abort, no changes made

### Step 6: Execute + Verify
After approval:
- Apply all approved edits using Edit tool
- `python3 -c "import py_compile; py_compile.compile('file.py', doraise=True)"` for each changed .py
- Verify JSON validity for any changed .json files
- Check cron syntax if cron was modified
- If ANY verification fails → revert that specific file and warn

### Step 7: Report
Output a change report:

```
## Dependency Update Report

### Change: [description]

### Updated (X files):
- file.py:123 — old → new
- config.json — old → new

### Verified:
- [x] Python syntax check passed
- [x] JSON valid
- [x] Cron syntax valid

### No action needed:
- git history (read-only)
- log files (ephemeral)
```

## Common Dependency Chains

### Persona rename/repurpose
```
personas/ID.json → config.py BOTS{} → admin_bot/commands.py DIGEST_BOTS
                 → send_xdigest.py X_PERSONAS → auto_healer.py digest flags
                 → admin_bot/callbacks.py display names → memory/project_personas.md
                 → CLAUDE.md persona list → ADMIN_HANDBOOK.md
```

### Thread ID change
```
personas/ID.json thread_id → config.py BOT_THREADS{} → admin_bot message routing
                            → send_xdigest.py target → auto_healer.py checks
```

### New env var
```
.env → .zshrc (source) → systemd EnvironmentFile → personas/*.json (if referenced)
     → config.py (os.getenv) → .claude/settings.json (if MCP needs it)
```

### File rename/move
```
old_path → all imports → start_all.sh → crontab → systemd ExecStart
         → CLAUDE.md references → ADMIN_HANDBOOK.md → memory/*.md
```

### Cron job change
```
crontab entry → auto_healer.py schedule checks → admin_bot/commands.py schedule display
              → ADMIN_HANDBOOK.md docs → memory/project_*.md
```

## Anti-Patterns
See [references/anti-patterns.md](references/anti-patterns.md)
