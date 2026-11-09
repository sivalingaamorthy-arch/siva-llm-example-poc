"""PreToolUse guard: deterministic policy that runs BEFORE any tool executes.

Principle: the system prompt *asks* the model to behave; a hook *enforces* it.
Here the guard applies the shared R2 safety rules (unapproved, contraindicated,
high intensity with hypertension) to every save_recommendation call.

Note the guard derives markers from the report itself. It never trusts the
model's own description of the user's conditions.
"""

from __future__ import annotations

from typing import Any

from . import sample_data

SERVER = "health"
SEARCH_TOOL = f"mcp__{SERVER}__search_articles"
SAVE_TOOL = f"mcp__{SERVER}__save_recommendation"
ALLOWED_TOOLS = {SEARCH_TOOL, SAVE_TOOL}


def evaluate(tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str]:
    """Return (allowed, reason). Pure function so it is easy to test and reuse."""
    if tool_name not in ALLOWED_TOOLS:
        return False, f"Tool '{tool_name}' is not on this agent's allowlist."

    if tool_name == SAVE_TOOL:
        report_id = tool_input.get("report_id", "")
        if report_id not in sample_data.REPORT_FILES:
            return False, f"Unknown report_id '{report_id}'. Use the id given in the request."
        article_id = tool_input.get("article_id", "")
        article = sample_data.article(article_id)
        if article is None:
            return False, (
                f"Article '{article_id}' does not exist. Call search_articles "
                "and use an id from its results."
            )
        violations = sample_data.safety_violations(
            article, sample_data.markers(sample_data.report(report_id))
        )
        if violations:
            return False, (
                f"Article '{article_id}' is unsafe for {report_id}: {'; '.join(violations)}. "
                "Choose a different, lower-intensity article."
            )
        if not tool_input.get("reason", "").strip():
            return False, "A non-empty 'reason' is required for audit purposes."

    return True, "ok"


async def pre_tool_use_guard(
    input_data: dict[str, Any], tool_use_id: str | None, context: Any
) -> dict[str, Any]:
    """Agent SDK hook callback. Signature: (input, tool_use_id, context)."""
    allowed, reason = evaluate(input_data["tool_name"], input_data.get("tool_input", {}))
    if allowed:
        return {}  # no opinion -> normal permission flow continues
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            # The reason is sent back to the model, so write it as guidance it
            # can act on, not as a bare "denied".
            "permissionDecisionReason": reason,
        }
    }
