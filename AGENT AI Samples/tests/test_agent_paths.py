from src.agents import shared
from src.agents.agno_agent import build_agno_judge
from src.agents.langchain_agent import build_langchain_judge
from src.agents.langgraph_agent import build_graph
from src.config import SAMPLE_DATA_ROOT, Settings
from src.loader import load_report
from src.models import Article, Candidate, JudgeVerdict
from src.rules import validate_rules

def test_langgraph_contains_explicit_retry_and_fallback_nodes():
    nodes = set(build_graph().get_graph().nodes)
    assert {"parse_report", "retrieve", "validate_rules", "judge", "retry", "fallback", "generate"} <= nodes


def test_langchain_and_agno_judges_build_without_making_api_calls(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used-for-network")
    candidates = [make_candidate("p1", "physical")]
    assert build_langchain_judge(candidates) is not None
    assert build_agno_judge(candidates) is not None


def make_candidate(article_id: str, category: str, intensity: str = "low") -> Candidate:
    return Candidate(
        article=Article(
            id=article_id,
            title=article_id,
            body="Synthetic educational content.",
            category=category,
            condition_tags=[],
            intensity=intensity,
            contraindications=["hypertension"] if intensity == "high" else [],
            source="vendor",
            approved=True,
            is_default=False,
            published_date="2026-01-15",
        ),
        similarity=0.7,
    )


def test_r2_retries_after_rules_reject_and_then_passes(monkeypatch, tmp_path):
    report = load_report(SAMPLE_DATA_ROOT / "reports" / "report2_safety_trap.json")
    high = make_candidate("physical-risk", "physical", "high")
    safe_physical = [make_candidate(f"physical-safe-{i}", "physical") for i in range(3)]
    mental = [make_candidate(f"mental-{i}", "mental") for i in range(3)]
    calls = []

    def fake_retrieve(report, markers, excluded, client, feedback=""):
        calls.append(list(excluded))
        return ([high, *safe_physical[:2]], mental) if not excluded else (safe_physical, mental)

    monkeypatch.setattr(shared, "create_client", lambda settings: object())
    monkeypatch.setattr(shared, "retrieve_for_report", fake_retrieve)
    monkeypatch.setattr(
        shared,
        "_safe_judge",
        lambda framework, client, context, candidates: JudgeVerdict(
            verdict="pass", feedback="Relevant article content."
        ),
    )
    monkeypatch.setattr(
        shared,
        "generate_summary",
        lambda *args, **kwargs: "Educational summary.",
    )
    monkeypatch.setattr(shared, "get_settings", lambda: Settings(
        database_url="postgresql://unused",
        api_key="test",
        generation_model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        max_retries=3,
    ))
    monkeypatch.setattr(shared, "OUTPUT_DIR", tmp_path)

    result = shared.run_bounded_loop(report, "langchain")
    assert result.retry_count == 1
    assert result.used_fallback is False
    assert len(calls) == 2
    assert all(item.article.intensity != "high" for item in result.physical)


def test_r3_performs_three_retries_then_falls_back_and_logs(monkeypatch, tmp_path):
    report = load_report(SAMPLE_DATA_ROOT / "reports" / "report3_content_gap.json")
    physical = [make_candidate(f"physical-{i}", "physical") for i in range(3)]
    mental = [make_candidate(f"mental-{i}", "mental") for i in range(3)]
    default_physical = make_candidate("default-physical", "physical").model_copy(
        update={"article": make_candidate("default-physical", "physical").article.model_copy(update={"is_default": True})}
    )
    default_mental = make_candidate("default-mental", "mental").model_copy(
        update={"article": make_candidate("default-mental", "mental").article.model_copy(update={"is_default": True})}
    )
    retrieval_calls = []
    monkeypatch.setattr(shared, "create_client", lambda settings: object())
    monkeypatch.setattr(
        shared,
        "retrieve_for_report",
        lambda report, markers, excluded, client, feedback="": (
            retrieval_calls.append(list(excluded)) or (physical, mental)
        ),
    )
    monkeypatch.setattr(shared, "load_defaults", lambda: ([default_physical], [default_mental]))
    monkeypatch.setattr(shared, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(shared, "get_settings", lambda: Settings(
        database_url="postgresql://unused",
        api_key="test",
        generation_model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        max_retries=3,
    ))

    result = shared.run_bounded_loop(report, "agno")
    assert result.used_fallback is True
    assert result.retry_count == 3
    assert len(retrieval_calls) == 4
    assert result.unmatched_topics == ["postpartum"]
    assert any(event.node == "fallback" for event in result.trace)
    assert (tmp_path / "content_gap_alerts.jsonl").exists()
    assert (tmp_path / "reassessment_queue.jsonl").exists()
