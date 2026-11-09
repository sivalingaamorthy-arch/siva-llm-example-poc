"""Access to the repository's canonical health-content sample data.

Reads Sample-Data-Health-Content/sample-data (articles + R1-R3 reports) instead of
keeping a private copy, as the repo's data README requires. Override the location
with HEALTH_CONTENT_SAMPLE_DATA.

Marker thresholds mirror RAG Samples/src/report_parser.py so every POC derives the
same markers from the same report.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

REPORT_FILES = {
    "R1": "report1_happy_path.json",
    "R2": "report2_safety_trap.json",
    "R3": "report3_content_gap.json",
}
_BP = re.compile(r"^\s*(\d{2,3})/(\d{2,3})\s*$")


def sample_data_root() -> Path:
    override = os.environ.get("HEALTH_CONTENT_SAMPLE_DATA")
    if override:
        return Path(override).resolve()
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "Sample-Data-Health-Content" / "sample-data"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Sample-Data-Health-Content/sample-data not found above this file; "
        "set HEALTH_CONTENT_SAMPLE_DATA."
    )


@lru_cache(maxsize=1)
def articles() -> dict[str, dict[str, Any]]:
    data = json.loads((sample_data_root() / "articles.json").read_text("utf-8"))
    return {a["id"]: a for a in data}


def article(article_id: str) -> dict[str, Any] | None:
    return articles().get(article_id)


def report(report_id: str) -> dict[str, Any]:
    if report_id not in REPORT_FILES:
        raise KeyError(f"Unknown report_id '{report_id}'. Use one of {sorted(REPORT_FILES)}.")
    path = sample_data_root() / "reports" / REPORT_FILES[report_id]
    return json.loads(path.read_text("utf-8"))


def markers(report_data: dict[str, Any]) -> list[str]:
    match = _BP.fullmatch(report_data["blood_pressure"])
    if match is None:
        raise ValueError(f"Report {report_data.get('report_id')} has an invalid blood_pressure.")
    systolic, diastolic = map(int, match.groups())
    found: set[str] = set()
    if report_data["bmi"] >= 30:
        found.add("high_bmi")
    if systolic >= 140 or diastolic >= 90:
        found.add("hypertension")
    if 5.6 <= report_data["fasting_glucose_mmol"] <= 6.9:
        found.add("prediabetes")
    if report_data["sleep_hours"] < 6:
        found.add("poor_sleep")
    if report_data["stress_level"] == "high":
        found.add("stress")
    if report_data["activity"].strip().lower() == "sedentary":
        found.add("sedentary")
    return sorted(found)


def safety_violations(article_data: dict[str, Any], report_markers: list[str]) -> list[str]:
    """The R2 rule set, as plain reasons. Empty list = safe to recommend."""
    reasons = []
    if not article_data["approved"]:
        reasons.append("article is not approved for publication")
    blocked = sorted(set(article_data["contraindications"]) & set(report_markers))
    if blocked:
        reasons.append(f"article is contraindicated for: {', '.join(blocked)}")
    if article_data["intensity"] == "high" and "hypertension" in report_markers:
        reasons.append("high-intensity content is not allowed when hypertension is present")
    return reasons
