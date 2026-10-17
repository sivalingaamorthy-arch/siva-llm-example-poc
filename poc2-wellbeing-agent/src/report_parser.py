import re

from src.errors import PocError
from src.models import HealthReport

_BP = re.compile(r"^\s*(\d{2,3})/(\d{2,3})\s*$")
TOPIC_PATTERNS = {
    "postpartum": re.compile(r"\bpost[- ]?partum\b|\bafter (?:giving )?birth\b", re.I),
    "pregnancy": re.compile(r"\bpregnan(?:t|cy)\b", re.I),
}


def parse_report(report: HealthReport) -> tuple[list[str], list[str]]:
    match = _BP.fullmatch(report.blood_pressure)
    if not match:
        raise PocError(
            f"Report {report.report_id} has invalid blood_pressure; expected values "
            "such as 120/80."
        )
    systolic, diastolic = map(int, match.groups())
    markers = set()
    if report.bmi >= 30:
        markers.add("high_bmi")
    if systolic >= 140 or diastolic >= 90:
        markers.add("hypertension")
    if 5.6 <= report.fasting_glucose_mmol <= 6.9:
        markers.add("prediabetes")
    if report.sleep_hours < 6:
        markers.add("poor_sleep")
    if report.stress_level == "high":
        markers.add("stress")
    if report.activity.strip().lower() == "sedentary":
        markers.add("sedentary")
    notes = report.notes.lower()
    topics = sorted(topic for topic, pattern in TOPIC_PATTERNS.items() if pattern.search(notes))
    return sorted(markers), topics
