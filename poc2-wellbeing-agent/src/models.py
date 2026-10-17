from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["physical", "mental", "wellbeing"]
Source = Literal["vendor", "Everwell"]


class Article(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    body: str = Field(min_length=1)
    category: Category
    condition_tags: list[str]
    intensity: Literal["low", "medium", "high"]
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


class Candidate(BaseModel):
    article: Article
    similarity: float


class JudgeVerdict(BaseModel):
    verdict: Literal["pass", "fail"]
    rejected_ids: list[str] = Field(default_factory=list)
    feedback: str
    uncovered_topics: list[str] = Field(default_factory=list)


class TraceEvent(BaseModel):
    attempt: int
    node: str
    message: str
    article_ids: list[str] = Field(default_factory=list)
    verdict: str | None = None
    elapsed_ms: int


class AgentResult(BaseModel):
    report_id: str
    framework: Literal["langchain", "langgraph", "agno"]
    generated_at: datetime
    generation_model: str
    embedding_model: str
    markers: list[str]
    unmatched_topics: list[str]
    retry_count: int
    used_fallback: bool
    physical: list[Candidate]
    mental: list[Candidate]
    summary: str
    trace: list[TraceEvent]
