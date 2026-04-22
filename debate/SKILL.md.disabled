---
name: debate
description: |
  6-model R&D Council debate — multi-round argument, cross-examination, consensus memo.
  Triggers: "/debate", "council", "R&D meeting", "model debate", "6 models discuss".
  NOT FOR: simple questions (just ask), code review (use review), brainstorming (use office-hours).
  Produces: executive memo with consensus position from 6 AI models.
---

# R&D Council — Multi-Model Debate

6 AI models (MiniMax, Cerebras, DeepSeek, Gemini, Kimi K2, Qwen3) autonomously
debate a topic across multiple rounds, then produce an executive memo.

## How It Works

### Round 1: Independent Analysis
Each model independently answers the question/topic. No model sees the others.
Uses `chat_completion_multi()` from llm_client.

### Round 2: Cross-Examination
Each model receives ALL other models' Round 1 answers and must:
- Identify the strongest argument they AGREE with (and why)
- Challenge the weakest argument they DISAGREE with (and why)
- Refine their own position based on what they learned

### Round 3: Final Position
Each model gives their final answer after seeing Round 2 cross-examinations.
Must state: "I changed my mind because..." or "I maintain my position because..."

### Synthesis: Judge Memo
A judge model (MiniMax) reads all 3 rounds and produces:

```
📋 R&D COUNCIL MEMO — {date}
Topic: {topic}

🏆 CONSENSUS (what all models agree on):
• ...

⚡ KEY DISAGREEMENTS:
• Model A vs Model B on X — Model A won because...

💡 TOP 3 ACTION ITEMS:
1. [Actionable, specific, with owner if applicable]
2. ...
3. ...

🔮 CONTRARIAN INSIGHT (what only 1-2 models saw):
• ...

📊 Confidence: X/10 | Cost: $X.XX | Models: 6/6 responded
```

## Usage

### On-demand
```
/debate Should we add Discord outreach to the MEXC BD pipeline?
/debate What's the best architecture for the social media 矩阵?
/debate Review our outreach message templates — which ones will convert best?
```

### Scheduled (cron)
The council can run automatically 2x daily with pre-set topics:
- Morning (9AM): Review yesterday's metrics + suggest today's priorities
- Evening (5PM): Evaluate today's progress + identify blockers

Topics rotate from a configurable list or are generated from live data
(digest performance, outreach stats, Andrea's latest ideas).

## Implementation

Uses `llm_client.py`:
- Round 1: `chat_completion_multi(messages)` — all 6 in parallel
- Round 2: 6x `chat_completion(messages + all_round1_responses)` — sequential or parallel
- Round 3: 6x `chat_completion(messages + round2_crossexam)` — final positions
- Judge: `chat_completion(all_rounds_combined, judge_prompt)`

Total: ~20 API calls per debate. All free tier. ~2-3 minutes.

## Saving History
All debates saved to `debate_history.json`:
- Date, topic, all rounds, final memo
- Keeps last 90 days
- Can review past debates: `/debate history`
