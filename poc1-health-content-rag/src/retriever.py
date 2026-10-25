from pgvector import Vector
from openai import OpenAI

from src.config import get_settings
from src.db import connect
from src.errors import PocError
from src.models import Article, HealthReport, Recommendation
from src.openai_client import embed_texts

RETRIEVAL_SQL = """
    SELECT id, title, body, category, condition_tags, intensity,
           contraindications, source, approved, is_default, published_date,
           1 - (embedding <=> %(embedding)s) AS similarity
    FROM articles
    WHERE approved = TRUE
      AND is_default = FALSE
      AND category = %(category)s
      AND embedding IS NOT NULL
      AND NOT (contraindications && %(markers)s::text[])
      AND NOT (
          %(has_hypertension)s
          AND category = 'physical'
          AND intensity = 'high'
      )
    ORDER BY embedding <=> %(embedding)s
    LIMIT 3
"""


def is_safe_candidate(article: Article, markers: list[str]) -> bool:
    if not article.approved or article.is_default:
        return False
    if set(article.contraindications).intersection(markers):
        return False
    if "hypertension" in markers and article.category == "physical":
        return article.intensity != "high"
    return True


def _recommendations_for_category(
    report: HealthReport,
    markers: list[str],
    category: str,
    client: OpenAI,
) -> list[Recommendation]:
    settings = get_settings()
    query = " ".join([*markers, report.notes]).strip()
    vector = embed_texts(client, [query or "general well-being"], settings.embedding_model)[0]
    if len(vector) != settings.embedding_dimensions:
        raise PocError(
            "Embedding API returned an unexpected vector dimension; check the "
            "configured embedding model and database schema."
        )
    with connect() as connection:
        rows = connection.execute(
            RETRIEVAL_SQL,
            {
                "embedding": Vector(vector),
                "markers": markers,
                "has_hypertension": "hypertension" in markers,
                "category": category,
            },
        ).fetchall()
    recommendations: list[Recommendation] = []
    for row in rows:
        article = Article(
            id=row[0],
            title=row[1],
            body=row[2],
            category=row[3],
            condition_tags=row[4],
            intensity=row[5],
            contraindications=row[6],
            source=row[7],
            approved=row[8],
            is_default=row[9],
            published_date=row[10],
        )
        if is_safe_candidate(article, markers):
            recommendations.append(Recommendation(article=article, similarity=float(row[11])))
    return recommendations


def retrieve_for_report(
    report: HealthReport, markers: list[str], client: OpenAI
) -> tuple[list[Recommendation], list[Recommendation]]:
    physical = _recommendations_for_category(report, markers, "physical", client)
    mental = _recommendations_for_category(report, markers, "mental", client)
    return physical, mental
