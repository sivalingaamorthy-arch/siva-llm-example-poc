"""Health-content MCP server whose tools return structured errors.

Run over stdio:   health-content-mcp
Simulate outage:  HEALTH_MCP_FLAKY_CALLS=2 health-content-mcp   (first 2 calls fail transiently)
"""

from __future__ import annotations

import functools
import logging
import os
import re
import sys
from typing import Any, Callable

from mcp.server import MCPServer
from mcp_types import CallToolResult

from . import sample_data
from .errors import ErrorCategory, ToolFailure, error_result, ok_result

log = logging.getLogger("health_content_mcp")
ID_PATTERN = re.compile(r"^(physical|mental|wellbeing|default)-[a-z0-9-]+$")
SUMMARY_FIELDS = ("id", "title", "category", "condition_tags", "intensity", "approved")
REVIEWER_ROLES = {"editor", "clinician"}


class ArticleStore:
    def __init__(self, flaky_calls: int = 0) -> None:
        self._articles = sample_data.articles()  # canonical shared catalog
        self._flaky_remaining = flaky_calls
        self.flags: list[dict[str, Any]] = []

    def _backend(self) -> dict[str, dict]:
        """Stand-in for a real database / search call that can time out."""
        if self._flaky_remaining > 0:
            self._flaky_remaining -= 1
            raise ToolFailure(
                ErrorCategory.TRANSIENT,
                "BACKEND_TIMEOUT",
                "Content index did not respond in time.",
                retry_after_ms=500,
                suggestion="Retry the same call after the delay.",
            )
        return self._articles


def structured_errors(fn: Callable[..., CallToolResult]) -> Callable[..., CallToolResult]:
    """Convert ToolFailure -> isError result; convert crashes -> safe INTERNAL error.

    Without this, the SDK reports an unhandled exception to the model as a bare
    "Error executing tool X": no category, no retry hint. The agent can't tell
    a typo from an outage.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> CallToolResult:
        try:
            return fn(*args, **kwargs)
        except ToolFailure as failure:
            log.info("tool %s failed: %s", fn.__name__, failure.code)
            return error_result(failure)
        except Exception:  # noqa: BLE001 - deliberate catch-all at the boundary
            log.exception("tool %s crashed", fn.__name__)  # details stay in server logs
            return error_result(
                ToolFailure(
                    ErrorCategory.INTERNAL,
                    "INTERNAL_ERROR",
                    "The tool hit an unexpected error. This is not caused by your input.",
                    suggestion="Do not retry. Tell the user the content service is unavailable.",
                )
            )

    return wrapper


def _validate_id(article_id: str) -> None:
    if not ID_PATTERN.match(article_id or ""):
        raise ToolFailure(
            ErrorCategory.VALIDATION,
            "INVALID_ARTICLE_ID",
            f"'{article_id}' is not a valid article id.",
            suggestion="Ids look like 'physical-01'. Use an id returned by search_articles.",
            details={"field": "article_id", "pattern": ID_PATTERN.pattern},
        )


def build_server(store: ArticleStore | None = None, *, debug: bool = False) -> MCPServer:
    store = store or ArticleStore(int(os.getenv("HEALTH_MCP_FLAKY_CALLS", "0")))
    server = MCPServer("health-content")

    @server.tool(
        description=(
            "Keyword search over health-content articles. Returns a list of "
            "{id,title,category,condition_tags,intensity,approved}. An empty list is a valid answer, not an error."
        )
    )
    @structured_errors
    def search_articles(query: str, limit: int = 5) -> CallToolResult:
        if not query.strip():
            raise ToolFailure(
                ErrorCategory.VALIDATION, "EMPTY_QUERY", "query must not be empty.",
                suggestion="Pass 1-5 keywords, e.g. 'sleep stress'.",
                details={"field": "query"},
            )
        if not 1 <= limit <= 20:
            raise ToolFailure(
                ErrorCategory.VALIDATION, "LIMIT_OUT_OF_RANGE", "limit must be 1-20.",
                details={"field": "limit", "min": 1, "max": 20, "got": limit},
            )
        terms = [t for t in query.lower().replace("_", " ").split() if len(t) > 2]
        hits = []
        for a in store._backend().values():
            tags = " ".join(a["condition_tags"]).replace("_", " ")
            text = " ".join([a["title"], a["category"], tags, a["body"]]).lower()
            score = sum(text.count(t) for t in terms)
            if score:
                hits.append((score, a))
        hits.sort(key=lambda h: h[0], reverse=True)
        results = [
            {k: a[k] for k in SUMMARY_FIELDS} for _, a in hits[:limit]
        ]
        # Success with zero results is NOT an error: the search worked.
        return ok_result({"query": query, "count": len(results), "results": results})

    @server.tool(description="Fetch one article by id, including its body.")
    @structured_errors
    def get_article(article_id: str) -> CallToolResult:
        _validate_id(article_id)
        article = store._backend().get(article_id)
        if article is None:
            raise ToolFailure(
                ErrorCategory.NOT_FOUND, "ARTICLE_NOT_FOUND",
                f"No article with id '{article_id}'.",
                suggestion="Search again; the id may be stale.",
            )
        return ok_result({"article": article})

    @server.tool(
        description=(
            "Flag an article for content review. reviewer_role must be 'editor' or "
            "'clinician'. Only clinicians may flag articles that carry contraindications."
        )
    )
    @structured_errors
    def flag_article(article_id: str, reason: str, reviewer_role: str) -> CallToolResult:
        _validate_id(article_id)
        if reviewer_role not in REVIEWER_ROLES:
            raise ToolFailure(
                ErrorCategory.VALIDATION, "INVALID_ROLE",
                f"reviewer_role '{reviewer_role}' is not recognised.",
                details={"field": "reviewer_role", "allowed": sorted(REVIEWER_ROLES)},
            )
        article = store._backend().get(article_id)
        if article is None:
            raise ToolFailure(ErrorCategory.NOT_FOUND, "ARTICLE_NOT_FOUND",
                              f"No article with id '{article_id}'.")
        if article["contraindications"] and reviewer_role != "clinician":
            raise ToolFailure(
                ErrorCategory.PERMISSION, "CLINICIAN_REQUIRED",
                "Articles with contraindications can only be flagged by a clinician.",
                details={"contraindications": article["contraindications"]},
                suggestion="Escalate to the clinical review team; do not retry with another role.",
            )
        if any(f["article_id"] == article_id for f in store.flags):
            raise ToolFailure(
                ErrorCategory.BUSINESS, "ALREADY_FLAGGED",
                f"Article '{article_id}' already has an open review flag.",
                suggestion="Tell the user it is already under review.",
            )
        if len(reason.strip()) < 10:
            raise ToolFailure(
                ErrorCategory.VALIDATION, "REASON_TOO_SHORT",
                "reason must be at least 10 characters.", details={"field": "reason"},
            )
        flag = {"article_id": article_id, "reason": reason, "reviewer_role": reviewer_role}
        store.flags.append(flag)
        return ok_result({"flagged": True, **flag})

    if debug or os.getenv("HEALTH_MCP_DEBUG") == "1":

        @server.tool(description="Diagnostics only: always crashes, to show INTERNAL errors.")
        @structured_errors
        def debug_crash() -> CallToolResult:
            raise RuntimeError("db password=hunter2 leaked in a stack trace")

    return server


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)  # never log to stdout on stdio
    build_server().run("stdio")


if __name__ == "__main__":
    main()
