"""The same agent, with the loop written out by hand on the Messages API.

Why this file exists: the Agent SDK hides the loop. Writing it once makes the
contract obvious:

    while True:
        response = model(messages, tools)
        if stop_reason == "tool_use":  run tools -> append tool_result -> continue
        if stop_reason == "end_turn":  done
        anything else (max_tokens, refusal, ...): stop and handle explicitly
        turn counter > MAX_TURNS: stop, never "just one more"

Anti-patterns this avoids: parsing the assistant's text to decide whether it is
"done", and using an iteration cap as the *primary* stop condition.

Run:  python -m health_agent.manual_loop R2
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

from . import catalog
from .agent import MAX_TURNS, SYSTEM_PROMPT, build_prompt
from .guard import SAVE_TOOL, SEARCH_TOOL, evaluate

MODEL = os.getenv("CLAUDE_MODEL_ID", "claude-sonnet-5-5")

# Same names the SDK version exposes, so the guard logic is shared verbatim.
TOOLS = [
    {
        "name": SEARCH_TOOL,
        "description": "Keyword search over the health-content catalog. Returns id, "
        "title, category, condition_tags and intensity.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": SAVE_TOOL,
        "description": "Persist one article recommendation for a user. Side effect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "report_id": {"type": "string", "enum": ["R1", "R2", "R3"]},
                "article_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["report_id", "article_id", "reason"],
        },
    },
]


@dataclass
class LoopResult:
    stop: str                 # "end_turn" | "max_turns" | other stop_reason
    turns: int
    final_text: str = ""
    denials: list[str] = field(default_factory=list)


def execute_tool(name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
    """Run guard, then tool. Returns (content, is_error)."""
    allowed, reason = evaluate(name, tool_input)  # the "PreToolUse hook"
    if not allowed:
        return f"DENIED by policy: {reason}", True
    if name == SEARCH_TOOL:
        results = catalog.search_articles(tool_input["query"])
        if not results:
            return "No matches. Try broader keywords.", True
        return json.dumps(results), False
    if name == SAVE_TOOL:
        record = catalog.save_recommendation(**tool_input)
        return json.dumps({"saved": True, **record}), False
    return f"Unknown tool {name}", True


def run_loop(client: Any, user_message: str, max_turns: int = MAX_TURNS) -> LoopResult:
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    denials: list[str] = []

    for turn in range(1, max_turns + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        # Always append the assistant turn verbatim (tool_use ids must round-trip).
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = "".join(b.text for b in response.content if b.type == "text")
            return LoopResult("end_turn", turn, text, denials)

        if response.stop_reason != "tool_use":
            # max_tokens, refusal, pause_turn ... are NOT success. Surface them.
            return LoopResult(response.stop_reason, turn, "", denials)

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            content, is_error = execute_tool(block.name, block.input)
            if content.startswith("DENIED"):
                denials.append(content)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )
        # All results for this turn go back in ONE user message.
        messages.append({"role": "user", "content": tool_results})

    return LoopResult("max_turns", max_turns, "", denials)


def main() -> None:
    import anthropic

    report_id = sys.argv[1] if len(sys.argv) > 1 else "R2"
    result = run_loop(anthropic.Anthropic(), build_prompt(report_id))
    print(f"[stop={result.stop} turns={result.turns} denials={len(result.denials)}]")
    print(result.final_text or "(no final answer: see stop reason)")
    raise SystemExit(0 if result.stop == "end_turn" else 2)


if __name__ == "__main__":
    main()
