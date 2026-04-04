# Scoring Reference

AgentUX computes six component metrics plus a composite Agent Efficacy Score (AES). All scores are on a 0-100 scale.

## Discoverability Score

**What it measures:** How easily the agent identified relevant sections, commands, or tools on the surface.

**Formula:**

```
score = (discovered_relevant / total_relevant) * 80
      + first_discovery_speed_factor * 20
```

Where `first_discovery_speed_factor = max(0, 1 - steps_to_first_discovery / total_steps)`.

**Inputs:**
- `discovered_relevant` -- count of relevant affordances the agent discovered.
- `total_relevant` -- total relevant affordances on the surface.
- `steps_to_first_discovery` -- steps before the first relevant affordance was found.

**Interpretation:**
| Range  | Rating    | Meaning                                    |
|--------|-----------|--------------------------------------------|
| 90-100 | Excellent | Affordances are immediately visible         |
| 70-89  | Good      | Most affordances found without difficulty    |
| 40-69  | Fair      | Some affordances hard to find or ambiguous   |
| 0-39   | Poor      | Critical affordances hidden or unclear       |

**Applicable surfaces:** browser, markdown, CLI, MCP.

---

## Actionability Score

**What it measures:** Whether discovered elements can be acted upon without confusion.

**Formula:**

```
score = (successful_actions / total_actions) * 70
      + (correct_on_first_try / total_actions) * 30
```

**Inputs:**
- `successful_actions` -- actions that produced expected results.
- `total_actions` -- total actions attempted.
- `correct_on_first_try` -- actions that succeeded without retry.

**Interpretation:**
| Range  | Rating    | Meaning                                    |
|--------|-----------|--------------------------------------------|
| 90-100 | Excellent | Actions work as expected with clear feedback|
| 70-89  | Good      | Most actions succeed, minor friction         |
| 40-69  | Fair      | Frequent action failures or unclear feedback |
| 0-39   | Poor      | Surface actively hinders correct action      |

**Applicable surfaces:** browser, markdown, CLI, MCP.

---

## Recovery Score

**What it measures:** How well the surface helped the agent recover after confusion or error.

**Formula:**

```
score = max(0, 100 - (dead_ends * 15) - (unrecoverable_errors * 25)
                    + (helpful_error_messages * 10))
```

**Inputs:**
- `dead_ends` -- times the agent hit a dead end or had to backtrack.
- `unrecoverable_errors` -- 3+ consecutive failures without recovery.
- `helpful_error_messages` -- errors followed by a successful recovery step.

**Interpretation:**
| Range  | Rating    | Meaning                            |
|--------|-----------|------------------------------------|
| 90-100 | Excellent | Clear error recovery paths          |
| 70-89  | Good      | Most errors recoverable             |
| 40-69  | Fair      | Some dead ends without guidance     |
| 0-39   | Poor      | Errors are opaque, recovery hard    |

**Applicable surfaces:** browser, markdown, CLI, MCP.

---

## Efficiency Score

**What it measures:** How much unnecessary navigation, retries, or extra context was required.

**Formula:**

```
score = max(0, 100 - (excess_steps * 8) - (backtracks * 12)
                    - (redundant_reads * 5))
```

Where `excess_steps = max(0, actual_steps - optimal_steps)`.

**Inputs:**
- `actual_steps` -- steps taken to complete the task.
- `optimal_steps` -- estimated minimum steps (heuristic: `max(2, actual // 3)`).
- `backtracks` -- times the agent reversed direction.
- `redundant_reads` -- times the agent re-read the same content.

**Interpretation:**
| Range  | Rating    | Meaning                    |
|--------|-----------|----------------------------|
| 90-100 | Excellent | Near-optimal path           |
| 70-89  | Good      | Minor inefficiencies        |
| 40-69  | Fair      | Significant wasted effort   |
| 0-39   | Poor      | Excessive wandering         |

**Applicable surfaces:** browser, markdown, CLI, MCP.

---

## Documentation Clarity Score

**What it measures:** How clear the information structure and explanatory content were.

**Formula:**

```
score = (facts_extracted / expected_facts) * 60
      + (low_uncertainty_steps / total_steps) * 40
```

**Inputs:**
- `facts_extracted` -- useful facts the agent could extract from the surface.
- `expected_facts` -- facts needed for the task (heuristic: `max(3, total_steps // 2)`).
- `low_uncertainty_steps` -- steps where the agent's uncertainty was below 0.3.

**Interpretation:**
| Range  | Rating    | Meaning                                    |
|--------|-----------|--------------------------------------------|
| 90-100 | Excellent | Information is clear and well-structured     |
| 70-89  | Good      | Mostly clear with minor gaps                 |
| 40-69  | Fair      | Important information unclear or missing     |
| 0-39   | Poor      | Content is confusing or misleading           |

**Applicable surfaces:** browser, markdown, CLI, MCP.

---

## Tool Clarity Score

**What it measures:** How clear command/tool names, flags, descriptions, and examples are. CLI and MCP surfaces only.

**Formula:**

```
score = (correct_tool_selections / total_selections) * 50
      + arg_correctness_rate * 30
      + help_text_usefulness * 20
```

**Inputs:**
- `correct_tool_selections` -- times the right tool/command was chosen first.
- `total_selections` -- total tool/command selection attempts.
- `arg_correctness_rate` -- fraction of calls with correct arguments.
- `help_text_usefulness` -- whether consulting help led to a successful next action.

**Interpretation:**
| Range  | Rating    | Meaning                                |
|--------|-----------|----------------------------------------|
| 90-100 | Excellent | Tools are self-documenting              |
| 70-89  | Good      | Minor naming or schema issues           |
| 40-69  | Fair      | Confusing names or missing descriptions |
| 0-39   | Poor      | Tools are undiscoverable or misleading  |

**Applicable surfaces:** CLI, MCP only.

---

## Agent Efficacy Score (AES)

**What it measures:** Composite first-run usability for an AI agent. Weighted combination of all component scores.

**Formula (surface-dependent):**

For **browser** and **markdown** surfaces (no Tool Clarity):

```
AES = discoverability * 0.25
    + actionability   * 0.25
    + recovery        * 0.15
    + efficiency      * 0.15
    + doc_clarity     * 0.20
```

For **CLI** and **MCP** surfaces:

```
AES = discoverability * 0.20
    + actionability   * 0.20
    + recovery        * 0.15
    + efficiency      * 0.15
    + doc_clarity     * 0.15
    + tool_clarity    * 0.15
```

**Interpretation:**
| Range  | Rating    | Meaning                              |
|--------|-----------|--------------------------------------|
| 90-100 | Excellent | Excellent agent usability             |
| 70-89  | Good      | Usable with minor friction            |
| 40-69  | Fair      | Agent struggles significantly         |
| 0-39   | Poor      | Surface is effectively unusable       |
