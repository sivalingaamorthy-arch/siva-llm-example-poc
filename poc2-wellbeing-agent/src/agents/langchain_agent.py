import json

from openai import OpenAIError
from langchain.agents import create_agent
from langchain_core.exceptions import LangChainException
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from src.config import POC_ROOT, get_settings
from src.errors import PocError
from src.models import Candidate, JudgeVerdict


def build_langchain_judge(candidates: list[Candidate]):
    settings = get_settings()
    by_id = {candidate.article.id: candidate.article for candidate in candidates}

    @tool
    def read_article(article_id: str) -> str:
        """Read the full text of a retrieved article by its ID."""
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

    return create_agent(
        model=ChatOpenAI(
            model=settings.generation_model,
            temperature=0,
            max_retries=0,
            timeout=45,
        ),
        tools=[read_article],
        system_prompt=(
            (POC_ROOT / "prompts" / "validator_judge_v1.txt").read_text(encoding="utf-8")
            + " Use read_article for the complete text of each candidate before judging."
        ),
        response_format=JudgeVerdict,
    )


def judge_with_langchain(context: dict, candidates: list[Candidate]) -> JudgeVerdict:
    try:
        agent = build_langchain_judge(candidates)
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
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
                        ),
                    }
                ]
            },
            config={"recursion_limit": 12},
        )
    except (OpenAIError, LangChainException, ValueError) as exc:
        raise PocError(
            f"LangChain validator failed ({type(exc).__name__}); check OpenAI "
            "credentials/model access and the structured agent response."
        ) from exc
    verdict = result.get("structured_response")
    if isinstance(verdict, JudgeVerdict):
        return verdict
    return JudgeVerdict.model_validate(verdict)
