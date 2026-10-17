from datetime import UTC, datetime
import json
from pathlib import Path

from src.config import POC_ROOT, get_settings
from src.errors import PocError
from src.generator import generate_summary
from src.models import HealthReport, PipelineResult
from src.openai_client import create_client
from src.report_parser import parse_report
from src.retriever import retrieve_for_report

OUTPUT_DIR = POC_ROOT / "output"


def run_recommendation(report: HealthReport) -> PipelineResult:
    settings = get_settings()
    markers = parse_report(report)
    client = create_client(settings)
    physical, mental = retrieve_for_report(report, markers, client)
    summary = generate_summary(report, markers, physical, mental, client)
    return PipelineResult(
        report_id=report.report_id,
        generated_at=datetime.now(UTC),
        generation_model=settings.generation_model,
        embedding_model=settings.embedding_model,
        markers=markers,
        physical=physical,
        mental=mental,
        summary=summary,
    )


def load_report(path: Path) -> HealthReport:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PocError(f"Cannot read health report at {path}: {exc}") from exc
    try:
        return HealthReport.model_validate(payload)
    except ValueError as exc:
        raise PocError(f"Health report failed schema validation: {exc}") from exc


def save_result(result: PipelineResult) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{result.report_id}.json"
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return output_path
