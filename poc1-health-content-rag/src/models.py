from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["physical", "mental", "wellbeing"]
Intensity = Literal["low", "medium", "high"]
Source = Literal["vendor", "Everwell"]


class Article(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    body: str = Field(min_length=1)
    category: Category
    condition_tags: list[str]
    intensity: Intensity
    contraindications: list[str]
    source: Source
    approved: bool
    is_default: bool
    published_date: date


class HealthReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    age: int = Field(ge=18, le=120)
    sex: str
    bmi: float = Field(gt=0, le=100)
    blood_pressure: str
    fasting_glucose_mmol: float = Field(gt=0, le=100)
    sleep_hours: float = Field(ge=0, le=24)
    stress_level: Literal["low", "moderate", "high"]
    activity: str
    notes: str = ""


class Recommendation(BaseModel):
    article: Article
    similarity: float


class PipelineResult(BaseModel):
    report_id: str
    generated_at: datetime
    generation_model: str
    embedding_model: str
    markers: list[str]
    physical: list[Recommendation]
    mental: list[Recommendation]
    summary: str
