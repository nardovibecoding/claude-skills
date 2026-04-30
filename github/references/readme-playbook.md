---
name: readme-gen
description: |
  Generate an excellent README.md for any repository by analyzing the codebase and
  applying battle-tested patterns from top GitHub projects.

  USE FOR:
  - "write a readme for this project"
  - "generate a README"
  - "create README.md"
  - "improve the readme"
  - When uploading a project to GitHub and a README is needed

allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(git *)
  - Bash(ls *)
  - Bash(wc *)
---

# README Generator Skill

Generates professional, high-impact README files based on patterns from top GitHub
projects (FastAPI, Ollama, Open WebUI, AutoGPT, n8n, python-telegram-bot, Stagehand,
AutoGen). The goal is a README that converts visitors into users and contributors.

---

## Execution Steps

> **Companion reference**: for the full publish pipeline (privacy scan, LICENSE, install.sh, `gh repo create` with fallback, post-push verification, sibling cross-linking), see `publish-workflow.md`. Load both when scaffolding a new public repo.

### Step 1 — Discover the project

Run these in parallel to understand the project before writing a single word:

```bash
# Language/framework detection
ls -la <project_root>
```

Also:
- Read all top-level config files: `package.json`, `pyproject.toml`, `requirements.txt`,
  `Cargo.toml`, `go.mod`, `composer.json`, `Gemfile` — whatever exists
- Read `*.env.example` or `.env.example` if present
- Glob for entry points: `main.py`, `app.py`, `index.ts`, `server.js`, `bot.py`, `run*.py`
- Read the top 3-5 most important source files (entry points + core logic)
- Check for existing docs: `docs/`, `wiki/`, any `.md` files
- Check `git log --oneline -20` for commit history (reveals features added over time)
- Check `git tag` for version history

Goal: understand **what it does**, **who uses it**, **how it runs**, **what makes it special**.

### Step 2 — Classify the project type

Pick the closest match — this determines which optional sections to include:

| Type | Key optional sections to add |
|------|------------------------------|
| Bot / automation agent | Architecture diagram (text), persona/agent table, command reference |
| CLI tool | Commands table, shell completion note |
| Web app / API | Endpoints table or screenshot, environment variables table |
| Library / SDK | API reference snippet, framework compatibility table |
| MCP / integration | Tool listing table, host compatibility, auth setup |
| Voice / audio system | Hardware requirements, latency specs, audio pipeline diagram |
| Multi-component system | Component table, service diagram, startup sequence |

### Step 3 — Choose the right sections

Every README gets the **Core sections** (always present). Add **Optional sections** based
on project type and what actually exists in the code. Never pad with empty sections.

---

## The Universal Structure (from 100K+ star repos)

```
1. Centered logo/banner
2. One-line tagline
3. Badge row (stars, version, CI, Discord, license — 5 max)
4. Hero image OR benchmark chart OR demo GIF
5. Social proof (optional: quote, stat, "Used by X")
6. What-it-is description (1-3 sentences)
7. Key features (4-8 bold bullets)
8. Single-command install
9. Working example (<20 lines)
10. Detailed features / integrations
11. Contributing (3-5 lines)
12. Star History chart
13. License
```

---

## Section Playbook

### CORE SECTIONS (always include)

---

#### 1. Header Block

```markdown
<div align="center">
  <img src="assets/logo.png" alt="Project Logo" width="120" />
  <h1>Project Name</h1>
  <p><strong>One punchy sentence that says exactly what this does.</strong></p>
  <p>Optional: second sentence with the "why" — what problem it solves.</p>

  <!-- Badges: pick only what is TRUE and USEFUL -->
  ![Python](https://img.shields.io/badge/python-3.11+-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)
  ![Status](https://img.shields.io/badge/status-active-brightgreen)
</div>
```

**Badge rules (from studying top repos):**
- Language + version badge: always include if the language matters to setup
- License badge: always include
- Build/CI status: include only if CI actually exists in the repo
- Download/install count: include only for published packages (npm, PyPI)
- Discord/community: include if a real community link exists
- Version: include for released packages, skip for personal/internal tools
- NEVER add badges that link to dead pages or show "unknown" status
- Keep badge count to 5 or fewer — top repos (Ollama, Stagehand) stay minimal

**One-liner rules:**
- Must fit in one line, no passive voice, no "a tool that"
- Good: "Run large language models locally."
- Bad: "This is a project that can be used to run various large language models on your machine."
- For multi-persona / multi-component systems: name the top-level capability, not every component

---

#### 2. Features

```markdown
## Features

- **Feature Name** — One sentence description. Focus on user benefit, not implementation.
- **Feature Name** — Be concrete: "Supports 9 personas with independent memory and voice profiles" beats "Multi-persona support"
- **Feature Name** — If a feature is unique/differentiating, say so explicitly
```

**Patterns from top repos:**
- Open WebUI: emoji prefix + bold name + description
- AutoGen: group features by category with sub-bullets when there are 8+
- n8n: bold name, plain description, no emoji (cleaner for technical audiences)
- Rule of thumb: 5-10 bullets. More than 10 → group into categories.
- Always lead with the 2-3 most impressive/unique features, not alphabetically

For **bot/agent systems** specifically, a features table often beats a bullet list:

```markdown
| Feature | Details |
|---------|---------|
| Personas | 9 independent AI personas, each with unique voice, memory, and digest schedule |
| News Digest | Level-2 deep analysis: top stories → cross-source match → full article scrape → AI summary |
| X Curation | Home timeline + 13 lists, blue-verified filter, engagement-rate scoring, feedback loop |
| Voice I/O | Whisper large-v3 STT, per-persona language, VAD auto-detection |
```

---

#### 3. Quickstart / Getting Started

This is the **most important section**. Visitors abandon READMEs here.

Rules:
- First working command must appear within 3 scrolls from the top of the README
- Show the simplest possible path first, advanced options after
- Every code block must be copy-pasteable without modification (no `<YOUR_VALUE>` if avoidable)
- Include expected output for the first command when it helps confidence
- AutoGen pattern: Hello World → intermediate → advanced, each as separate named blocks

```markdown
## Getting Started

### Prerequisites
- Python 3.11+
- [Something else] installed

### Install

\```bash
git clone https://github.com/you/repo.git
cd repo
pip install -r requirements.txt
cp .env.example .env   # then fill in your API keys
\```

### Run

\```bash
python run_bot.py daliu
\```

Expected output:
\```
[daliu] Bot started. Polling for messages...
\```
```

For **multi-component systems**, add a "Start everything" section.

---

#### 4. Configuration

Include when the project has meaningful configuration (env vars, JSON configs, etc.).

```markdown
## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_TOKEN` | Yes | Your bot token from @BotFather |
| `MINIMAX_API_KEY` | Yes | MiniMax API key |
| `WHISPER_MODEL` | No | Whisper model size (default: `large-v3`) |
```

**Rule**: env var tables are more scannable than prose. Always use tables for config docs.

---

#### 5. License

```markdown
## License

MIT — see [LICENSE](LICENSE)
```

Keep it one line unless the license has unusual terms.

---

#### 6. Hero Visual (after badges, before features)

Place the strongest visual proof above the fold. Pick ONE:

**Demo GIF** (for CLI tools, skills, bots):
```markdown
<div align="center">
  <img src="assets/demo.gif" alt="Demo" width="700" />
</div>
```
Auto-generate with VHS — see [references/vhs-templates.md](references/vhs-templates.md).

**Benchmark chart** (for performance-focused tools like uv):
```markdown
<div align="center">
  <img src="assets/benchmark.png" alt="Benchmarks" width="700" />
</div>
```

**Screenshot** (for web apps, UIs):
Use dark/light mode support:
```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/screenshot-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/screenshot-light.png">
  <img alt="Screenshot" src="assets/screenshot-dark.png" width="700">
</picture>
```

**Rules:**
- Skip if no visual exists — never use placeholders
- Dark backgrounds perform better (most GitHub users use dark mode)
- Keep GIFs under 15 seconds and 5MB
- One hero visual only — additional screenshots go in `<details>` collapsible

---

#### 7. Social Proof (optional, high impact)

Only include if real. Fake social proof backfires.

**Named testimonial** (FastAPI pattern — Microsoft, Uber, Netflix):
```markdown
> "Quote from a notable user or company."
> — **Name**, Role at Company ([source](link))
```

**Used-by logos**:
```markdown
### Used by
<p>
  <img src="https://img.shields.io/badge/Company_1-logo?style=flat" />
  <img src="https://img.shields.io/badge/Company_2-logo?style=flat" />
</p>
```

**Stats badge** (npm downloads, PyPI installs):
```markdown
![Downloads](https://img.shields.io/npm/dw/package-name)
```

**Personal stat** (gstack pattern):
```
"600K lines of code shipped in 60 days"
```

---

#### 8. Why This Over X? (comparison table)

Only include if meaningful competitors exist. Pattern from uv (benchmark chart) and FastAPI (vs Flask).

```markdown
## Comparison

| Feature | This Tool | Alternative A | Alternative B |
|---------|-----------|---------------|---------------|
| Speed | 10x faster | Baseline | 2x faster |
| Install | 1 command | 5 steps | 3 steps |
| Config | Zero-config | YAML required | JSON required |
```

**Rules:**
- Be honest — don't lie about competitors
- Focus on measurable differences, not subjective claims
- If you can't fill the table with real data, skip this section

---

#### 8b. Related Repos (same-author ecosystem linking)

When the author has other public repos in the same space, link them. This compounds discoverability across the ecosystem.

Before writing the README, run:

```bash
gh repo list <author> --limit 100 --json name,description
```

Scan for same-topic repos. Add a one-line callout near the top of the README:

```markdown
Pairs with [sibling-repo-name](https://github.com/author/sibling-repo-name) for <what the sibling does>.
```

Also plan to add a reverse link in the sibling's README next time it's edited. Skip this section entirely if no related same-author repos exist.

**Credits subsection** (only if the project builds on another's pattern/tool):

```markdown
## Credits

- <Pattern name> inspired by [upstream-repo](...) by <author>
- Built with [Claude Code](https://claude.com/claude-code)
```

Skip Credits entirely if the work is fully original — do not pad with filler acknowledgments.

---

#### 9. Star History (bottom of README)

```markdown
## Star History

<a href="https://star-history.com/#user/repo&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=user/repo&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=user/repo&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=user/repo&type=Date" />
 </picture>
</a>
```

Skip for brand-new repos (empty chart looks sad). Add after first 50+ stars.

---

### OPTIONAL SECTIONS (add when relevant)

---

#### Architecture (for multi-component systems)

ASCII diagrams beat no diagrams when a real image doesn't exist. Mermaid is acceptable
but renders poorly on GitHub without a plugin. ASCII renders everywhere.

```
Telegram API
     │
     ▼
 bot_base.py  ←──  personas/<id>.json (character, language, schedule)
     │
     ├── memory.py        (per-persona vector DB)
     ├── news.py          (Level-2 news digest)
     ├── x_curator.py     (X/Twitter curation pipeline)
     ├── reddit_digest.py (Reddit top posts)
     └── voice/           (Whisper STT + TTS)
```

Pattern from AutoGPT: name each component with a one-liner role.
Pattern from AutoGen: show the layered architecture (Core → AgentChat → Extensions).

---

#### Personas / Agents Table (for bot/agent systems)

```markdown
| ID | Name | Character | Digest | Voice |
|----|------|-----------|--------|-------|
| `daliu` | 大劉 | HK tycoon, Cantonese | Daily news (11:39 HKT) | Yes |
| `sbf` | SBF | Crypto bro | Daily crypto (11:45 HKT) | Yes |
| `twitter` | Elon | X curation (EN) | Daily X picks | No |
```

---

#### Commands Reference (for bots / CLIs)

```markdown
| Command | Description |
|---------|-------------|
| `/start` | Greet and introduce the persona |
| `/digest` | Manually trigger news digest |
```

---

#### How It Works (for non-obvious pipelines)

Use numbered steps. Pattern from Ollama's quickstart and AutoGPT's workflow examples.

```markdown
### News Digest Pipeline

1. RSS feeds fetched from configured sources
2. Top 5 stories selected by recency + source diversity
3. Articles cross-matched across sources (deduplication)
4. Full article text scraped (Level 2 deep analysis)
5. Real content fed to AI for synthesis — no hallucinated summaries
6. Delivered to Telegram topic thread at scheduled time
```

---

#### Screenshots / Demo

- Put the single most impressive screenshot right at the top of the section
- Use `<details>` collapsible for secondary screenshots
- GIFs are extremely effective for CLI tools and bots
- If no screenshots exist yet, skip this section entirely

---

#### Project Structure (for 10+ file projects)

```
project/
├── entry.py      # Entry point
├── core.py       # Core logic
└── config/       # Configuration files
```

Rules:
- Only include for projects with 10+ files where layout isn't obvious
- Annotate every entry — a bare file list is useless
- Skip `__pycache__/`, `.git/`, `venv/` and other noise

---

#### Deployment (for server-side projects)

Include startup command, log location, and sync/deploy flow.

---

#### Contributing

Keep to 3-5 lines for personal/small-team projects.

---

#### Roadmap (optional)

Use GitHub checkboxes (`- [ ]`). Skip if the roadmap is vague or unknown.

---

## Writing Rules (Distilled from 8 Top Repos)

### Tone and copy
- Write for a technical audience who is time-constrained. Every sentence must earn its place.
- Use active voice: "Runs on Python 3.11" not "Python 3.11 is required"
- Lead with value: say what it does BEFORE saying how it works
- Concrete beats vague: "9 AI personas with independent memory" beats "multi-persona support"
- No marketing fluff ("revolutionary", "game-changing", "powerful") — let the features speak

### Structure
- Quickstart must be reachable within 3 scrolls — never bury installation
- Tables over prose for: config vars, commands, personas, tools, file structure
- Code blocks for every terminal command, no exceptions
- `<details>` collapsible for secondary content (more screenshots, extended config, etc.)
- "Back to top" links only needed for READMEs longer than ~400 lines

### What to skip
- TOC: only add for READMEs longer than 300 lines
- Screenshots: skip if none exist, never use placeholder images
- Roadmap: skip if the list is aspirational vaporware
- Contributing: keep to 3-5 lines for personal/internal projects
- Badges: 5 max; skip CI badges if no CI pipeline exists
