import json

from openai import OpenAI, OpenAIError

from src.config import POC_ROOT, Settings, get_settings
from src.errors import PocError
from src.models import Candidate, JudgeVerdict


def create_client(settings: Settings | None = None) -> OpenAI:
    settings = settings or get_settings()
    if not settings.api_key:
        raise PocError(
            "OPENAI_API_KEY is not configured. Add it as a Codespaces secret, "
            "then restart the Codespace."
        )
    return OpenAI(api_key=settings.api_key, max_retries=0, timeout=45.0)


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    try:
        response = client.embeddings.create(model=settings.embedding_model, input=texts)
    except OpenAIError as exc:
        raise PocError(
            f"OpenAI embedding request failed ({type(exc).__name__}); check key, "
            "internet access, model access, and account billing."
        ) from exc
    vectors = [
        item.embedding
        for item in sorted(response.data, key=lambda item: item.index)
    ]
    if len(vectors) != len(texts) or any(
        len(vector) != settings.embedding_dimensions for vector in vectors
    ):
        raise PocError("OpenAI returned unexpected embedding count or dimension.")
    return vectors


def judge_candidates(
    client: OpenAI,
    report_context: dict,
    candidates: list[Candidate],
) -> JudgeVerdict:
    settings = get_settings()
    prompt_data = {
        "report": report_context,
        "candidates": [
            {
                "id": candidate.article.id,
                "title": candidate.article.title,
                "body": candidate.article.body,
                "category": candidate.article.category,
                "condition_tags": candidate.article.condition_tags,
            }
            for candidate in candidates
        ],
    }
    try:
        system_prompt = (POC_ROOT / "prompts" / "validator_judge_v1.txt").read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise PocError(f"Cannot read validator prompt: {exc}") from exc
    try:
        response = client.chat.completions.create(
            model=settings.generation_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                    + "\nReturn JSON with keys verdict (pass/fail), rejected_ids "
                    "(array), feedback (string), and uncovered_topics (array). "
                    "Only use IDs in the supplied candidates.",
                },
                {"role": "user", "content": json.dumps(prompt_data, ensure_ascii=False)},
            ],
        )
    except OpenAIError as exc:
        raise PocError(
            f"OpenAI validator request failed ({type(exc).__name__}); check key, "
            "internet access, model access, and billing."
        ) from exc
    content = response.choices[0].message.content
    if not content:
        raise PocError("OpenAI validator returned an empty response.")
    try:
        return JudgeVerdict.model_validate_json(content)
    except ValueError as exc:
        raise PocError("OpenAI validator returned invalid verdict JSON.") from exc


def generate_summary(
    client: OpenAI,
    report_context: dict,
    physical: list[Candidate],
    mental: list[Candidate],
    used_fallback: bool,
) -> str:
    settings = get_settings()
    articles = [
        candidate.article.model_dump(mode="json")
        for candidate in [*physical, *mental]
    ]
    try:
        system_prompt = (POC_ROOT / "prompts" / "summary_v1.txt").read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise PocError(f"Cannot read summary prompt: {exc}") from exc
    if used_fallback:
        system_prompt += (
            "\nClearly say that the displayed defaults are generic and do not necessarily "
            "address the specific report topics."
        )
    try:
        response = client.chat.completions.create(
            model=settings.generation_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "report": report_context,
                            "articles": articles,
                            "fallback": used_fallback,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
    except OpenAIError as exc:
        raise PocError(
            f"OpenAI summary request failed ({type(exc).__name__}); check key, "
            "internet access, model access, and billing."
        ) from exc
    text = response.choices[0].message.content
    if not text:
        raise PocError("OpenAI returned an empty summary.")
    sentence = "Please speak to a health adviser before making changes to your health routine."
    if report_context["markers"] and sentence not in text:
        text = f"{text}\n\n{sentence}"
    return text
