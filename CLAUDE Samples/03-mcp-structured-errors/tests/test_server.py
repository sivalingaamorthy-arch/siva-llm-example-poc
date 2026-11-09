"""In-process MCP client tests: real protocol round-trip, no subprocess."""

import asyncio

import pytest
from mcp import Client

from health_content_mcp.server import ArticleStore, build_server


def call(name, args, *, store=None, debug=False):
    async def _run():
        async with Client(build_server(store, debug=debug)) as client:
            return await client.call_tool(name, args)

    return asyncio.run(_run())


def err(result):
    assert result.is_error is True, result
    return result.structured_content["error"]


def test_reads_canonical_catalog():
    ok = call("get_article", {"article_id": "physical-08"})
    assert ok.structured_content["article"]["contraindications"] == ["hypertension"]


def test_tools_are_listed():
    async def _run():
        async with Client(build_server()) as client:
            return {t.name for t in (await client.list_tools()).tools}

    assert asyncio.run(_run()) == {"search_articles", "get_article", "flag_article"}


def test_search_success_and_empty_is_not_an_error():
    ok = call("search_articles", {"query": "sleep"})
    assert ok.is_error is False and ok.structured_content["results"][0]["category"] in {"mental", "wellbeing", "physical"}
    empty = call("search_articles", {"query": "quantum chromodynamics"})
    assert empty.is_error is False and empty.structured_content["count"] == 0


@pytest.mark.parametrize(
    "name,args,category,code",
    [
        ("search_articles", {"query": "  "}, "validation", "EMPTY_QUERY"),
        ("search_articles", {"query": "sleep", "limit": 99}, "validation", "LIMIT_OUT_OF_RANGE"),
        ("get_article", {"article_id": "123"}, "validation", "INVALID_ARTICLE_ID"),
        ("get_article", {"article_id": "physical-99"}, "not_found", "ARTICLE_NOT_FOUND"),
        (
            "flag_article",
            {"article_id": "physical-08", "reason": "intensity wording unclear", "reviewer_role": "editor"},
            "permission",
            "CLINICIAN_REQUIRED",
        ),
        (
            "flag_article",
            {"article_id": "physical-01", "reason": "outdated advice", "reviewer_role": "intern"},
            "validation",
            "INVALID_ROLE",
        ),
    ],
)
def test_error_taxonomy(name, args, category, code):
    e = err(call(name, args))
    assert (e["errorCategory"], e["code"]) == (category, code)
    assert e["isRetryable"] is False
    assert e["message"]


def test_business_rule_duplicate_flag():
    store = ArticleStore()
    args = {"article_id": "physical-01", "reason": "advice needs a source", "reviewer_role": "editor"}
    assert call("flag_article", args, store=store).is_error is False
    assert err(call("flag_article", args, store=store))["code"] == "ALREADY_FLAGGED"


def test_transient_error_is_retryable_then_succeeds():
    store = ArticleStore(flaky_calls=1)
    first = err(call("get_article", {"article_id": "physical-01"}, store=store))
    assert first["errorCategory"] == "transient" and first["isRetryable"] is True
    assert first["retryAfterMs"] == 500
    assert call("get_article", {"article_id": "physical-01"}, store=store).is_error is False


def test_crash_becomes_safe_internal_error():
    e = err(call("debug_crash", {}, debug=True))
    assert e["errorCategory"] == "internal" and e["isRetryable"] is False
    assert "hunter2" not in str(e)  # no leaking internals to the model


def test_text_content_mirrors_structured_content():
    r = call("get_article", {"article_id": "physical-99"})
    assert '"errorCategory": "not_found"' in r.content[0].text
