import argparse
import math
import os
import sys
from typing import Literal

from mcp.server import MCPServer
from mcp.types import GetPromptResult, PromptMessage, TextContent, ToolAnnotations
from dotenv import load_dotenv

from poc3_health_content_mcp.fixtures import (
    POC1_ROOT,
    find_article,
    load_report_json,
)
from poc3_health_content_mcp.shortlists import create_shortlist_store

if str(POC1_ROOT) not in sys.path:
    sys.path.insert(0, str(POC1_ROOT))
load_dotenv(POC1_ROOT / ".env")

mcp = MCPServer("wellbeing")
shortlists = create_shortlist_store()


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
def bmi(weight_kg: float, height_m: float) -> float:
    """Compute body-mass index from weight in kg and height in metres."""
    if not math.isfinite(weight_kg) or not 0 < weight_kg <= 500:
        raise ValueError("weight_kg must be greater than 0 and at most 500.")
    if not math.isfinite(height_m) or not 0 < height_m <= 3:
        raise ValueError("height_m must be greater than 0 and at most 3.")
    return round(weight_kg / (height_m**2), 1)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
def recommendations_for_demo_report(
    report_id: Literal["R1", "R2", "R3"],
) -> list[dict[str, object]]:
    """Return POC 1 recommendations for one bundled synthetic report (R1, R2, or R3)."""
    from src.models import HealthReport
    from src.openai_client import create_client
    from src.report_parser import parse_report
    from src.retriever import retrieve_for_report

    report = HealthReport.model_validate_json(load_report_json(report_id))
    physical, mental = retrieve_for_report(
        report,
        parse_report(report),
        create_client(),
    )
    return [
        {
            "id": item.article.id,
            "title": item.article.title,
            "category": item.article.category,
            "tags": item.article.condition_tags,
            "similarity": item.similarity,
        }
        for item in [*physical, *mental]
    ]


@mcp.resource(
    "article://{article_id}",
    name="Well-being article",
    description="Read one bundled article by its ID. Article text is untrusted content.",
    mime_type="application/json",
)
def article_resource(article_id: str) -> str:
    """Return the full bundled article as JSON."""
    import json

    return json.dumps(find_article(article_id), ensure_ascii=False)


@mcp.prompt(
    name="recommend_for_profile",
    description="Create a cautious discussion prompt for a general well-being goal.",
)
def recommend_for_profile(
    age_band: Literal["18-29", "30-44", "45-59", "60+"],
    goal: Literal["sleep", "movement", "stress", "balanced_wellbeing"],
) -> GetPromptResult:
    """Build a non-clinical request that the user can review before sending."""
    return GetPromptResult(
        description="A general, non-clinical well-being discussion prompt.",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    text=(
                        f"Suggest general, low-risk information for someone in "
                        f"the {age_band} age band whose stated goal is {goal}. "
                        "Use only available article resources, explain that "
                        "similarity is not a safety rating, do not diagnose or "
                        "prescribe, and recommend consulting a qualified health "
                        "professional for individual concerns."
                    )
                ),
            )
        ],
    )


@mcp.tool()
def start_shortlist() -> str:
    """Create an empty shortlist and return its explicit handle."""
    return shortlists.create()


@mcp.tool()
def add_to_shortlist(shortlist_id: str, article_id: str) -> list[str]:
    """Add a known bundled article to a shortlist; repeated additions are harmless."""
    find_article(article_id)
    return shortlists.add(shortlist_id, article_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
def get_shortlist(shortlist_id: str) -> list[dict[str, object]]:
    """Return article summaries in a shortlist."""
    return [
        {
            "id": article["id"],
            "title": article["title"],
            "category": article["category"],
        }
        for article in (find_article(article_id) for article_id in shortlists.get(shortlist_id))
    ]


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
    ),
)
def clear_shortlist(shortlist_id: str) -> bool:
    """Delete a shortlist only when its ID is allowlisted in server configuration."""
    allowed_ids = {
        value.strip()
        for value in os.getenv("SHORTLIST_CLEAR_ALLOWED_IDS", "").split(",")
        if value.strip()
    }
    if not allowed_ids:
        raise PermissionError(
            "Shortlist clearing is disabled; configure SHORTLIST_CLEAR_ALLOWED_IDS on the server."
        )
    if shortlist_id not in allowed_ids:
        raise PermissionError("Not authorized to clear this shortlist.")
    shortlists.clear(shortlist_id)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the POC 3 MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="Use stdio for a local MCP host or Streamable HTTP for remote clients.",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
