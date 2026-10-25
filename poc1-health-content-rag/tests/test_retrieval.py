from pathlib import Path

from src.models import Article
from src.report_parser import parse_report
from src.retriever import RETRIEVAL_SQL, is_safe_candidate
from src.pipeline import load_report
from src.vendor_loader import load_snapshot

ROOT = Path(__file__).resolve().parents[1]


def test_r2_has_hypertension_and_prediabetes_markers():
    report = load_report(ROOT / "reports" / "report2_safety_trap.json")
    assert parse_report(report) == ["hypertension", "prediabetes"]


def test_sql_applies_approval_default_contraindication_and_intensity_filters():
    assert "approved = TRUE" in RETRIEVAL_SQL
    assert "is_default = FALSE" in RETRIEVAL_SQL
    assert "contraindications &&" in RETRIEVAL_SQL
    assert "intensity = 'high'" in RETRIEVAL_SQL
    assert "LIMIT 3" in RETRIEVAL_SQL


def test_safety_guard_rejects_unsafe_candidates():
    article_data = load_snapshot()[7].model_copy()
    assert article_data.intensity == "high"
    assert not is_safe_candidate(article_data, ["hypertension"])
    assert not is_safe_candidate(article_data.model_copy(update={"approved": False}), [])
    assert not is_safe_candidate(
        article_data.model_copy(update={"is_default": True, "intensity": "low"}),
        [],
    )


def test_snapshot_contains_33_valid_articles_and_word_counts():
    articles = load_snapshot()
    assert len(articles) == 33
    assert {article.category for article in articles} == {"physical", "mental", "wellbeing"}
    assert sum(not article.approved for article in articles) == 3
    assert sum(article.is_default for article in articles) == 3
    assert all(150 <= len(article.body.split()) <= 300 for article in articles)
    assert sum(
        article.category == "physical"
        and article.intensity == "high"
        and article.contraindications == ["hypertension"]
        for article in articles
    ) == 2
    assert not any("postpartum" in article.body.lower() for article in articles)
