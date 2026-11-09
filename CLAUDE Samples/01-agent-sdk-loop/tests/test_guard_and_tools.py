import asyncio

from health_agent import catalog, sample_data
from health_agent.guard import SAVE_TOOL, SEARCH_TOOL, evaluate, pre_tool_use_guard


def save(report_id, article_id, reason="fits the report"):
    return evaluate(SAVE_TOOL, {"report_id": report_id, "article_id": article_id, "reason": reason})


def test_reads_canonical_catalog_and_markers():
    assert len(sample_data.articles()) == 33
    assert sample_data.markers(sample_data.report("R2")) == ["hypertension", "prediabetes"]
    assert sample_data.markers(sample_data.report("R1")) == [
        "high_bmi", "poor_sleep", "sedentary", "stress"
    ]


def test_search_surfaces_unsafe_candidates_for_the_guard_to_stop():
    ids = [a["id"] for a in catalog.search_articles("fitness interval training")]
    assert "physical-08" in ids  # HIIT: search does not filter, the guard does


def test_search_skips_defaults_and_handles_nonsense():
    assert all(not a["id"].startswith("default") for a in catalog.search_articles("well-being"))
    assert catalog.search_articles("zzqx") == []


def test_save_writes_to_outbox(tmp_path):
    outbox = tmp_path / "recs.jsonl"
    catalog.save_recommendation("R1", "physical-01", "sedentary day", outbox=outbox)
    assert '"article_id": "physical-01"' in outbox.read_text()


def test_guard_allows_search_and_safe_save():
    assert evaluate(SEARCH_TOOL, {"query": "walking"})[0]
    assert save("R2", "physical-01")[0]  # gentle walking is fine with hypertension


def test_guard_blocks_r2_safety_trap():
    allowed, reason = save("R2", "physical-08")
    assert not allowed
    assert "contraindicated for: hypertension" in reason and "high-intensity" in reason


def test_same_article_is_allowed_without_hypertension():
    assert save("R1", "physical-08")[0]  # the rule is report-specific, not a blocklist


def test_guard_blocks_unapproved_article():
    allowed, reason = save("R1", "physical-07")
    assert not allowed and "not approved" in reason


def test_guard_blocks_unknown_ids_tools_and_empty_reason():
    assert not save("R2", "nope")[0]
    assert not save("R9", "physical-01")[0]
    assert not save("R1", "physical-01", reason=" ")[0]
    assert not evaluate("Bash", {"command": "rm -rf /"})[0]


def test_hook_callback_shape():
    deny = asyncio.run(
        pre_tool_use_guard(
            {"tool_name": SAVE_TOOL,
             "tool_input": {"report_id": "R2", "article_id": "physical-09", "reason": "x"}},
            "toolu_1",
            None,
        )
    )
    out = deny["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse" and out["permissionDecision"] == "deny"
    allow = asyncio.run(
        pre_tool_use_guard({"tool_name": SEARCH_TOOL, "tool_input": {"query": "x"}}, "t", None)
    )
    assert allow == {}


def test_sdk_options_wire_guard_and_limits():
    from health_agent.agent import build_options

    opts = build_options()
    assert opts.max_turns == 6 and opts.tools == []
    assert "PreToolUse" in opts.hooks and "health" in opts.mcp_servers
