import json
from pathlib import Path

from pydantic import ValidationError

from src.config import SAMPLE_DATA_ROOT
from src.db import connect
from src.errors import PocError
from src.models import Article

ARTICLES_PATH = SAMPLE_DATA_ROOT / "articles.json"


def load_snapshot(path: Path = ARTICLES_PATH) -> list[Article]:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PocError(f"Cannot read article snapshot at {path}: {exc}") from exc
    if not isinstance(records, list):
        raise PocError("Article snapshot must contain a JSON array.")
    try:
        articles = [Article.model_validate(record) for record in records]
    except ValidationError as exc:
        raise PocError(f"Article snapshot failed schema validation: {exc}") from exc
    if len(articles) != 33:
        raise PocError(f"Expected 33 articles in the snapshot; found {len(articles)}.")
    return articles


def seed_database(path: Path = ARTICLES_PATH) -> int:
    articles = load_snapshot(path)
    with connect() as connection:
        for article in articles:
            connection.execute(
                """
                INSERT INTO articles (
                    id, title, body, category, condition_tags, intensity,
                    contraindications, source, approved, is_default,
                    published_date, embedding
                ) VALUES (
                    %(id)s, %(title)s, %(body)s, %(category)s, %(condition_tags)s,
                    %(intensity)s, %(contraindications)s, %(source)s, %(approved)s,
                    %(is_default)s, %(published_date)s, NULL
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
                    published_date = EXCLUDED.published_date,
                    embedding = NULL
                """,
                article.model_dump(),
            )
    return len(articles)
