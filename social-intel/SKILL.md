---
name: social-intel
description: On-demand pull of Polymarket-relevant Twitter/Reddit signals via social_intel.py. Scans last N hours (default 24), runs LLM intel-extraction, appends date-keyed P0/P1/P2 insights to the rolling log at ~/NardoWorld/trading/polymarket/social-intel.md. Each insight tagged with Affects (strategy file), Confidence, Change block, Hypothesis, Test, Status. Triggers — /social-intel, social intel, pull social intel, refresh social intel. Producer is ~/telegram-claude-bot/social_intel.py (Twitter via twikit, Reddit via public endpoints, LLM via llm_client). NOT FOR — placing trades (read-only research), Manifold or Kalshi-flavored signals (Polymarket-only per producer config), TG fan-out by default (--daily gates that path; this skill calls --hours <N> only). Produces — appended date section in social-intel.md plus stdout summary; consumed by /eval-strats §5 External Research and by humans reviewing strategy adjustments.
---

# social-intel

On-demand wrapper around `~/telegram-claude-bot/social_intel.py` (the Twitter/Reddit → Polymarket strategy intel pipeline).

## Invocation

```
python3 ~/telegram-claude-bot/social_intel.py --hours <N>
```

Default `--hours 24`. The producer scrapes Twitter (`twikit`) + Reddit (r/Polymarket, r/PredictionMarkets), extracts P0/P1/P2 insights via LLM, dedupes against `social-intel-seen-claims.jsonl`, and appends a `## YYYY-MM-DD` block to the rolling log.

### Examples

- Default (last 24h): `python3 ~/telegram-claude-bot/social_intel.py --hours 24`
- Last 48h backfill: `python3 ~/telegram-claude-bot/social_intel.py --hours 48`
- Last 6h quick refresh: `python3 ~/telegram-claude-bot/social_intel.py --hours 6`

## Behavior

1. Scrapes Twitter + Reddit for keywords `polymarket`, `prediction market`, `predictionmarkets`, `预测市场`.
2. LLM extracts P0/P1/P2 insights using bot-strategy context (active vs DISABLED strategies are pre-loaded into the prompt).
3. Per insight, fields emitted: `Affects: <strategy>.ts`, `Confidence: HIGH|MED|LOW`, `Change:` block (proposed code/param change), `Hypothesis:`, `Test:`, `Status: pending`.
4. Appends to `~/NardoWorld/trading/polymarket/social-intel.md` (rolling log, newest date first).
5. Also writes `~/NardoWorld/trading/polymarket/social-intel-link-queue.md` (URLs flagged for manual deeper review).

## TG fan-out behavior

The producer posts to Telegram **only** when `--daily` is passed (gates `push_tg=daily` at `social_intel.py:773`). This skill invokes `--hours <N>` without `--daily`, so calling `/social-intel` does NOT spam TG. Use `python3 ~/telegram-claude-bot/social_intel.py --daily` directly for the cron-style daily TG digest path.

## Output paths

- rolling log: `~/NardoWorld/trading/polymarket/social-intel.md`
- link queue: `~/NardoWorld/trading/polymarket/social-intel-link-queue.md`
- seen-URLs dedup: `~/NardoWorld/trading/polymarket/social-intel-seen-urls.jsonl`
- seen-claims dedup: `~/NardoWorld/trading/polymarket/social-intel-seen-claims.jsonl`

## Failure modes

- Twitter auth lapses (cookies expired) → producer exits non-zero, stderr surfaces. Refresh cookies via `~/telegram-claude-bot/twitter_cookies.json` rotation flow. Rolling log unchanged on failure.
- LLM 429 / quota → producer retries via `llm_client._FALLBACK_CHAIN`; if all chain members fail, exits non-zero.
- Reddit public endpoint blocked → entries from Reddit drop, Twitter signals still emit. No abort.

## Consumed by

- `/eval-strats` §5 External Research — parses last 14 days of rolling-log entries, groups by P0/P1/P2, joins per-strategy via `Affects:` field. Suppress with `--no-external-research`.
- Humans reviewing strategy adjustments before promoting/retiring code paths.

## Spec source

`~/.ship/eval-strats-social-intel-integration/goals/01-spec.md` REQ-1, REQ-2, REQ-3, REQ-10.

## Version

v1.0 (2026-04-27 — Phase 3 EXECUTE Slice 1).
