from pgvector import Vector

from src.config import get_settings
from src.db import connect, article_count
from src.errors import PocError
from src.openai_client import create_client, embed_texts


def ingest_articles() -> int:
    settings = get_settings()
    count = article_count()
    if count == 0:
        raise PocError("The articles table is empty. Run `python -m src.rag_app --seed` first.")
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, title, body FROM articles ORDER BY id"
        ).fetchall()
    client = create_client(settings)
    updated = 0
    for start in range(0, len(rows), 64):
        batch = rows[start : start + 64]
        texts = [f"{title}\n\n{body}" for _, title, body in batch]
        vectors = embed_texts(client, texts, settings.embedding_model)
        if len(vectors) != len(batch) or any(
            len(vector) != settings.embedding_dimensions for vector in vectors
        ):
            raise PocError(
                "Embedding API returned an unexpected count or vector dimension; "
                "check EMBEDDING_MODEL and EMBEDDING_DIMENSIONS."
            )
        with connect() as connection:
            for (article_id, _, _), vector in zip(batch, vectors, strict=True):
                connection.execute(
                    "UPDATE articles SET embedding = %s WHERE id = %s",
                    (Vector(vector), article_id),
                )
        updated += len(batch)
    return updated
