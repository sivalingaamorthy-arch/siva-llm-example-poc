import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PROJECT_ROOT.parent
POC1_ROOT = Path(
    os.environ.get(
        "POC1_ROOT",
        str(REPOSITORY_ROOT / "RAG Samples"),
    )
).resolve()
SAMPLE_DATA_ROOT = Path(
    os.environ.get(
        "HEALTH_CONTENT_SAMPLE_DATA",
        str(REPOSITORY_ROOT / "Sample-Data-Health-Content" / "sample-data"),
    )
).resolve()
REPORT_FILES = {
    "R1": SAMPLE_DATA_ROOT / "reports" / "report1_happy_path.json",
    "R2": SAMPLE_DATA_ROOT / "reports" / "report2_safety_trap.json",
    "R3": SAMPLE_DATA_ROOT / "reports" / "report3_content_gap.json",
}
ARTICLE_FILE = SAMPLE_DATA_ROOT / "articles.json"


def load_report_json(report_id: str) -> str:
    return REPORT_FILES[report_id].read_text(encoding="utf-8")


def load_articles() -> list[dict[str, Any]]:
    with ARTICLE_FILE.open(encoding="utf-8") as article_file:
        articles = json.load(article_file)
    if not isinstance(articles, list):
        raise ValueError(f"Expected an article list in {ARTICLE_FILE}.")
    return articles


def find_article(article_id: str) -> dict[str, Any]:
    for article in load_articles():
        if article.get("id") == article_id:
            return article
    raise ValueError(f"Unknown article_id: {article_id}")
