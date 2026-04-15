"""Step 6: Deterministic risk scoring — no LLM, fully reproducible."""

from __future__ import annotations

from schemas.alerts import RiskScore

# Severity weights (0-40 points)
_SEVERITY_SCORES: dict[str, int] = {
    "critical": 40,
    "high": 28,
    "medium": 15,
    "low": 5,
}

# Event type weights (0-15 points)
_TYPE_SCORES: dict[str, int] = {
    "app_error": 15,
    "metric_alert": 12,
    "deploy": 8,
    "log": 3,
    "unknown": 5,
}

# Service criticality weights (0-15 points)
_SERVICE_CRITICALITY: dict[str, int] = {
    "checkout": 15,
    "payments": 15,
    "auth": 12,
    "inventory": 10,
    "api-gateway": 12,
    "frontend": 8,
    "notifications": 5,
}
_DEFAULT_SERVICE_SCORE = 7


def compute_risk_score(
    severity: str,
    event_type: str,
    service: str,
    is_anomaly: bool,
    z_score: float,
    classification_confidence: float,
) -> RiskScore:
    """Compute a deterministic risk score from 0-100.

    Formula:
        base = severity_score + type_score + service_score
        anomaly_bonus = 20 if is_anomaly else 0
        z_bonus = min(10, abs(z_score) * 3)  if is_anomaly
        confidence_modifier = confidence * 0.5 (slightly reduces if low confidence)
        final = clamp(base + anomaly_bonus + z_bonus - confidence_penalty, 0, 100)
    """
    factors: dict[str, float] = {}

    # Base severity
    sev_score = _SEVERITY_SCORES.get(severity, 5)
    factors["severity"] = sev_score

    # Event type
    type_score = _TYPE_SCORES.get(event_type, 5)
    factors["event_type"] = type_score

    # Service criticality
    svc_score = _SERVICE_CRITICALITY.get(service, _DEFAULT_SERVICE_SCORE)
    factors["service_criticality"] = svc_score

    # Anomaly bonus
    anomaly_bonus = 0.0
    if is_anomaly:
        anomaly_bonus = 20.0 + min(10.0, abs(z_score) * 3.0)
    factors["anomaly_bonus"] = anomaly_bonus

    # Low confidence penalty (reduces score if we're not sure)
    confidence_penalty = max(0.0, (1.0 - classification_confidence) * 10.0)
    factors["confidence_penalty"] = -confidence_penalty

    raw_score = sev_score + type_score + svc_score + anomaly_bonus - confidence_penalty
    final_score = max(0, min(100, int(round(raw_score))))

    level = RiskScore.level_from_score(final_score)

    return RiskScore(score=final_score, level=level, factors=factors)
