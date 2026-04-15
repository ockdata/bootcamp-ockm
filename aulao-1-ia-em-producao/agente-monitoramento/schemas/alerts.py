from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class RiskScore(BaseModel):
    """Deterministic risk score for an event."""

    score: int = Field(ge=0, le=100, description="Risk score 0-100")
    level: Literal["low", "medium", "high", "critical"] = "low"
    factors: dict[str, float] = Field(
        default_factory=dict,
        description="Contributing factors and their weights",
    )

    @staticmethod
    def level_from_score(score: int) -> Literal["low", "medium", "high", "critical"]:
        if score >= 80:
            return "critical"
        if score >= 60:
            return "high"
        if score >= 35:
            return "medium"
        return "low"

    @model_validator(mode="after")
    def ensure_level_matches_score(self) -> RiskScore:
        expected = self.level_from_score(self.score)
        if self.level != expected:
            self.level = expected
        return self


class Alert(BaseModel):
    """An alert emitted by the pipeline."""

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_id: str
    service: str
    severity: str
    risk_score: int
    risk_level: str
    title: str
    summary: str
    root_cause: str = ""
    recommendations: list[str] = Field(default_factory=list)
    pipeline_run_id: str = ""
