from __future__ import annotations

from fastapi import APIRouter, Depends, status

from ..errors import problem
from ..models import Recommendation, RecommendationIn
from ..repository import Repository, get_repository

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=Recommendation, status_code=status.HTTP_201_CREATED)
def create_recommendation(body: RecommendationIn, repo: Repository = Depends(get_repository)):
    article = repo.get_article(body.article_id)
    if article is None:
        raise problem(404, "article-not-found", f"No article with id '{body.article_id}'.")
    # Safety guard (see .claude/rules/safety-content.md): the shared R2 rules,
    # evaluated against markers derived from the report, never from the request.
    markers = repo.report_markers(body.report_id)
    violations = repo.safety_violations(article, markers)
    if not article.approved:
        raise problem(422, "article-not-approved", f"'{article.id}' is not approved.")
    if violations:
        raise problem(422, "unsafe-for-report", "; ".join(violations))
    return repo.add_recommendation(body, markers)
