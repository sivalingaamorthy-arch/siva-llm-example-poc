"""Data access over the repo's canonical sample data. Routes never read files."""

from __future__ import annotations

from . import sample_data
from .models import Article, Recommendation, RecommendationIn


class Repository:
    def __init__(self) -> None:
        self.articles: dict[str, Article] = {
            k: Article(**v) for k, v in sample_data.articles().items()
        }
        self.recommendations: list[Recommendation] = []

    def list_articles(self, tag: str | None = None, category: str | None = None) -> list[Article]:
        items = [a for a in self.articles.values() if not a.is_default]
        if tag:
            items = [a for a in items if tag in a.condition_tags]
        if category:
            items = [a for a in items if a.category == category]
        return items

    def get_article(self, article_id: str) -> Article | None:
        return self.articles.get(article_id)

    def report_markers(self, report_id: str) -> list[str]:
        return sample_data.markers(sample_data.report(report_id))

    def safety_violations(self, article: Article, markers: list[str]) -> list[str]:
        return sample_data.safety_violations(article.model_dump(), markers)

    def add_recommendation(self, rec: RecommendationIn, markers: list[str]) -> Recommendation:
        saved = Recommendation(
            id=len(self.recommendations) + 1, report_markers=markers, **rec.model_dump()
        )
        self.recommendations.append(saved)
        return saved


_repo: Repository | None = None


def get_repository() -> Repository:
    """FastAPI dependency; override in tests with app.dependency_overrides."""
    global _repo
    if _repo is None:
        _repo = Repository()
    return _repo
