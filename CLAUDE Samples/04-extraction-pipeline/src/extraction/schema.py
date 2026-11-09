"""Two layers of schema, on purpose.

Target: the metadata fields of the canonical catalog
(Sample-Data-Health-Content/sample-data/articles.json), so extracted vendor articles
could be added to it.

1. TOOL_SCHEMA: JSON Schema sent to Claude with `strict: true` + forced tool_choice.
   Guarantees SHAPE: right keys, right types, enums respected, no extra fields.
2. ArticleMetadata (Pydantic): enforces what shape can't, i.e. ranges, lengths and
   cross-field rules. Its error messages are fed back to the model on retry.

The tag vocabulary is read from the canonical catalog, not hard-coded: one source of
truth, so the extractor can't drift from the data the other POCs use.
Grounding checks that need the SOURCE text live in validate.py.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import sample_data

CATEGORIES = ["physical", "mental", "wellbeing"]
INTENSITIES = ["low", "medium", "high"]


def tag_vocabulary() -> list[str]:
    tags: set[str] = set()
    for a in sample_data.articles().values():
        tags.update(a["condition_tags"])
        tags.update(a["contraindications"])
    return sorted(tags)


TAGS = tag_vocabulary()


class ArticleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=5, max_length=120)
    summary: str = Field(min_length=20, max_length=300)
    category: Literal["physical", "mental", "wellbeing"]
    condition_tags: list[str] = Field(min_length=1, max_length=4)
    intensity: Literal["low", "medium", "high"]
    contraindications: list[str] = Field(default_factory=list)
    evidence_quote: str | None = Field(
        default=None, description="Verbatim sentence from the source supporting intensity."
    )
    author: str | None = None  # null when absent: never invent
    confidence: float = Field(ge=0.0, le=1.0)
    uncertain_fields: list[str] = Field(default_factory=list)

    @field_validator("condition_tags", "contraindications")
    @classmethod
    def known_tags(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - set(TAGS))
        if unknown:
            raise ValueError(f"unknown tags {unknown}; allowed: {TAGS}")
        if len(set(value)) != len(value):
            raise ValueError("contains duplicates")
        return value

    @model_validator(mode="after")
    def cross_field_rules(self) -> "ArticleMetadata":
        if self.intensity == "high" and not self.contraindications:
            raise ValueError(
                "intensity is 'high' but contraindications is empty; high-intensity "
                "content must declare who should avoid it (catalog convention)"
            )
        unknown = set(self.uncertain_fields) - set(type(self).model_fields)
        if unknown:
            raise ValueError(f"uncertain_fields names unknown fields: {sorted(unknown)}")
        return self


TOOL_NAME = "record_article_metadata"

TOOL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "summary", "category", "condition_tags", "intensity",
        "contraindications", "evidence_quote", "author", "confidence", "uncertain_fields",
    ],
    "properties": {
        "title": {"type": "string", "description": "Article title, cleaned of markup."},
        "summary": {"type": "string", "description": "One or two sentences, 20-300 characters."},
        "category": {"type": "string", "enum": CATEGORIES},
        "condition_tags": {"type": "array", "items": {"type": "string", "enum": TAGS},
                           "description": "1-4 tags for who the article is relevant to."},
        "intensity": {"type": "string", "enum": INTENSITIES,
                      "description": "Physical or emotional demand of what the article suggests."},
        "contraindications": {"type": "array", "items": {"type": "string", "enum": TAGS},
                              "description": "Tags of people who should NOT be shown this article."},
        "evidence_quote": {"type": ["string", "null"],
                           "description": "Copy ONE sentence verbatim from the source that justifies the intensity."},
        "author": {"type": ["string", "null"],
                   "description": "Author name if stated in the source, else null. Never guess."},
        "confidence": {"type": "number", "description": "0-1, your confidence in the whole record."},
        "uncertain_fields": {"type": "array", "items": {"type": "string"},
                             "description": "Names of fields you were unsure about."},
    },
}

TOOL = {
    "name": TOOL_NAME,
    "description": "Record structured catalog metadata extracted from one vendor article.",
    "input_schema": TOOL_SCHEMA,
    "strict": True,
}
