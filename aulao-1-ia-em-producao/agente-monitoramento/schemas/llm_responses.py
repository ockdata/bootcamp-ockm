"""Pydantic models for structured LLM responses.
1. Field(description=...) — descriptions viajam no JSON schema para o LLM
2. @field_validator — validacao por campo com auto-correcao
3. @model_validator(mode="after") — cross-field domain logic
4. max_length — limita tamanho de strings geradas pelo LLM
5. @computed_field — property derivada que aparece em model_dump() mas NAO no schema enviado ao LLM
6. Literal + ge/le — enums e ranges numericos enforced pelo schema
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class ClassificationResult(BaseModel):
    """LLM output: event classification."""

    event_type: Literal["log", "metric_alert", "app_error", "deploy", "unknown"] = Field(
        default="unknown",
        description=(
            "Tipo do evento: 'app_error' para erros, 'metric_alert' para alertas "
            "de metricas, 'deploy' para deploys, 'log' para informativos."
        ),
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        default="low",
        description=(
            "Severidade: 'critical' para OOM/fatal, 'high' para 5xx/errors, "
            "'medium' para warnings, 'low' para info."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="Confianca de 0.0 a 1.0. Use < 0.3 se nao conseguir determinar.",
    )
    reasoning: str = Field(
        default="",
        max_length=500,
        description="Justificativa curta da classificacao em 1-2 frases.",
    )

    @field_validator("reasoning")
    @classmethod
    def reasoning_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            return "Classificacao sem justificativa."
        return v.strip()

    @model_validator(mode="after")
    def check_severity_coherence(self) -> ClassificationResult:
        if self.event_type == "log" and self.severity in ("critical", "high"):
            self.confidence = min(self.confidence, 0.4)
            self.reasoning += " [ajustado: log + sev alta = confianca reduzida]"
        if self.event_type == "unknown" and self.confidence > 0.5:
            self.confidence = 0.3
        return self


class ExtractionResult(BaseModel):
    """LLM output: structured extraction from raw event."""

    summary: str = Field(
        default="",
        max_length=500,
        description="Resumo conciso do evento em 1-2 frases.",
    )
    affected_component: str = Field(
        default="",
        max_length=200,
        description="Componente ou servico afetado (ex: 'api-gateway', 'database').",
    )
    error_code: str = Field(
        default="",
        max_length=100,
        description="Codigo de erro se presente (ex: 'HTTP 500', 'OOMKilled', 'TIMEOUT').",
    )
    user_impact: str = Field(
        default="",
        max_length=300,
        description="Impacto percebido pelo usuario final.",
    )
    key_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Metricas relevantes como dicionario (ex: {'latency_ms': '450', 'error_rate': '12%'}).",
    )


class RootCauseResult(BaseModel):
    """LLM output: root cause analysis."""

    root_cause: str = Field(
        default="",
        max_length=500,
        description="Causa raiz provavel em 1-2 frases curtas.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.5,
        description="Confianca de 0.0 a 1.0 na analise de causa raiz.",
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Ate 5 fatores contribuintes, cada um com no maximo 10 palavras.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Ate 5 acoes recomendadas, cada uma com no maximo 10 palavras.",
    )
    similar_incidents: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Ate 5 incidentes similares conhecidos.",
    )

    @field_validator("contributing_factors", "recommendations")
    @classmethod
    def truncate_items(cls, v: list[str]) -> list[str]:
        return [item[:200] for item in v[:5]]

    @computed_field
    @property
    def has_actionable_recommendations(self) -> bool:
        """True se ha recomendacoes acionaveis com confianca suficiente."""
        return len(self.recommendations) > 0 and self.confidence >= 0.5
