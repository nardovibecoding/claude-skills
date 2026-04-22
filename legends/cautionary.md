# Cautionary Pattern Library

Failure modes derived from legends who crashed. If your move matches a pattern here, genie auto-summons that legend as a warning voice — regardless of fitness score.

---

## P1 — Borrowed Leverage Fragility
**Legend**: 羅兆輝 Law Siu-fai (HK$2B → 0, died 47)
**Trigger**: move uses counterparty credit/face/borrowed scale as primary enabler
**Failure mechanism**: when ONE counterparty loses confidence, the whole face/credit structure collapses instantly
**Detection signals**:
- "I don't have the capital but I know someone who..."
- Deal structure depends on a specific person's willingness
- Multi-party dependency where any single exit unwinds the position

## P2 — No-Floor Utilitarian EV
**Legend**: SBF (25-year sentence)
**Trigger**: reasoning uses expected-value math without a variance floor or Kelly criterion
**Failure mechanism**: unbounded position sizing, customer funds as "just numbers," ethics as PR
**Detection signals**:
- "The EV says..."
- "If I'm doing enough good, then..."
- Ethics framed as signaling, not constraint
- Willingness to "bet it all" justified by math

## P3 — Political Protection Expiry
**Legend**: Alvin Chau (18 years), 大劉 (HK fugitive)
**Trigger**: business model assumes current political weather is stable
**Failure mechanism**: political protection has a defined expiry date; when weather changes, legal exposure becomes terminal
**Detection signals**:
- "It's fine, [official/regulator] is on our side"
- Grey-zone operations dependent on non-enforcement
- Moves that are illegal or semi-legal but tolerated

## P4 — Grey Zone Monopoly
**Legend**: Alvin Chau (18 years)
**Trigger**: "we're the only ones who do this" where "this" is marginally legal
**Failure mechanism**: the monopoly only holds while regulators don't care; regulator arrival is binary, not gradual
**Detection signals**:
- Product is structurally unavailable elsewhere because of risk, not technical difficulty
- Margins are high specifically because others won't touch it
- "If not us, someone worse" — structural defense that doesn't hold in court

## P5 — Persecution Brand → Fraud
**Legend**: Miles Guo (9 of 12 federal counts)
**Trigger**: using perceived persecution as credibility that extracts value from followers
**Failure mechanism**: the loyalty-as-currency model requires ever-escalating grievance; rational audit becomes impossible within the community; external legal system eventually arrives
**Detection signals**:
- Converting audit requests into "proof of persecution"
- Financial contributions framed as political acts
- Apocalyptic urgency that bypasses rational risk assessment

## P6 — Perfectionism Isolation
**Legend**: Stephen Chow (<20 films in 30 years), Jobs
**Trigger**: excellence standard becomes a reason to delay, reduce collaborators, or isolate
**Failure mechanism**: the demand for excellence has an opportunity cost — fewer shots taken; relationships erode
**Detection signals**:
- Collaborators consistently leave citing interpersonal issues
- Output frequency drops without apparent improvement in quality
- "No one else can do this right"

## P7 — Delegation Becomes Absence
**Legend**: Branson blind-spot pattern
**Trigger**: delegation-first philosophy in a brand that needs the founder's living presence
**Failure mechanism**: delegation + adventure slides into delegation + absence; the brand becomes hollow
**Detection signals**:
- Founder appears only at launches and crises
- Culture references "when founder was more involved"
- Decisions slow because the founder is unreachable

## P8 — Network Becomes Patronage
**Legend**: Jiang Zemin Shanghai Clique pattern
**Trigger**: network-over-institution works for one generation, then corrodes the institutions
**Failure mechanism**: loyalty-based selection produces mediocre next-gen leadership; institutional capacity decays
**Detection signals**:
- Key roles filled by loyalty criterion, not competence
- Institutional processes bypassed for personal relationships
- "Second generation" struggles to reproduce founder's results

## P9 — Circle of Competence as Comfort Zone
**Legend**: Buffett blind-spot pattern
**Trigger**: "I don't understand it" rule applied to what should be learned, not avoided
**Failure mechanism**: genuine discipline degrades into convenient avoidance; misses transformative transitions
**Detection signals**:
- The excluded domain is growing faster than your domains for 3+ years
- Excluded domain produces more alpha than included ones
- Peers with adjacent circles are adapting; you are not

## P10 — Identity Tied to Performance
**Legend**: Patrick Tse at 89, Trump
**Trigger**: brand requires continuous visible performance; retirement = brand death
**Failure mechanism**: gap between legend and physical/cognitive reality widens; collaborators manage it, audience eventually sees through
**Detection signals**:
- Cannot step back without existential cost
- Performance calendar compressing but intensity not reducing
- Off-stage private state diverges sharply from on-stage persona

## P11 — Wrong-Prediction Frequency
**Legend**: Stephen Shiu 燈神 pattern
**Trigger**: making specific predictions at high frequency despite poor hit rate
**Failure mechanism**: each wrong call erodes credibility; framework (history pattern matching) not updated
**Detection signals**:
- Prediction output > prediction retrospection
- No visible tracking of own hit rate
- Audience defends you by saying "he wasn't serious"

## P12 — Trend-Following Whipsaw
**Legend**: 曹仁超 pattern
**Trigger**: momentum strategy without tail protection at inflection points
**Failure mechanism**: miss first AND last 20% of every move; cumulative drag from whipsaws at reversals
**Detection signals**:
- Stop-losses triggered repeatedly near tops/bottoms
- "Waiting for trend confirmation" at every cycle
- P&L positive in trending markets, negative in range-bound

## P13 — Personal Happiness Overrides Others' Autonomy
**Legend**: Cecil Chao (Gigi $1B bounty)
**Trigger**: treating personal optimization as a valid frame for decisions affecting others who didn't consent
**Failure mechanism**: the happiness-as-north-star framework has no awareness of consent; produces ethical harm disguised as personal fulfillment
**Detection signals**:
- Deciding something about another adult that requires their compliance
- Framing requests as personal goals rather than joint decisions
- Publicity/resources used to override another's expressed preference

## P14 — Law-As-Terrain
**Legend**: 大劉 (Macau conviction, HK fugitive)
**Trigger**: legal system treated as landscape to navigate rather than constraint to respect
**Failure mechanism**: arbitrage of legal ambiguity compounds exposure; eventually a jurisdiction forces clarity
**Detection signals**:
- "It's grey, not illegal"
- Cross-jurisdiction structures designed to create ambiguity
- Multiple counsel saying "probably fine" rather than "fine"

---

## Detection & Trigger Rules

1. **Auto-include as warning voice** when move matches ≥1 pattern
2. **Confidence levels**: HIGH (≥3 detection signals) | MEDIUM (2 signals) | LOW (1 signal, flagged as possible false positive per B7)
3. **Stacked patterns**: if 2+ patterns trigger, list all, rank by severity (P2, P5 > P1, P13 > P6, P9)
4. **False-positive check**: before firing warning, ask "does the structural mechanism actually apply here, or just superficial resemblance?"
5. **Already-in-pattern**: if Bernard's profile or decision log shows he's currently running a pattern, shift from "warning" to "exit-from-pattern" mode — route to Edwin Lee (exit) + relevant escape legend
6. **Version**: v1 2026-04-20. Review quarterly for AI-era / new failure modes.
