import json

import pytest

from poc3_health_content_mcp import server
from poc3_health_content_mcp.shortlists import MemoryShortlistStore


def test_bmi_returns_rounded_value() -> None:
    assert server.bmi(72, 1.75) == 23.5


@pytest.mark.parametrize(
    ("weight_kg", "height_m"),
    [(0, 1.75), (-1, 1.75), (72, 0), (72, float("inf"))],
)
def test_bmi_rejects_invalid_measurements(weight_kg: float, height_m: float) -> None:
    with pytest.raises(ValueError):
        server.bmi(weight_kg, height_m)


def test_report_tool_uses_only_bundled_ids() -> None:
    tool = server.mcp._tool_manager.get_tool("recommendations_for_demo_report")
    assert tool.parameters["properties"]["report_id"]["enum"] == ["R1", "R2", "R3"]


def test_article_resource_rejects_unknown_ids() -> None:
    with pytest.raises(ValueError, match="Unknown article_id"):
        server.article_resource("../../.env")


def test_article_resource_returns_fixture_json() -> None:
    article = json.loads(server.article_resource("physical-01"))
    assert article["id"] == "physical-01"
    assert article["title"]


def test_shortlist_store_is_explicit_and_idempotent() -> None:
    store = MemoryShortlistStore()
    shortlist_id = store.create()

    assert store.add(shortlist_id, "physical-01") == ["physical-01"]
    assert store.add(shortlist_id, "physical-01") == ["physical-01"]
    assert store.get(shortlist_id) == ["physical-01"]

    store.clear(shortlist_id)
    with pytest.raises(ValueError, match="Unknown shortlist_id"):
        store.get(shortlist_id)


def test_clear_requires_server_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    test_store = MemoryShortlistStore()
    monkeypatch.setattr(server, "shortlists", test_store)
    shortlist_id = test_store.create()
    monkeypatch.delenv("SHORTLIST_CLEAR_ALLOWED_IDS", raising=False)

    with pytest.raises(PermissionError, match="disabled"):
        server.clear_shortlist(shortlist_id)
    assert test_store.get(shortlist_id) == []

    monkeypatch.setenv("SHORTLIST_CLEAR_ALLOWED_IDS", "not-the-shortlist")
    with pytest.raises(PermissionError, match="Not authorized"):
        server.clear_shortlist(shortlist_id)
    assert test_store.get(shortlist_id) == []

    monkeypatch.setenv("SHORTLIST_CLEAR_ALLOWED_IDS", shortlist_id)
    assert server.clear_shortlist(shortlist_id) is True
    with pytest.raises(ValueError, match="Unknown shortlist_id"):
        test_store.get(shortlist_id)
