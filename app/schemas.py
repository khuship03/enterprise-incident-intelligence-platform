from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=5, max_length=180, examples=["Production API requests timing out"])
    description: str = Field(
        min_length=15,
        max_length=12000,
        examples=["Since 14:10 UTC, requests to the checkout API are timing out. Several users cannot complete purchases after the latest deployment."],
    )
    service: str = Field(default="Unknown service", min_length=2, max_length=120)
    source: str = Field(default="manual", min_length=2, max_length=80)


class IncidentView(BaseModel):
    id: str
    title: str
    description: str
    service: str
    source: str
    status: str
    created_at: str
    updated_at: str
    summary: str | None = None
    category: str | None = None
    severity: str | None = None
    confidence: float | None = None
    key_symptoms: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    retrieved_runbooks: list[dict] = Field(default_factory=list)
    assigned_group: str | None = None
    needs_human_review: bool = False
    analysis_provider: str | None = None
    triage_notes: str | None = None
    error_message: str | None = None
    reviewed_by: str | None = None
    review_notes: str | None = None
    reviewed_at: str | None = None
    processing_attempts: int = 0


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reviewed_by: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=2000)


class MetricsView(BaseModel):
    total_incidents: int
    status_counts: dict[str, int]
    category_counts: dict[str, int]
    severity_counts: dict[str, int]
    incidents_requiring_review: int
