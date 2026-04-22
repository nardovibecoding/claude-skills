# Legend Perspectives

Each file = one legend's evolving view of Bernard, his projects, and his harness state.

## Lifecycle

1. **Bootstrap**: file created empty with metadata header
2. **First populate**: `/legends brief <legend>` runs once — legend reads profile.md + wiki + graph + decisions + recent convos, writes their view in their voice
3. **Refresh**: `/legends brief` (all) weekly, or `/legends brief <legend>` after major decision in their domain
4. **Auto-refresh trigger**: edges in graph_index.json linking the legend to a project → refresh when that project's hub node updates

## File format

See `_template.md`. Each perspective file has:
- Metadata header (last_refresh, era_snapshot, status)
- Who-he-is section (their read on Bernard)
- What-he's-building section (ranked by this legend's lens)
- Recent-decisions section (their retrospective on recent calls)
- Standing-advice section (their persistent frame for Bernard right now)
- Pattern-watch section (which cautionary patterns they're watching)

## Language rule

Each perspective written in the legend's native voice:
- LKS → 廣東話 + English mix, 長者口吻
- 林夕 → 廣東話, 禪意
- Jobs → English, minimalist declarative
- Masa → 日本語 or English with Japanese phrasing
- etc. — see matrix.yaml `language` field

## Token budget per file

Target: 300-500 words. Long enough to feel alive, short enough to load cheap at panel call.

## Auto-stale flag

If `last_refresh` > 30 days, perspective is marked stale in panel output. Bernard prompted to `/legends brief`.

## Files

41 perspective files expected (one per legend in matrix.yaml). Created lazily — only when first summoned to a panel or when `/legends brief <legend>` runs.
