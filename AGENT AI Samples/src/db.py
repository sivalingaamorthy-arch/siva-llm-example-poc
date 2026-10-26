from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

from src.config import POC_ROOT, get_settings
from src.errors import PocError


@contextmanager
def connect(*, register_vector_type: bool = True) -> Iterator[psycopg.Connection]:
    try:
        with psycopg.connect(get_settings().database_url) as connection:
            if register_vector_type:
                register_vector(connection)
            yield connection
    except psycopg.Error as exc:
        raise PocError(
            "Cannot connect to POC2 PostgreSQL. Start its database with "
            "`docker compose up -d db` from poc2-wellbeing-agent/."
        ) from exc


def initialize_database() -> None:
    with connect(register_vector_type=False) as connection:
        connection.execute((POC_ROOT / "setup_db.sql").read_text(encoding="utf-8"))


def article_count() -> int:
    with connect() as connection:
        return int(connection.execute("SELECT count(*) FROM articles").fetchone()[0])
