import json

from openai import OpenAIError
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.config import POC_ROOT, get_settings
from src.errors import PocError
from src.models import Candidate, JudgeVerdict


def build_agno_judge(candidates: list[Candidate]):
    settings = get_settings()
    by_id = {candidate.article.id: candidate.article for candidate in candidates}

    def read_article(article_id: str) -> str:
        """Read the full text of a retrieved article by ID."""
        article = by_id.get(article_id)
        if article is None:
            return "Article not found in the retrieved candidate set."
        return json.dumps(
            {
                "id": article.id,
                "title": article.title,
                "category": article.category,
                "body": article.body,
                "condition_tags": article.condition_tags,
            },
            ensure_ascii=False,
        )

    return Agent(
        model=OpenAIChat(id=settings.generation_model, max_retries=0, timeout=45),
        tools=[read_article],
        instructions=[
            (POC_ROOT / "prompts" / "validator_judge_v1.txt").read_text(encoding="utf-8"),
            "Use read_article to inspect full article text before judging.",
        ],
        output_schema=JudgeVerdict,
        markdown=False,
        retries=0,
    )


def judge_with_agno(context: dict, candidates: list[Candidate]) -> JudgeVerdict:
    try:
        agent = build_agno_judge(candidates)
        response = agent.run(
            json.dumps(
                {
                    "report": context,
                    "candidates": [
                        {
                            "id": candidate.article.id,
                            "title": candidate.article.title,
                            "category": candidate.article.category,
                            "condition_tags": candidate.article.condition_tags,
                        }
                        for candidate in candidates
                    ],
                },
                ensure_ascii=False,
            )
        )
    except (OpenAIError, ValueError) as exc:
        raise PocError(
            f"Agno validator failed ({type(exc).__name__}); check OpenAI "
            "credentials/model access and the structured agent response."
        ) from exc
    content = getattr(response, "content", response)
    if isinstance(content, JudgeVerdict):
        return content
    if isinstance(content, str):
        return JudgeVerdict.model_validate_json(content)
    return JudgeVerdict.model_validate(content)
