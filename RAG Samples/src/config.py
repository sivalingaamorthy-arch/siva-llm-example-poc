import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.errors import PocError

POC_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(POC_ROOT / ".env")
SAMPLE_DATA_ROOT = Path(
    os.getenv(
        "HEALTH_CONTENT_SAMPLE_DATA",
        str(POC_ROOT.parent / "Sample-Data-Health-Content" / "sample-data"),
    )
).resolve()


def resolve_report_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    candidates = [POC_ROOT / path, SAMPLE_DATA_ROOT / path]
    if path.parent == Path("."):
        candidates.append(SAMPLE_DATA_ROOT / "reports" / path)
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str | None
    generation_model: str
    embedding_model: str
    embedding_dimensions: int


def get_settings() -> Settings:
    try:
        dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
    except ValueError as exc:
        raise PocError("EMBEDDING_DIMENSIONS must be the integer 1536.") from exc
    if dimensions != 1536:
        raise PocError(
            "EMBEDDING_DIMENSIONS must be 1536 for the configured "
            "text-embedding-3-small model and database schema."
        )
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://poc1:poc1_dev_only@localhost:5432/wellbeing_rag",
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        generation_model=os.getenv("GENERATION_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dimensions=dimensions,
    )
