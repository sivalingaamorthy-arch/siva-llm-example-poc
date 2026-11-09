"""Extract -> validate -> (retry with errors) -> route.

Run (offline):  python -m extraction.pipeline --mock
Run (live):     ANTHROPIC_API_KEY=... python -m extraction.pipeline
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .llm import AnthropicExtractor, Extractor, ScriptedExtractor
from .schema import ArticleMetadata
from .validate import validate

ROOT = Path(__file__).resolve().parents[2]
MAX_ATTEMPTS = 3            # 1 try + 2 retries; beyond that retries rarely help
AUTO_APPROVE_CONFIDENCE = 0.85

Route = Literal["auto_approved", "human_review"]


@dataclass
class Outcome:
    doc_id: str
    route: Route
    reasons: list[str]
    attempts: int
    record: dict[str, Any] | None = None
    last_errors: list[str] = field(default_factory=list)


def build_prompt(doc_id: str, text: str) -> str:
    return f"doc_id={doc_id}\n<article>\n{text}\n</article>"


def extract_with_retry(
    extractor: Extractor, doc_id: str, text: str, max_attempts: int = MAX_ATTEMPTS
) -> tuple[ArticleMetadata | None, int, list[str]]:
    base_prompt = build_prompt(doc_id, text)
    messages: list[dict[str, Any]] = [{"role": "user", "content": base_prompt}]
    errors: list[str] = []
    for attempt in range(1, max_attempts + 1):
        raw = extractor.extract(messages)
        record, errors = validate(raw, text)
        if record:
            return record, attempt, []
        # Retry with SPECIFIC feedback: original document + previous answer + each
        # error. A bare "try again" just samples the same mistake again.
        feedback = (
            "\n\nYour previous extraction failed validation.\n"
            f"Previous answer:\n{json.dumps(raw, indent=2)}\n"
            "Errors to fix:\n- " + "\n- ".join(errors) + "\n"
            "Return a corrected record. Keep the fields that were valid."
        )
        messages = [{"role": "user", "content": base_prompt + feedback}]
    return None, max_attempts, errors


def route(record: ArticleMetadata) -> tuple[Route, list[str]]:
    reasons = []
    if record.contraindications:
        reasons.append(f"declares contraindications: {', '.join(record.contraindications)}")
    if record.intensity == "high":
        reasons.append("high-intensity content needs a reviewer")
    if record.confidence < AUTO_APPROVE_CONFIDENCE:
        reasons.append(f"confidence {record.confidence:.2f} < {AUTO_APPROVE_CONFIDENCE}")
    if record.uncertain_fields:
        reasons.append(f"model unsure about: {', '.join(record.uncertain_fields)}")
    return ("human_review", reasons) if reasons else ("auto_approved", ["all checks passed"])


def process(extractor: Extractor, doc_id: str, text: str) -> Outcome:
    record, attempts, errors = extract_with_retry(extractor, doc_id, text)
    if record is None:
        return Outcome(doc_id, "human_review", [f"validation failed after {attempts} attempts"],
                       attempts, None, errors)
    decision, reasons = route(record)
    return Outcome(doc_id, decision, reasons, attempts, record.model_dump())


def run(extractor: Extractor, raw_dir: Path, out_dir: Path) -> list[Outcome]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outcomes = [process(extractor, p.stem, p.read_text("utf-8")) for p in sorted(raw_dir.glob("*.txt"))]
    for name in ("auto_approved", "human_review"):
        with (out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for o in outcomes:
                if o.route == name:
                    fh.write(json.dumps(asdict(o)) + "\n")
    return outcomes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="use scripted fixtures, no API key")
    ap.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT / "output")
    args = ap.parse_args()
    extractor = ScriptedExtractor(ROOT / "data" / "fixtures") if args.mock else AnthropicExtractor()
    outcomes = run(extractor, args.raw, args.out)
    for o in outcomes:
        print(f"{o.doc_id:<28} {o.route:<14} attempts={o.attempts}  {'; '.join(o.reasons)}")
    auto = sum(o.route == "auto_approved" for o in outcomes)
    print(f"\n{auto}/{len(outcomes)} auto-approved; review queue -> {args.out / 'human_review.jsonl'}")


if __name__ == "__main__":
    main()
