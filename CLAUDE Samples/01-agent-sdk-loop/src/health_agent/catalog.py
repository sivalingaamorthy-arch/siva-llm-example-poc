"""Pure-Python business logic for the two tools, over the canonical sample data.

Kept free of SDK imports on purpose: the same functions back the Agent SDK tools
(agent.py) and the hand-written Messages API loop (manual_loop.py), and they are
trivially unit-testable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import sample_data

DEFAULT_OUTBOX = Path("output") / "recommendations.jsonl"


def search_articles(query: str, limit: int = 5) -> list[dict]:
    """Naive keyword search over title, category, condition tags and body.

    Deliberately returns unsafe candidates too (e.g. HIIT for "get fitter quickly"):
    filtering is the guard's job, so the demo can show the guard working.
    """
    terms = [t for t in query.lower().replace("_", " ").split() if len(t) > 2]
    scored: list[tuple[int, dict]] = []
    for a in sample_data.articles().values():
        if a["is_default"]:
            continue
        haystack = " ".join(
            [a["title"], a["category"], " ".join(a["condition_tags"]).replace("_", " "), a["body"]]
        ).lower()
        score = sum(haystack.count(t) for t in terms)
        if score:
            scored.append((score, a))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {k: a[k] for k in ("id", "title", "category", "condition_tags", "intensity")}
        for _, a in scored[:limit]
    ]


def save_recommendation(
    report_id: str, article_id: str, reason: str, outbox: Path | None = None
) -> dict:
    """The side-effecting tool. This is what the PreToolUse guard protects."""
    outbox = outbox or DEFAULT_OUTBOX
    record = {
        "report_id": report_id,
        "article_id": article_id,
        "reason": reason,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    outbox.parent.mkdir(parents=True, exist_ok=True)
    with outbox.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record
