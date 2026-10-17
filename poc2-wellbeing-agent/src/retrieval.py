from pgvector import Vector
from openai import OpenAI

from src.db import connect
from src.errors import PocError
from src.models import Article, Candidate, HealthReport
from src.openai_service import embed_texts


def retrieve_candidates(
    report: HealthReport,
    markers: list[str],
    category: str,
    exclude_ids: list[str],
    client: OpenAI,
    limit: int = 8,
    feedback: str = "",
) -> list[Candidate]:
    query = " ".join([*markers, report.notes, feedback]).strip() or "general well-being"
    vector = embed_texts(client, [query])[0]
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, body, category, condition_tags, intensity,
                   contraindications, source, approved, is_default, published_date,
                   1 - (embedding <=> %(embedding)s) AS similarity
            FROM articles
            WHERE approved = TRUE
              AND is_default = FALSE
              AND category = %(category)s
              AND embedding IS NOT NULL
              AND NOT (id = ANY(%(exclude_ids)s::text[]))
            ORDER BY embedding <=> %(embedding)s
            LIMIT %(limit)s
            """,
            {
                "embedding": Vector(vector),
                "category": category,
                "exclude_ids": exclude_ids,
                "limit": limit,
            },
        ).fetchall()
    candidates = []
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
        candidates.append(Candidate(article=article, similarity=float(row[11])))
    if not candidates:
        return []
    return candidates


def retrieve_for_report(
    report: HealthReport,
    markers: list[str],
    excluded_ids: list[str],
    client: OpenAI,
    feedback: str = "",
) -> tuple[list[Candidate], list[Candidate]]:
    physical = retrieve_candidates(
        report, markers, "physical", excluded_ids, client, feedback=feedback
    )
    mental = retrieve_candidates(
        report, markers, "mental", excluded_ids, client, feedback=feedback
    )
    return physical[:3], mental[:3]


def load_defaults() -> tuple[list[Candidate], list[Candidate]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, body, category, condition_tags, intensity,
                   contraindications, source, approved, is_default, published_date
            FROM articles
            WHERE approved = TRUE AND is_default = TRUE
            ORDER BY category, id
            """
        ).fetchall()
    by_category: dict[str, list[Candidate]] = {"physical": [], "mental": []}
    for row in rows:
        if row[3] not in by_category:
            continue
        article = Article(
            id=row[0], title=row[1], body=row[2], category=row[3],
            condition_tags=row[4], intensity=row[5],
            contraindications=row[6], source=row[7], approved=row[8],
            is_default=row[9], published_date=row[10],
        )
        by_category[row[3]].append(Candidate(article=article, similarity=0.0))
    if len(by_category["physical"]) != 1 or len(by_category["mental"]) != 1:
        raise PocError("Expected one approved default article in physical and mental categories.")
    return by_category["physical"], by_category["mental"]
