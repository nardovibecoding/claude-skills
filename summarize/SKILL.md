---
name: summarize
description: |
  Adaptive summarization — output length scales with input length for comfortable reading.
  Triggers: "summarize", "summarize this", "tldr", "too long", "sum up", "key points", "give me summary".
  NOT FOR: translation (just ask), content creation (use content-humanizer).
  Produces: summary at optimal compression ratio based on input length.
---

# Adaptive Summarization

Summary length automatically scales with input for comfortable reading.

## Compression Ratios — English

| Input | Target output | Ratio | Style |
|-------|--------------|-------|-------|
| < 500 words | 2-3 sentences | ~20% | Key takeaway only |
| 500-1,500 words | 80-120 words | ~10% | Core points condensed |
| 1,500-3,000 words | 150-250 words | ~8% | Structured summary |
| 3,000-8,000 words | 300-500 words | ~6% | Section-by-section |
| 8,000-20,000 words | 500-800 words | ~4% | Executive brief |
| 20,000+ words | 800-1,200 words | ~3% | Full executive summary |

## Compression Ratios — Chinese (中文)

Chinese packs ~1.5x more meaning per character. Summaries should be shorter.

| Input | Target output | Ratio | Style |
|-------|--------------|-------|-------|
| < 300字 | 1-2句话 | ~15% | 一句话概括 |
| 300-1,000字 | 50-80字 | ~8% | 要点浓缩 |
| 1,000-2,000字 | 100-160字 | ~6% | 分段总结 |
| 2,000-5,000字 | 200-350字 | ~5% | 按主题分段 |
| 5,000-15,000字 | 350-550字 | ~3% | 摘要+关键引用 |
| 15,000字+ | 500-800字 | ~2.5% | 完整摘要报告 |

## Language Detection
- Detect input language automatically
- Summarize in the SAME language as the input (unless asked otherwise)
- Mixed language input → summarize in the dominant language

## Process

1. **Estimate input length** — count words or estimate from tokens
2. **Pick ratio** from table above
3. **Summarize** following the target length
4. **Format** based on output length:
   - < 100 words → plain text, no headers
   - 100-300 words → bullet points
   - 300+ words → headers + bullets + key quotes

## Rules
- Lead with the MOST important point, not chronological order
- Include specific numbers, names, dates — not vague generalities
- If the source has a conclusion/recommendation, always include it
- For technical content: explain jargon in parentheses
- For news: who, what, why, impact
- For research: methodology → findings → implications
- Preserve the TONE of the original (formal stays formal, casual stays casual)
- End with: "Worth reading in full?" + honest 1-line verdict
