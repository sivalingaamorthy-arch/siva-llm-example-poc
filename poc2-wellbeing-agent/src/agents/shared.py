from datetime import UTC, datetime
import json
from pathlib import Path
import time

from src.config import POC_ROOT, get_settings
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

OUTPUT_DIR = POC_ROOT / "output"


def _append_json_line(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _save_fallback_events(report_id: str, uncovered: list[str], reason: str) -> None:
    now = datetime.now(UTC).isoformat()
    _append_json_line(
        OUTPUT_DIR / "content_gap_alerts.jsonl",
        {
            "report_id": report_id,
            "uncovered_topics": uncovered,
            "reason": reason,
            "timestamp": now,
        },
    )
    _append_json_line(
        OUTPUT_DIR / "reassessment_queue.jsonl",
        {"report_id": report_id, "reason": reason, "timestamp": now},
    )


def _safe_judge(
    framework: str,
    client,
    context: dict,
    candidates: list[Candidate],
) -> JudgeVerdict:
    if framework == "langchain":
        from src.agents.langchain_agent import judge_with_langchain

        return judge_with_langchain(context, candidates)
    if framework == "agno":
        from src.agents.agno_agent import judge_with_agno

        return judge_with_agno(context, candidates)
    return judge_candidates(client, context, candidates)


def run_bounded_loop(report: HealthReport, framework: str) -> AgentResult:
    settings = get_settings()
    client = create_client(settings)
    markers, unmatched_topics = parse_report(report)
    context = {
        "report_id": report.report_id,
        "markers": markers,
        "unmatched_topics": unmatched_topics,
        "notes": report.notes,
    }
    trace: list[TraceEvent] = []
    excluded: list[str] = []
    feedback = ""
    physical: list[Candidate] = []
    mental: list[Candidate] = []
    accepted = False
    final_verdict = JudgeVerdict(verdict="fail", feedback="No validation attempt completed.")
    retry_count = 0

    for attempt in range(settings.max_retries + 1):
        started = time.perf_counter()
        physical, mental = retrieve_for_report(
            report, markers, excluded, client, feedback=feedback
        )
        candidates = [*physical, *mental]
        trace.append(
            TraceEvent(
                attempt=attempt,
                node="retrieve",
                message=f"Retrieved {len(physical)} physical and {len(mental)} mental candidates.",
                article_ids=[candidate.article.id for candidate in candidates],
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
        )

        started = time.perf_counter()
        final_verdict = validate_rules(
            report, markers, unmatched_topics, physical, mental
        )
        trace.append(
            TraceEvent(
                attempt=attempt,
                node="rules_validator",
                message=final_verdict.feedback,
                article_ids=final_verdict.rejected_ids,
                verdict=final_verdict.verdict,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
        )

        if final_verdict.verdict == "pass":
            started = time.perf_counter()
            final_verdict = _safe_judge(framework, client, context, candidates)
            trace.append(
                TraceEvent(
                    attempt=attempt,
                    node=f"{framework}_judge",
                    message=final_verdict.feedback,
                    article_ids=final_verdict.rejected_ids,
                    verdict=final_verdict.verdict,
                    elapsed_ms=int((time.perf_counter() - started) * 1000),
                )
            )
        if final_verdict.verdict == "pass":
            accepted = True
            retry_count = attempt
            break
        if attempt < settings.max_retries:
            retry_count = attempt + 1
            new_exclusions = final_verdict.rejected_ids or [
                candidate.article.id for candidate in candidates
            ]
            excluded = sorted(set(excluded).union(new_exclusions))
            feedback = final_verdict.feedback
            trace.append(
                TraceEvent(
                    attempt=attempt,
                    node="retry",
                    message=f"Retry {retry_count}/{settings.max_retries}: {final_verdict.feedback}",
                    article_ids=new_exclusions,
                    verdict="retry",
                    elapsed_ms=0,
                )
            )

    used_fallback = not accepted
    if used_fallback:
        physical, mental = load_defaults()
        _save_fallback_events(
            report.report_id,
            final_verdict.uncovered_topics or unmatched_topics,
            final_verdict.feedback,
        )
        trace.append(
            TraceEvent(
                attempt=settings.max_retries,
                node="fallback",
                message="Retry limit reached; returned generic approved defaults and queued reassessment.",
                article_ids=[
                    candidate.article.id for candidate in [*physical, *mental]
                ],
                verdict="fallback",
                elapsed_ms=0,
            )
        )
        summary = (
            "The available content did not pass review for this report. The items shown "
            "are generic defaults and may not address the reported topics. Please speak "
            "to a health adviser before making changes to your health routine."
        )
        if unmatched_topics:
            summary += " Content coverage is missing for: " + ", ".join(unmatched_topics) + "."
    else:
        summary = generate_summary(client, context, physical, mental, used_fallback=False)

    result = AgentResult(
        report_id=report.report_id,
        framework=framework,
        generated_at=datetime.now(UTC),
        generation_model=settings.generation_model,
        embedding_model=settings.embedding_model,
        markers=markers,
        unmatched_topics=unmatched_topics,
        retry_count=retry_count,
        used_fallback=used_fallback,
        physical=physical,
        mental=mental,
        summary=summary,
        trace=trace,
    )
    output_path = OUTPUT_DIR / "runs" / f"{report.report_id}_{framework}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
