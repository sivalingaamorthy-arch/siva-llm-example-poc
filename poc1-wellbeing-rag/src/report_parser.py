import re

from src.errors import PocError
from src.models import HealthReport

_BLOOD_PRESSURE = re.compile(r"^\s*(\d{2,3})/(\d{2,3})\s*$")


def parse_report(report: HealthReport) -> list[str]:
    match = _BLOOD_PRESSURE.fullmatch(report.blood_pressure)
    if match is None:
        raise PocError(
            f"Report {report.report_id} has an invalid blood_pressure value; "
            "expected systolic/diastolic, for example 120/80."
        )
    systolic, diastolic = map(int, match.groups())
    markers: set[str] = set()
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
    return sorted(markers)
