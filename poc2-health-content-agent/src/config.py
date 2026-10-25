import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.errors import PocError

POC_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(POC_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_key: str | None
    generation_model: str
    embedding_model: str
    embedding_dimensions: int
    max_retries: int


def get_settings() -> Settings:
    try:
        dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        max_retries = int(os.getenv("MAX_RETRIES", "3"))
    except ValueError as exc:
        raise PocError("EMBEDDING_DIMENSIONS and MAX_RETRIES must be integers.") from exc
    if dimensions != 1536:
        raise PocError("EMBEDDING_DIMENSIONS must be 1536 for text-embedding-3-small.")
    if max_retries != 3:
        raise PocError("MAX_RETRIES is fixed at 3 for comparable agent runs.")
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://poc2:poc2_dev_only@localhost:5433/wellbeing_agent",
        ),
        api_key=os.getenv("OPENAI_API_KEY") or None,
        generation_model=os.getenv("GENERATION_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dimensions=dimensions,
        max_retries=max_retries,
    )
