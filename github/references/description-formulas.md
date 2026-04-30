# Repo Description Formulas

The repo description (one-liner under the name) is critical for GitHub search ranking
and first impressions. Max 350 chars, but aim for <120.

## Formula

```
[Superlative/action] [category noun] [for/that] [key use case] [(differentiator)]
```

## Examples from 100K+ star repos

| Repo | Stars | Description |
|------|-------|-------------|
| uv | 40K | "An extremely fast Python package and project manager, written in Rust" |
| Ollama | 120K | "Get up and running with Llama 3.3, DeepSeek-R1, Phi-4, Gemma 3, and other large language models." |
| FastAPI | 85K | "FastAPI framework, high performance, easy to learn, fast to code, ready for production" |
| shadcn/ui | 110K | "Beautifully designed components that you can copy and paste into your apps." |
| Open WebUI | 70K | "User-friendly AI Interface (Supports Ollama, OpenAI API, ...)" |

## Patterns that work

**Action verb lead** (Ollama pattern):
- "Get up and running with..."
- "Scan and audit..."
- "Build and deploy..."

**Superlative + differentiator** (uv pattern):
- "An extremely fast [X], written in [Y]"
- "The simplest way to [X]"
- "A lightweight [X] that [unique thing]"

**Feature-stack** (FastAPI pattern):
- "[Name]: [adj], [adj], [adj], [adj]"

**User benefit** (shadcn pattern):
- "[Adjective] [things] that you can [action]"

## Anti-patterns (avoid)
- "A tool that..." (passive, boring)
- "This project..." (redundant — they're ON the project)
- Starting with the repo name (redundant — it's in the title)
- Buzzwords without substance ("revolutionary", "next-gen", "powerful")
- Too long (>150 chars gets truncated in search results)

## Template for Claude Code skills
```
[What it does] — [key differentiator]. [Number] [concrete metric].
```
Examples:
- "Scan Claude Code skills for malicious code, prompt injection, and exfiltration. 50+ detection patterns, PASS/WARN/FAIL verdicts."
- "Audit and optimize CLAUDE.md rules — classify, trim bloat, save context window tokens."
