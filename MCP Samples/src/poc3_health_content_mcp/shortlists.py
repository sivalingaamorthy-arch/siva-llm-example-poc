import os
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

import psycopg


class ShortlistStore(Protocol):
    def create(self) -> str: ...

    def add(self, shortlist_id: str, article_id: str) -> list[str]: ...

    def get(self, shortlist_id: str) -> list[str]: ...

    def clear(self, shortlist_id: str) -> None: ...


class MemoryShortlistStore:
    def __init__(self) -> None:
        self._shortlists: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        shortlist_id = str(uuid.uuid4())
        with self._lock:
            self._shortlists[shortlist_id] = []
        return shortlist_id

    def add(self, shortlist_id: str, article_id: str) -> list[str]:
        with self._lock:
            articles = self._require(shortlist_id)
            if article_id not in articles:
                articles.append(article_id)
            return list(articles)

    def get(self, shortlist_id: str) -> list[str]:
        with self._lock:
            return list(self._require(shortlist_id))

    def clear(self, shortlist_id: str) -> None:
        with self._lock:
            self._require(shortlist_id)
            del self._shortlists[shortlist_id]

    def _require(self, shortlist_id: str) -> list[str]:
        try:
            return self._shortlists[shortlist_id]
        except KeyError as exc:
            raise ValueError(f"Unknown shortlist_id: {shortlist_id}") from exc


class PostgresShortlistStore:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/wellbeing_rag",
        )

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(self._database_url) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_shortlists (
                    shortlist_id UUID PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mcp_shortlist_articles (
                    shortlist_id UUID NOT NULL REFERENCES mcp_shortlists
                        (shortlist_id) ON DELETE CASCADE,
                    article_id TEXT NOT NULL,
                    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (shortlist_id, article_id)
                )
                """
            )
            yield connection

    def create(self) -> str:
        shortlist_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO mcp_shortlists (shortlist_id) VALUES (%s)",
                (uuid.UUID(shortlist_id),),
            )
        return shortlist_id

    def add(self, shortlist_id: str, article_id: str) -> list[str]:
        parsed_id = self._parse_id(shortlist_id)
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM mcp_shortlists WHERE shortlist_id = %s",
                (parsed_id,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"Unknown shortlist_id: {shortlist_id}")
            connection.execute(
                """
                INSERT INTO mcp_shortlist_articles (shortlist_id, article_id)
                VALUES (%s, %s)
                ON CONFLICT (shortlist_id, article_id) DO NOTHING
                """,
                (parsed_id, article_id),
            )
            rows = connection.execute(
                "SELECT article_id FROM mcp_shortlist_articles "
                "WHERE shortlist_id = %s ORDER BY added_at, article_id",
                (parsed_id,),
            ).fetchall()
        return [row[0] for row in rows]

    def get(self, shortlist_id: str) -> list[str]:
        parsed_id = self._parse_id(shortlist_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT article_id FROM mcp_shortlist_articles "
                "WHERE shortlist_id = %s ORDER BY added_at, article_id",
                (parsed_id,),
            ).fetchall()
            if not rows and connection.execute(
                "SELECT 1 FROM mcp_shortlists WHERE shortlist_id = %s",
                (parsed_id,),
            ).fetchone() is None:
                raise ValueError(f"Unknown shortlist_id: {shortlist_id}")
        return [row[0] for row in rows]

    def clear(self, shortlist_id: str) -> None:
        parsed_id = self._parse_id(shortlist_id)
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM mcp_shortlists WHERE shortlist_id = %s",
                (parsed_id,),
            )
            if result.rowcount == 0:
                raise ValueError(f"Unknown shortlist_id: {shortlist_id}")

    @staticmethod
    def _parse_id(shortlist_id: str) -> uuid.UUID:
        try:
            return uuid.UUID(shortlist_id)
        except ValueError as exc:
            raise ValueError("shortlist_id must be a UUID.") from exc


def create_shortlist_store() -> ShortlistStore:
    mode = os.getenv("SHORTLIST_STORAGE", "memory").strip().lower()
    if mode == "memory":
        return MemoryShortlistStore()
    if mode == "postgres":
        return PostgresShortlistStore()
    raise ValueError("SHORTLIST_STORAGE must be 'memory' or 'postgres'.")
