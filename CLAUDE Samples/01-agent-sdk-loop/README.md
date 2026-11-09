# POC 5: Agent SDK loop with a PreToolUse guard

**Part of [CLAUDE Samples](../README.md) · AI learning journey**
A Claude Agent SDK agent with a full agentic loop, two tools, a `PreToolUse` guard and a turn limit.

Scenario: the repo's shared [health-content sample data](../../Sample-Data-Health-Content/README.md). Given synthetic report R1, R2 or R3, the agent searches the 33-article catalog and saves one recommendation. The **R2 safety rules** (no unapproved articles, nothing contraindicated by the report's markers, no high-intensity content with hypertension) are enforced in a hook, not in the prompt. R2's note *"Wants to get fitter quickly"* is the bait: search happily returns HIIT, and the guard stops it.

## What's inside

| Concept | Where | Notes |
|---|---|---|
| Agent loop (SDK-managed) | `src/health_agent/agent.py` | `query()` runs the loop; we read `AssistantMessage` / `ResultMessage` |
| Agent loop (hand-written) | `src/health_agent/manual_loop.py` | The same agent on the raw Messages API, branching on `stop_reason` |
| Tool 1, read-only | `search_articles` | Returns `is_error` with a hint when there are no matches |
| Tool 2, side effect | `save_recommendation` | Appends to `output/recommendations.jsonl` |
| `PreToolUse` guard | `src/health_agent/guard.py` | Applies the R2 rules from markers it derives from the report itself; also rejects unknown ids, empty reasons and non-allowlisted tools |
| Shared data access | `src/health_agent/sample_data.py` | Canonical catalog + reports; same marker thresholds as `RAG Samples/src/report_parser.py` |
| Turn limit | `max_turns=6` (+ `max_budget_usd`) | Handles `error_max_turns` explicitly |
| Tests (offline) | `tests/` | Fake client, so no API key is needed |

```
user ─▶ model ──stop_reason=tool_use──▶ PreToolUse guard ──allow──▶ tool ──▶ tool_result ─┐
          ▲                                   └──deny + reason (is_error) ──────────────────┤
          └─────────────────────────────────────────────────────────────────────────────────┘
        stop_reason=end_turn ─▶ answer          turns > MAX_TURNS ─▶ stop and fall back
```

## Principles to take away

1. **The loop terminates on `stop_reason`, not on text.** `tool_use` means continue and `end_turn` means done. Anything else (`max_tokens`, `refusal`, …) is surfaced and never treated as success. Don't parse "I'm done" out of the model's prose.
2. **The turn limit is a safety net, not the stop condition.** If you routinely hit `max_turns`, the tools or the prompt are wrong.
3. **Prompts ask; hooks enforce.** Anything with compliance weight goes in a deterministic `PreToolUse` hook. The deny reason goes back to the model, so write it as guidance it can act on.
4. **Defense in depth.** `tools=[]` removes the built-in tools, `allowed_tools` auto-approves only ours, and the guard still rejects anything off the allowlist.
5. **Keep business logic free of SDK code** (`catalog.py`). The SDK tools and the manual loop share it, and so do the tests.
6. **Never let the model describe the facts the guard checks.** The guard reads the report's markers itself; it doesn't trust a `conditions` argument the model could get wrong.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                   # offline, no key needed
# Run from this folder. Data is found by walking up to Sample-Data-Health-Content/;
# set HEALTH_CONTENT_SAMPLE_DATA to point elsewhere.

export ANTHROPIC_API_KEY=sk-ant-...
python -m health_agent.agent R1            # happy path
python -m health_agent.agent R2            # safety trap: watch the guard deny HIIT (physical-08/09)
python -m health_agent.manual_loop R2      # same agent, hand-written loop
MAX_TURNS=1 python -m health_agent.agent R1   # see the turn limit trip
```

The Agent SDK uses the bundled Claude Code CLI. `CLAUDE_MODEL` (an alias such as `sonnet`) sets the SDK model, and `CLAUDE_MODEL_ID` sets the model for the manual loop.

## Experiments to try

- Remove the guard from `build_options()` and run R2 a few times. Does the prompt alone keep HIIT out?
- Run R3 (the postpartum content gap). Does the agent admit nothing fits, or save the nearest neighbour?
- Change `permissionDecision` to `"ask"` or `"defer"` and see how the result message changes.
- Add a `PostToolUse` hook that strips `body` text from tool output to save tokens.

## MY EXPERIENCE
_Notes from running this: what surprised me, what I'd do differently in an enterprise build._
