from openai import OpenAI, OpenAIError

from src.config import Settings, get_settings
from src.errors import ExternalServiceError


def create_client(settings: Settings | None = None) -> OpenAI:
    settings = settings or get_settings()
    if not settings.openai_api_key:
        raise ExternalServiceError(
            "OPENAI_API_KEY is not configured. Add it as a Codespaces secret, "
            "then restart the Codespace."
        )
    return OpenAI(api_key=settings.openai_api_key, max_retries=0, timeout=30.0)


def embed_texts(client: OpenAI, texts: list[str], model: str) -> list[list[float]]:
    try:
        response = client.embeddings.create(model=model, input=texts)
    except OpenAIError as exc:
        raise ExternalServiceError(
            f"OpenAI embedding request failed ({type(exc).__name__}). Check "
            "internet access, API key permissions, model access, and account billing."
        ) from exc
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def generate_text(client: OpenAI, model: str, system_prompt: str, user_prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except OpenAIError as exc:
        raise ExternalServiceError(
            f"OpenAI generation request failed ({type(exc).__name__}). Check "
            "internet access, API key permissions, model access, and account billing."
        ) from exc
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ExternalServiceError("OpenAI returned an empty summary.")
    return content.strip()
