from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .models import Problem

PROBLEM_BASE = "https://example.com/problems/"


def problem(status: int, slug: str, detail: str) -> HTTPException:
    """The only way routes should signal an error."""
    return HTTPException(
        status_code=status,
        detail=Problem(
            type=PROBLEM_BASE + slug, title=slug.replace("-", " "), status=status, detail=detail
        ).model_dump(),
    )


async def problem_handler(_: Request, exc: HTTPException) -> JSONResponse:
    body = exc.detail if isinstance(exc.detail, dict) else Problem(
        type=PROBLEM_BASE + "http-error", title="http error", status=exc.status_code,
        detail=str(exc.detail),
    ).model_dump()
    return JSONResponse(body, status_code=exc.status_code,
                        media_type="application/problem+json")
