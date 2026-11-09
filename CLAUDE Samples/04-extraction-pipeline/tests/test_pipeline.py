import json
from pathlib import Path

import pytest

from extraction.llm import ScriptedExtractor
from extraction.pipeline import ROOT, extract_with_retry, process, route, run
from extraction.schema import TAGS, TOOL_SCHEMA, ArticleMetadata
from extraction.validate import validate

FIXTURES = ROOT / "data" / "fixtures"
RAW = ROOT / "data" / "raw"


def text(doc):
    return (RAW / f"{doc}.txt").read_text()


def fixture(doc, i=0):
    return json.loads((FIXTURES / f"{doc}.json").read_text())[i]


# --- schema ---------------------------------------------------------------

def test_tool_schema_and_pydantic_model_agree():
    assert set(TOOL_SCHEMA["required"]) == set(ArticleMetadata.model_fields)
    assert TOOL_SCHEMA["additionalProperties"] is False


def test_tag_vocabulary_comes_from_canonical_catalog():
    assert {"hypertension", "prediabetes", "poor_sleep", "sedentary"} <= set(TAGS)
    assert TOOL_SCHEMA["properties"]["condition_tags"]["items"]["enum"] == TAGS


def test_pydantic_rejects_extra_fields_and_unknown_tags():
    good = fixture("01-morning-walks")
    assert validate({**good, "sentiment": "positive"}, text("01-morning-walks"))[0] is None
    record, errors = validate({**good, "condition_tags": ["astrology"]}, text("01-morning-walks"))
    assert record is None and any("condition_tags" in e for e in errors)


def test_cross_field_rule():
    record, errors = validate(fixture("02-hiit-bootcamp", 0), text("02-hiit-bootcamp"))
    assert record is None and "contraindications" in errors[0]


# --- grounding --------------------------------------------------------------

def test_hallucinated_author_and_paraphrased_quote_are_caught():
    record, errors = validate(fixture("03-desk-stretches", 0), text("03-desk-stretches"))
    assert record is None
    assert any(e.startswith("author") for e in errors)
    assert any(e.startswith("evidence_quote") for e in errors)


# --- retry loop -------------------------------------------------------------

def test_retry_feeds_back_specific_errors():
    seen = []

    class Spy(ScriptedExtractor):
        def extract(self, messages):
            seen.append(messages[-1]["content"])
            return super().extract(messages)

    record, attempts, _ = extract_with_retry(Spy(FIXTURES), "03-desk-stretches", text("03-desk-stretches"))
    assert record is not None and attempts == 2
    assert "author: name does not appear in the source" in seen[1]
    assert "Dr. Priya Raman" in seen[1]  # previous answer is shown back


def test_retries_are_bounded():
    record, attempts, errors = extract_with_retry(
        ScriptedExtractor(FIXTURES), "05-vendor-supplement-promo", text("05-vendor-supplement-promo")
    )
    assert record is None and attempts == 3 and errors


# --- routing ----------------------------------------------------------------

@pytest.mark.parametrize(
    "doc,expected_route,reason_fragment",
    [
        ("01-morning-walks", "auto_approved", "all checks passed"),
        ("02-hiit-bootcamp", "human_review", "contraindications: hypertension"),
        ("03-desk-stretches", "auto_approved", "all checks passed"),
        ("04-evening-tips", "human_review", "confidence"),
        ("05-vendor-supplement-promo", "human_review", "validation failed"),
    ],
)
def test_end_to_end_routing(doc, expected_route, reason_fragment):
    outcome = process(ScriptedExtractor(FIXTURES), doc, text(doc))
    assert outcome.route == expected_route
    assert any(reason_fragment in r for r in outcome.reasons)


def test_run_writes_both_queues(tmp_path: Path):
    outcomes = run(ScriptedExtractor(FIXTURES), RAW, tmp_path)
    approved = (tmp_path / "auto_approved.jsonl").read_text().splitlines()
    review = (tmp_path / "human_review.jsonl").read_text().splitlines()
    assert len(approved) == 2 and len(review) == 3 and len(outcomes) == 5
    failed = [json.loads(l) for l in review if json.loads(l)["record"] is None]
    assert failed[0]["last_errors"]  # reviewer sees WHY it failed


def test_route_is_conservative():
    rec = ArticleMetadata(**fixture("01-morning-walks"))
    assert route(rec)[0] == "auto_approved"
    assert route(rec.model_copy(update={"contraindications": ["hypertension"]}))[0] == "human_review"
