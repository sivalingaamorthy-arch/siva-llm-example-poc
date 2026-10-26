from src.config import SAMPLE_DATA_ROOT
from src.loader import load_report
from src.models import Article, Candidate
from src.report_parser import parse_report
from src.rules import validate_rules

def candidate(
    article_id: str,
    category: str,
    *,
    intensity: str = "low",
    contraindications: list[str] | None = None,
    approved: bool = True,
) -> Candidate:
    return Candidate(
        article=Article(
            id=article_id,
            title=article_id,
            body="Synthetic educational content.",
            category=category,
            condition_tags=[],
            intensity=intensity,
            contraindications=contraindications or [],
            source="vendor",
            approved=approved,
            is_default=False,
            published_date="2026-01-15",
        ),
        similarity=0.5,
    )


def test_marker_parser_extracts_safety_markers_and_unmatched_postpartum():
    r2 = load_report(SAMPLE_DATA_ROOT / "reports" / "report2_safety_trap.json")
    r3 = load_report(SAMPLE_DATA_ROOT / "reports" / "report3_content_gap.json")
    assert parse_report(r2) == (["hypertension", "prediabetes"], [])
    assert parse_report(r3) == (["poor_sleep"], ["postpartum"])


def test_rules_reject_hypertension_contraindication_and_high_intensity():
    report = load_report(SAMPLE_DATA_ROOT / "reports" / "report2_safety_trap.json")
    physical = [
        candidate("p1", "physical", intensity="high"),
        candidate("p2", "physical", contraindications=["hypertension"]),
        candidate("p3", "physical"),
    ]
    mental = [candidate(f"m{i}", "mental") for i in range(3)]
    verdict = validate_rules(
        report, ["hypertension", "prediabetes"], [], physical, mental
    )
    assert verdict.verdict == "fail"
    assert {"p1", "p2"}.issubset(verdict.rejected_ids)
    assert "contraindicated" in verdict.feedback


def test_unmatched_topic_fails_closed_for_fallback():
    report = load_report(SAMPLE_DATA_ROOT / "reports" / "report3_content_gap.json")
    physical = [candidate(f"p{i}", "physical") for i in range(3)]
    mental = [candidate(f"m{i}", "mental") for i in range(3)]
    verdict = validate_rules(report, ["poor_sleep"], ["postpartum"], physical, mental)
    assert verdict.verdict == "fail"
    assert verdict.uncovered_topics == ["postpartum"]


def test_snapshot_has_33_articles_and_fictional_insurer():
    import json

    records = json.loads((SAMPLE_DATA_ROOT / "articles.json").read_text())
    assert len(records) == 33
    assert {record["source"] for record in records} == {"vendor", "Everwell"}
    assert sum(record["is_default"] for record in records) == 3
    assert not any("postpartum" in record["body"].lower() for record in records)
