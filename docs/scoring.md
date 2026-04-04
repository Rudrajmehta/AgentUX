# Scoring Reference

AgentUX scores are designed to be **honest, strict, and actionable**. No free points. No inflated numbers. Every score reflects what the agent actually did, not what exists on the surface.

## Core Principles

1. **Scores reflect agent behavior, not surface inventory.** `surface.discover()` lists what's available — that's the denominator. Only affordances the agent INTERACTED with count.
2. **Shallow runs score low.** A 2-step run cannot prove usability. Scores are capped when sample size is too small.
3. **No untested capability gets credit.** If no errors occurred, Recovery is capped at 50 — you can't prove error handling without errors.
4. **Every score includes recommendations.** Scores tell you what to fix, not just what number you got.
5. **No score above 90 without thorough testing.** High scores require both depth (enough steps) and breadth (enough affordances tested).

---

## Metrics

### Discoverability (0-100)

**What it measures:** What fraction of available affordances did the agent actually interact with?

**How it's calculated:**
```
score = (interacted / total_relevant) * 100
```

- `interacted` = affordances the agent actually used (clicked, executed, called)
- `total_relevant` = all relevant affordances on the surface
- Penalty: if agent touched <20% and there are >3 affordances, capped at 40
- Bonus: +5 if first interaction happened in steps 1-2

**What a low score means:** The surface is hard to explore, or the agent didn't go deep enough.

---

### Actionability (0-100)

**What it measures:** Of the actions the agent attempted, how many worked?

**How it's calculated:**
```
success_pts    = (successful / total_actions) * 50
first_try_pts  = (first_try / total_actions) * 25
depth_bonus    = min(25, total_actions * 5)
score          = success_pts + first_try_pts + depth_bonus
```

- Capped at 60 when <3 actions tested (low confidence)
- 0 when no actions attempted

---

### Recovery (0-100)

**How it's calculated:**
```
If no errors occurred: score = 50 (untested, capped)
Otherwise: score = 100 - (dead_ends * 15) - (unrecoverable * 25) + (recovered * 10)
```

- Capped at 50 when no errors occurred (untested)

---

### Efficiency (0-100)

**How it's calculated:**
```
penalty = (backtracks * 12) + (redundant_reads * 8) + (wasted_steps * 8)
score = 100 - penalty
```

- Capped at 50 when <3 steps

---

### Documentation Clarity (0-100)

**How it's calculated:**
```
fact_pts    = min(50, (unique_facts / steps) * 25)
clarity_pts = clarity_ratio * 25
depth_pts   = min(25, steps * 5)
score       = fact_pts + clarity_pts + depth_pts
```

- Facts are deduplicated. Capped at 50 for <3 step runs.

---

### Tool Clarity (0-100) — CLI and MCP only

```
score = (correct / total) * 50 + arg_rate * 30 + help_factor * 20
```

- Capped at 50 when <3 tool invocations

---

### Agent Efficacy Score — AES (0-100)

Weighted composite of all metrics.

**Browser/Markdown weights:** Discoverability 25%, Actionability 25%, Recovery 15%, Efficiency 15%, Doc Clarity 20%

**CLI/MCP weights:** Discoverability 20%, Actionability 20%, Recovery 15%, Efficiency 15%, Doc Clarity 15%, Tool Clarity 15%

---

## Caps Summary

| Condition | Effect |
|-----------|--------|
| <3 steps | Efficiency, Doc Clarity capped at 50 |
| <3 actions | Actionability capped at 60 |
| <3 tool calls | Tool Clarity capped at 50 |
| <20% interaction | Discoverability capped at 40 |
| No errors | Recovery capped at 50 |
| 0 steps (infra fail) | All scores = 0 |

---

## Recommendations

Every metric produces actionable recommendations. Examples:

- "Agent only interacted with 2/26 affordances (8%) — 24 untested"
- "Only 2 actions tested — low confidence (capped at 60)"
- "No errors occurred — recovery untested (capped at 50)"
