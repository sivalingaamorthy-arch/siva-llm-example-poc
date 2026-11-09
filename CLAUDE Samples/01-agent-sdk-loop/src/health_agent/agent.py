"""Agent SDK version: the SDK runs the loop; we supply tools, guard and limits.

Run:  python -m health_agent.agent R2      (R1 | R2 | R3 from the shared sample data)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from . import catalog, sample_data
from .guard import ALLOWED_TOOLS, SERVER, pre_tool_use_guard

MAX_TURNS = int(os.getenv("MAX_TURNS", "6"))
MODEL = os.getenv("CLAUDE_MODEL", "sonnet")

SYSTEM_PROMPT = """You recommend health-content articles for a synthetic health report.
Goal: recommend ONE physical-activity article that fits the report and save it.
1. Call search_articles with keywords from the report (you may search more than once).
2. Choose the best match and call save_recommendation with the report_id and a one-sentence reason.
3. Reply with the title and why it fits. Do not give medical advice.
If a tool call is denied, read the reason and adapt; do not retry the same call."""


def _text(payload: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@tool(
    "search_articles",
    "Keyword search over the health-content catalog. Returns id, title, category, "
    "condition_tags and intensity. Use short keyword queries such as 'fitness walking'.",
    {"query": str},
)
async def search_articles_tool(args: dict) -> dict:
    results = catalog.search_articles(args["query"])
    if not results:
        return {
            "content": [{"type": "text", "text": "No matches. Try broader keywords."}],
            "is_error": True,
        }
    return _text(results)


@tool(
    "save_recommendation",
    "Persist one article recommendation for a user. Side effect: writes to the "
    "recommendations outbox. Only call after search_articles.",
    {"report_id": str, "article_id": str, "reason": str},
)
async def save_recommendation_tool(args: dict) -> dict:
    record = catalog.save_recommendation(args["report_id"], args["article_id"], args["reason"])
    return _text({"saved": True, **record})


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name=SERVER, tools=[search_articles_tool, save_recommendation_tool]
    )
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={SERVER: server},
        tools=[],                         # no built-in tools (Bash, Read, ...)
        allowed_tools=sorted(ALLOWED_TOOLS),  # auto-approve only our two tools
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[pre_tool_use_guard])]},
        max_turns=MAX_TURNS,              # hard stop for runaway loops
        max_budget_usd=0.25,              # and a cost ceiling
        setting_sources=[],               # ignore user/project settings for reproducibility
    )


def build_prompt(report_id: str) -> str:
    report = sample_data.report(report_id)
    return f"report_id={report_id}\nSynthetic health report:\n{json.dumps(report, indent=2)}"


async def run(report_id: str) -> int:
    prompt = build_prompt(report_id)
    async for message in query(prompt=prompt, options=build_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"\n[assistant] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[tool_use] {block.name} {json.dumps(block.input)}")
        elif isinstance(message, ResultMessage):
            print(
                f"\n[result] subtype={message.subtype} turns={message.num_turns} "
                f"cost=${message.total_cost_usd or 0:.4f}"
            )
            if message.permission_denials:
                print(f"[result] guard denials: {len(message.permission_denials)}")
            if message.subtype == "error_max_turns":
                print(f"[result] stopped at MAX_TURNS={MAX_TURNS}; returning a safe fallback.")
                return 2
            return 1 if message.is_error else 0
    return 1


def main() -> None:
    report_id = sys.argv[1] if len(sys.argv) > 1 else "R2"
    raise SystemExit(asyncio.run(run(report_id)))


if __name__ == "__main__":
    main()
