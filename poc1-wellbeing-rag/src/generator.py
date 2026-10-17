import json

from openai import OpenAI

from src.config import POC_ROOT, get_settings
from src.errors import PocError
from src.models import HealthReport, Recommendation
from src.openai_client import generate_text

PROMPT_PATH = POC_ROOT / "prompts" / "summary_v1.txt"


def generate_summary(
    report: HealthReport,
    markers: list[str],
    physical: list[Recommendation],
    mental: list[Recommendation],
    client: OpenAI,
) -> str:
    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise PocError(f"Cannot read summary prompt at {PROMPT_PATH}: {exc}") from exc
    articles = [
        recommendation.article.model_dump(mode="json")
        for recommendation in [*physical, *mental]
    ]
    context = json.dumps(
        {
            "report_id": report.report_id,
            "markers": markers,
            "notes": report.notes,
            "retrieved_articles": articles,
        },
        ensure_ascii=False,
    )
    summary = generate_text(
        client,
        get_settings().generation_model,
        system_prompt,
        "Write a short educational summary using this JSON context only:\n" + context,
    )
    adviser_sentence = (
        "Please speak to a health adviser before making changes to your health routine."
    )
    if markers and adviser_sentence not in summary:
        summary = f"{summary}\n\n{adviser_sentence}"
    return summary
