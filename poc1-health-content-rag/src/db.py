from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

from src.config import POC_ROOT, get_settings
from src.errors import DatabaseError


@contextmanager
def connect(*, register_vector_type: bool = True) -> Iterator[psycopg.Connection]:
    try:
        with psycopg.connect(get_settings().database_url) as connection:
            if register_vector_type:
                register_vector(connection)
            yield connection
    except psycopg.Error as exc:
        raise DatabaseError(
            "Cannot use PostgreSQL. Start the Codespaces database with "
            "`docker compose up -d db`, then check DATABASE_URL."
        ) from exc


def initialize_database() -> None:
    schema = (POC_ROOT / "setup_db.sql").read_text(encoding="utf-8")
    with connect(register_vector_type=False) as connection:
        connection.execute(schema)
    print("Database schema and pgvector extension are ready.")


def article_count() -> int:
    with connect() as connection:
        row = connection.execute("SELECT count(*) FROM articles").fetchone()
    return int(row[0])
