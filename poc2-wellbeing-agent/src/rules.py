from src.models import Candidate, HealthReport, JudgeVerdict


def validate_rules(
    report: HealthReport,
    markers: list[str],
    unmatched_topics: list[str],
    physical: list[Candidate],
    mental: list[Candidate],
) -> JudgeVerdict:
    candidates = [*physical, *mental]
    rejected: list[str] = []
    reasons: list[str] = []
    for candidate in candidates:
        article = candidate.article
        unsafe_tags = sorted(set(article.contraindications).intersection(markers))
        if not article.approved:
            rejected.append(article.id)
            reasons.append(f"{article.id} is not approved")
        if article.is_default:
            rejected.append(article.id)
            reasons.append(f"{article.id} is a fallback default, not a candidate")
        expected_category = "physical" if candidate in physical else "mental"
        if article.category != expected_category:
            rejected.append(article.id)
            reasons.append(f"{article.id} has wrong category {article.category}")
        if unsafe_tags:
            rejected.append(article.id)
            reasons.append(f"{article.id} contraindicated for {', '.join(unsafe_tags)}")
        if (
            "hypertension" in markers
            and article.category == "physical"
            and article.intensity == "high"
        ):
            rejected.append(article.id)
            reasons.append(f"{article.id} is high-intensity with hypertension marker")
    if len(physical) != 3:
        reasons.append(f"Expected 3 physical articles; got {len(physical)}")
    if len(mental) != 3:
        reasons.append(f"Expected 3 mental articles; got {len(mental)}")
    if unmatched_topics:
        reasons.append(
            "No article catalog coverage for unmatched topics: "
            + ", ".join(unmatched_topics)
        )
    return JudgeVerdict(
        verdict="fail" if reasons else "pass",
        rejected_ids=sorted(set(rejected)),
        feedback="; ".join(reasons) if reasons else "Deterministic safety and shape rules passed.",
        uncovered_topics=unmatched_topics,
    )
