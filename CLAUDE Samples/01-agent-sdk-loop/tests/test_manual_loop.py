"""Loop tests with a scripted fake client: no API key, deterministic, fast."""

from types import SimpleNamespace as NS

import pytest

from health_agent import catalog
from health_agent.guard import SAVE_TOOL, SEARCH_TOOL
from health_agent.manual_loop import run_loop


def tool_use(id_, name, input_):
    return NS(type="tool_use", id=id_, name=name, input=input_)


def text(t):
    return NS(type="text", text=t)


class FakeClient:
    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        # snapshot: the loop keeps appending to the same list after the call
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self._scripted.pop(0)


@pytest.fixture(autouse=True)
def tmp_outbox(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "DEFAULT_OUTBOX", tmp_path / "recs.jsonl")
    # save_recommendation's default arg is bound at def time; patch the function too
    original = catalog.save_recommendation
    monkeypatch.setattr(
        catalog,
        "save_recommendation",
        lambda **kw: original(**kw, outbox=tmp_path / "recs.jsonl"),
    )


def test_happy_path_search_save_answer():
    client = FakeClient(
        [
            NS(stop_reason="tool_use", content=[tool_use("t1", SEARCH_TOOL, {"query": "walking"})]),
            NS(
                stop_reason="tool_use",
                content=[tool_use("t2", SAVE_TOOL, {"report_id": "R2", "article_id": "physical-01", "reason": "gentle start"})],
            ),
            NS(stop_reason="end_turn", content=[text("Try 'Gentle walking'.")]),
        ]
    )
    result = run_loop(client, "report_id=R2")
    assert result.stop == "end_turn" and result.turns == 3
    assert "Gentle walking" in result.final_text
    # tool_result must reference the tool_use id it answers
    last_user = client.calls[-1]["messages"][-1]
    assert last_user["content"][0]["tool_use_id"] == "t2"


def test_guard_denial_is_fed_back_as_error_result():
    client = FakeClient(
        [
            NS(
                stop_reason="tool_use",
                content=[tool_use("t1", SAVE_TOOL, {"report_id": "R2", "article_id": "physical-08", "reason": "get fitter quickly"})],
            ),
            NS(stop_reason="end_turn", content=[text("Chose a gentler option.")]),
        ]
    )
    result = run_loop(client, "report_id=R2")
    assert len(result.denials) == 1
    fed_back = client.calls[1]["messages"][-1]["content"][0]
    assert fed_back["is_error"] is True and "hypertension" in fed_back["content"]


def test_turn_limit_stops_a_runaway_loop():
    looping = NS(stop_reason="tool_use", content=[tool_use("t", SEARCH_TOOL, {"query": "walking"})])
    client = FakeClient([looping] * 10)
    result = run_loop(client, "loop forever", max_turns=3)
    assert result.stop == "max_turns" and len(client.calls) == 3


def test_non_success_stop_reason_is_surfaced():
    client = FakeClient([NS(stop_reason="max_tokens", content=[text("trunc")])])
    assert run_loop(client, "x").stop == "max_tokens"
