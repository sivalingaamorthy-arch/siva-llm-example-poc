import json
from pathlib import Path

from pydantic import ValidationError

from src.config import POC_ROOT
from src.db import connect
from src.errors import PocError
from src.models import Article, HealthReport


def seed_articles() -> int:
    path = POC_ROOT / "data" / "articles.json"
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
        articles = [Article.model_validate(record) for record in records]
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise PocError(f"Cannot load validated article data: {exc}") from exc
    if len(articles) != 33:
        raise PocError(f"Expected 33 article records; found {len(articles)}.")
    with connect() as connection:
        for article in articles:
            connection.execute(
                """
                INSERT INTO articles (
                    id, title, body, category, condition_tags, intensity,
                    contraindications, source, approved, is_default, published_date
                ) VALUES (
                    %(id)s, %(title)s, %(body)s, %(category)s, %(condition_tags)s,
                    %(intensity)s, %(contraindications)s, %(source)s, %(approved)s,
                    %(is_default)s, %(published_date)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    body = EXCLUDED.body,
                    category = EXCLUDED.category,
                    condition_tags = EXCLUDED.condition_tags,
                    intensity = EXCLUDED.intensity,
                    contraindications = EXCLUDED.contraindications,
                    source = EXCLUDED.source,
                    approved = EXCLUDED.approved,
                    is_default = EXCLUDED.is_default,
                    published_date = EXCLUDED.published_date
                """,
                article.model_dump(),
            )
    return len(articles)


def load_report(path: Path) -> HealthReport:
    try:
        return HealthReport.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise PocError(f"Cannot load valid report at {path}: {exc}") from exc
