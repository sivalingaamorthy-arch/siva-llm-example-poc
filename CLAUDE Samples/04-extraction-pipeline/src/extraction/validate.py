"""Validation = schema (Pydantic) + grounding checks against the source text."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from .schema import ArticleMetadata


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def validate(raw: dict[str, Any], source: str) -> tuple[ArticleMetadata | None, list[str]]:
    """Return (record, errors). errors are phrased as instructions for a retry."""
    try:
        record = ArticleMetadata.model_validate(raw)
    except ValidationError as exc:
        errors = []
        for e in exc.errors():
            loc = ".".join(str(p) for p in e["loc"]) or "record"
            errors.append(f"{loc}: {e['msg']}")
        return None, errors

    errors: list[str] = []
    if record.evidence_quote and _norm(record.evidence_quote) not in _norm(source):
        errors.append(
            "evidence_quote: not found verbatim in the source. Copy an exact sentence, "
            "or set it to null."
        )
    if record.author and _norm(record.author) not in _norm(source):
        errors.append("author: name does not appear in the source. Use null if no author is stated.")
    if record.intensity != "low" and not record.evidence_quote:
        errors.append("evidence_quote: required when intensity is 'medium' or 'high'.")

    return (record, []) if not errors else (None, errors)
