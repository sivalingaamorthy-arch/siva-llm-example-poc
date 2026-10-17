from datetime import UTC, datetime
import time
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from src.config import get_settings
from src.errors import PocError
from src.models import (
    AgentResult,
    Candidate,
    HealthReport,
    JudgeVerdict,
    TraceEvent,
)
from src.openai_service import create_client, generate_summary, judge_candidates
from src.report_parser import parse_report
from src.retrieval import load_defaults, retrieve_for_report
from src.rules import validate_rules
from src.agents.shared import OUTPUT_DIR, _save_fallback_events


class GraphState(TypedDict):
    report: HealthReport
    client: OpenAI
    markers: list[str]
    unmatched_topics: list[str]
    excluded_ids: list[str]
    feedback: str
    physical: list[Candidate]
    mental: list[Candidate]
    verdict: JudgeVerdict
    attempt: int
    retry_count: int
    trace: list[TraceEvent]
    used_fallback: NotRequired[bool]
    summary: NotRequired[str]
    result: NotRequired[AgentResult]


def build_graph():
    settings = get_settings()

    def parse_node(state: GraphState) -> dict:
        started = time.perf_counter()
        markers, topics = parse_report(state["report"])
        event = TraceEvent(
            attempt=0,
            node="parse_report",
            message=f"Parsed {len(markers)} markers and {len(topics)} unmatched topics.",
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return {"markers": markers, "unmatched_topics": topics, "trace": [event]}

    def retrieve_node(state: GraphState) -> dict:
        started = time.perf_counter()
        physical, mental = retrieve_for_report(
            state["report"], state["markers"], state["excluded_ids"], state["client"],
            feedback=state["feedback"],
        )
        candidates = [*physical, *mental]
        event = TraceEvent(
            attempt=state["attempt"],
            node="retrieve",
            message=f"Retrieved {len(physical)} physical and {len(mental)} mental candidates.",
            article_ids=[candidate.article.id for candidate in candidates],
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return {
            "physical": physical,
            "mental": mental,
            "trace": [*state["trace"], event],
        }

    def rules_node(state: GraphState) -> dict:
        started = time.perf_counter()
        verdict = validate_rules(
            state["report"],
            state["markers"],
            state["unmatched_topics"],
            state["physical"],
            state["mental"],
        )
        event = TraceEvent(
            attempt=state["attempt"],
            node="rules_validator",
            message=verdict.feedback,
            article_ids=verdict.rejected_ids,
            verdict=verdict.verdict,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return {"verdict": verdict, "trace": [*state["trace"], event]}

    def judge_node(state: GraphState) -> dict:
        started = time.perf_counter()
        verdict = judge_candidates(
            state["client"],
            {
                "report_id": state["report"].report_id,
                "markers": state["markers"],
                "unmatched_topics": state["unmatched_topics"],
                "notes": state["report"].notes,
            },
            [*state["physical"], *state["mental"]],
        )
        event = TraceEvent(
            attempt=state["attempt"],
            node="llm_judge",
            message=verdict.feedback,
            article_ids=verdict.rejected_ids,
            verdict=verdict.verdict,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return {"verdict": verdict, "trace": [*state["trace"], event]}

    def retry_node(state: GraphState) -> dict:
        verdict = state["verdict"]
        candidate_ids = [
            candidate.article.id
            for candidate in [*state["physical"], *state["mental"]]
        ]
        newly_excluded = verdict.rejected_ids or candidate_ids
        excluded = sorted(set(state["excluded_ids"]).union(newly_excluded))
        next_attempt = state["attempt"] + 1
        event = TraceEvent(
            attempt=state["attempt"],
            node="retry",
            message=f"Retry {next_attempt}/{settings.max_retries}: {verdict.feedback}",
            article_ids=newly_excluded,
            verdict="retry",
            elapsed_ms=0,
        )
        return {
            "excluded_ids": excluded,
            "feedback": verdict.feedback,
            "attempt": next_attempt,
            "retry_count": next_attempt,
            "trace": [*state["trace"], event],
        }

    def fallback_node(state: GraphState) -> dict:
        physical, mental = load_defaults()
        verdict = state["verdict"]
        topics = verdict.uncovered_topics or state["unmatched_topics"]
        _save_fallback_events(state["report"].report_id, topics, verdict.feedback)
        event = TraceEvent(
            attempt=state["attempt"],
            node="fallback",
            message="Retry limit reached; returned generic approved defaults and queued reassessment.",
            article_ids=[item.article.id for item in [*physical, *mental]],
            verdict="fallback",
            elapsed_ms=0,
        )
        summary = (
            "The available content did not pass review for this report. The items shown "
            "are generic defaults and may not address the reported topics. Please speak "
            "to a health adviser before making changes to your health routine."
        )
        if topics:
            summary += " Content coverage is missing for: " + ", ".join(topics) + "."
        return {
            "physical": physical,
            "mental": mental,
            "used_fallback": True,
            "summary": summary,
            "trace": [*state["trace"], event],
        }

    def generate_node(state: GraphState) -> dict:
        context = {
            "report_id": state["report"].report_id,
            "markers": state["markers"],
            "unmatched_topics": state["unmatched_topics"],
            "notes": state["report"].notes,
        }
        summary = generate_summary(
            state["client"], context, state["physical"], state["mental"], False
        )
        return {"used_fallback": False, "summary": summary}

    def finish_node(state: GraphState) -> dict:
        result = AgentResult(
            report_id=state["report"].report_id,
            framework="langgraph",
            generated_at=datetime.now(UTC),
            generation_model=settings.generation_model,
            embedding_model=settings.embedding_model,
            markers=state["markers"],
            unmatched_topics=state["unmatched_topics"],
            retry_count=state["retry_count"],
            used_fallback=state["used_fallback"],
            physical=state["physical"],
            mental=state["mental"],
            summary=state["summary"],
            trace=state["trace"],
        )
        path = OUTPUT_DIR / "runs" / f"{result.report_id}_langgraph.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return {"result": result}

    def after_rules(state: GraphState) -> str:
        return "judge" if state["verdict"].verdict == "pass" else "route"

    def route(state: GraphState) -> str:
        if state["verdict"].verdict == "pass":
            return "generate"
        if state["attempt"] < settings.max_retries:
            return "retry"
        return "fallback"

    graph = StateGraph(GraphState)
    graph.add_node("parse_report", parse_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("validate_rules", rules_node)
    graph.add_node("judge", judge_node)
    graph.add_node("retry", retry_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("generate", generate_node)
    graph.add_node("finish", finish_node)
    graph.add_edge(START, "parse_report")
    graph.add_edge("parse_report", "retrieve")
    graph.add_edge("retrieve", "validate_rules")
    graph.add_conditional_edges(
        "validate_rules",
        after_rules,
        {"judge": "judge", "route": "route"},
    )
    graph.add_conditional_edges(
        "judge",
        route,
        {
            "generate": "generate",
            "retry": "retry",
            "fallback": "fallback",
        },
    )
    # Rules failures use the same bounded retry/fallback router.
    graph.add_node("route", lambda state: state)
    graph.add_conditional_edges(
        "route",
        route,
        {
            "generate": "generate",
            "retry": "retry",
            "fallback": "fallback",
        },
    )
    graph.add_edge("retry", "retrieve")
    graph.add_edge("fallback", "finish")
    graph.add_edge("generate", "finish")
    graph.add_edge("finish", END)
    return graph.compile()


def run_langgraph(report: HealthReport) -> AgentResult:
    graph = build_graph()
    final_state = graph.invoke(
        {
            "report": report,
            "client": create_client(),
            "markers": [],
            "unmatched_topics": [],
            "excluded_ids": [],
            "feedback": "",
            "physical": [],
            "mental": [],
            "verdict": JudgeVerdict(verdict="fail", feedback="Not validated."),
            "attempt": 0,
            "retry_count": 0,
            "trace": [],
        },
        config={"recursion_limit": 50},
    )
    result = final_state.get("result")
    if not result:
        raise PocError("LangGraph completed without producing a final result.")
    return result
