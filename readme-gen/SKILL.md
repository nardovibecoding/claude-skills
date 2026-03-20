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
