from __future__ import annotations

from fastapi import APIRouter, Depends

from ..errors import problem
from ..models import Article, ArticleSummary
from ..repository import Repository, get_repository

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleSummary])
def list_articles(
    tag: str | None = None,
    category: str | None = None,
    repo: Repository = Depends(get_repository),
):
    return repo.list_articles(tag, category)


@router.get("/{article_id}", response_model=Article)
def get_article(article_id: str, repo: Repository = Depends(get_repository)):
    article = repo.get_article(article_id)
    if article is None:
        raise problem(404, "article-not-found", f"No article with id '{article_id}'.")
    return article
