---
name: extractskill
description: |
  Evaluate and install community AI skills from GitHub URLs or skill repos.
  Triggers: "extract skill", "evaluate skill", "check this skill", shared skill URL, list of skills to review.
  NOT FOR: security scanning (use skill-security-auditor), skill cleanup (use lint).
  Produces: installed skill or extracted patterns saved to memory.
user-invocable: true
---

# Extract Skill — Evaluate & Extract Community Skills

Fast-track evaluation of community AI skills. Fetch, Assess, Install or Extract.

## When to Use

- User shares a GitHub URL to a skill or skill repo
- User says "extract skill", "evaluate this skill", "check this skill"
- User shares a list of skills to review
- After finding skills via evolution feed, web search, or recommendations

## Process

### Step 1: Fetch & Read

For each skill URL:
1. Fetch SKILL.md (try raw.githubusercontent.com for GitHub URLs)
2. Fetch README.md if SKILL.md is thin
3. Check for scripts/, references/, templates/ directories
4. Read enough to understand what it does

### Step 2: Evaluate (30 seconds per skill)

Score against Bernard's existing system:

**Overlap check** — Does our system already do this?
- Check installed skills: `ls ~/.claude/skills/`
- Check plugins: security-guidance, hookify, frontend-design
- Check existing tools (confirm-existing before assuming): `~/.claude/hooks/` + `~/.claude/scripts/` (grep for memory system, skill-security-auditor, dispatcher_post.py, graph_merge.py)
- Check CLAUDE.md rules + `~/.claude/rules/*.md`
- Check memory files: `ls ~/.claude/projects/-Users-bernard/memory/ | grep -iE 'research|feedback|reference'`

**Score: 0-100% overlap**
- 0-30%: Genuinely new capability — INSTALL candidate
- 30-70%: Partial overlap — EXTRACT the unique parts
- 70-100%: We already do this — SKIP

**Value check** — Is it relevant to our system?
- Telegram bots, X curation, Reddit digest, news aggregation, MCP servers, face app
- VPS deployment, security, monitoring, memory management
- If it solves a problem we don't have, SKIP regardless of overlap

### Step 3: Security Scan (MANDATORY — not optional)

**Must run before any INSTALL.** Invoke `skill-security-auditor` skill on the fetched skill directory. Do NOT fall back to manual grep — the auditor covers 11+ threat categories the eyeball-check misses.

```bash
# Point auditor at the fetched skill
~/.claude/skills/skill-security-auditor/scripts/skill_security_auditor.py <fetched-skill-dir>
```

Gate logic:
- **PASS** → proceed to Step 4 Act
- **WARN** → surface findings, require user confirm before install
- **FAIL** → STOP. Do NOT install. Report findings + offer to open in read-only mode for manual review.

Covered categories: eval/exec/shell=True, network calls, credential harvesting, prompt injection, DNS exfil via gethostbyname, filesystem writes outside skill dir, subprocess shell injection, env var reads, pickle/marshal deserialization, etc.

### Step 4: Act

**If INSTALL:**
1. Create ~/.claude/skills/<name>/
2. Write all files (SKILL.md, scripts, references, templates)
3. Verify it appears in skill list

**If EXTRACT:**
1. Read the skill thoroughly
2. Extract ONLY the unique patterns/techniques we're missing
3. Append to ~/.claude/projects/-Users-bernard/memory/research_extracted_patterns.md
4. Update MEMORY.md if adding a new reference file
5. If patterns are actionable rules, route per CLAUDE.md "Rule promotion routing" HARD RULE: project/domain-specific → `~/.claude/rules/<scope>.md`; truly universal → CLAUDE.md. Default to scoped file — CLAUDE.md stays lean.

**If SKIP:**
1. One-line explanation why
2. Move on

### Step 5: Report

For each skill, output one line:

- [INSTALL] skill-name — what it adds (X files installed)
- [EXTRACT] skill-name — what patterns saved (N lines added to memory)
- [SKIP] skill-name — why (80% overlap with X)

## Batch Mode

When given a repo URL with multiple skills:
1. Fetch the repo directory listing
2. List all skills with 1-line description
3. Ask user which to evaluate (or evaluate all)
4. Process in parallel using background agents
5. Present summary table

## Output Format

| Skill | Verdict | Overlap | Unique Value |
|---|---|---|---|
| skill-name | INSTALL/EXTRACT/SKIP | 45% | What it adds |

## Important

- Always use background agents for fetching/evaluation
- Run skill-security-auditor before any install
- Never install enterprise/compliance frameworks (SOC2, HIPAA, PCI-DSS) — not relevant
- Extracted patterns go to memory, not CLAUDE.md (unless they are actionable rules)
- If a skill is just a static playbook (no scripts, no hooks), EXTRACT don't INSTALL
