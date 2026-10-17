from datetime import UTC, datetime
from pathlib import Path

from src.models import Article, Recommendation
from src.pipeline import load_report, run_recommendation, save_result

ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_result_and_output_use_shared_report_pipeline(monkeypatch, tmp_path):
    article = Article(
        id="physical-test",
        title="A safe article",
        body="Educational article content.",
        category="physical",
        condition_tags=["general"],
        intensity="low",
        contraindications=[],
        source="vendor",
        approved=True,
        is_default=False,
        published_date="2026-01-15",
    )
    recommendation = Recommendation(article=article, similarity=0.82)
    monkeypatch.setattr("src.pipeline.create_client", lambda settings: object())
    monkeypatch.setattr(
        "src.pipeline.retrieve_for_report",
        lambda report, markers, client: ([recommendation], []),
    )
    monkeypatch.setattr(
        "src.pipeline.generate_summary",
        lambda report, markers, physical, mental, client: "Grounded summary [physical-test].",
    )
    monkeypatch.setattr("src.pipeline.OUTPUT_DIR", tmp_path)

    report = load_report(ROOT / "reports" / "report1_happy_path.json")
    result = run_recommendation(report)
    output_path = save_result(result)

    assert result.report_id == "R1"
    assert result.markers == ["high_bmi", "poor_sleep", "sedentary", "stress"]
    assert result.physical[0].similarity == 0.82
    assert result.summary.endswith("[physical-test].")
    assert output_path == tmp_path / "R1.json"
    assert '"embedding_model": "text-embedding-3-small"' in output_path.read_text()
