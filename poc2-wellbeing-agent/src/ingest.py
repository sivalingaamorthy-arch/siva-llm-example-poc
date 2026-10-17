from pgvector import Vector

from src.db import article_count, connect
from src.errors import PocError
from src.openai_service import create_client, embed_texts


def ingest_articles() -> int:
    if article_count() == 0:
        raise PocError("Articles table is empty; initialize and seed the database first.")
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, title, body FROM articles ORDER BY id"
        ).fetchall()
    client = create_client()
    for start in range(0, len(rows), 64):
        batch = rows[start : start + 64]
        embeddings = embed_texts(client, [f"{title}\n\n{body}" for _, title, body in batch])
        with connect() as connection:
            for (article_id, _, _), embedding in zip(batch, embeddings, strict=True):
                connection.execute(
                    "UPDATE articles SET embedding = %s WHERE id = %s",
                    (Vector(embedding), article_id),
                )
    return len(rows)
