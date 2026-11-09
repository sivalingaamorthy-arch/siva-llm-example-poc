from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ARTICLE_ID = r"^(physical|mental|wellbeing|default)-[a-z0-9-]+$"


class ArticleSummary(BaseModel):
    id: str
    title: str
    category: Literal["physical", "mental", "wellbeing"]
    condition_tags: list[str]
    intensity: Literal["low", "medium", "high"]
    approved: bool


class Article(ArticleSummary):
    """Mirrors Sample-Data-Health-Content/sample-data/articles.json."""

    body: str
    contraindications: list[str]
    source: str
    is_default: bool
    published_date: str


class RecommendationIn(BaseModel):
    report_id: Literal["R1", "R2", "R3"]
    article_id: str = Field(pattern=ARTICLE_ID)
    reason: str = Field(min_length=10, max_length=280)


class Recommendation(RecommendationIn):
    id: int
    report_markers: list[str]


class Problem(BaseModel):
    """RFC 9457-style error body. Every non-2xx response uses this shape."""

    type: str
    title: str
    status: int
    detail: str
