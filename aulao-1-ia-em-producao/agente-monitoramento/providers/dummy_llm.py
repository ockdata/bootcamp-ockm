"""Deterministic dummy LLM for tests and offline demos."""

from __future__ import annotations

import time
from typing import Type, TypeVar

from schemas.llm_responses import (
    ClassificationResult,
    ExtractionResult,
    RootCauseResult,
)

T = TypeVar("T")

# Keyword-based heuristic mapping
_SEVERITY_KEYWORDS: dict[str, str] = {
    "critical": "critical",
    "fatal": "critical",
    "OOMKilled": "critical",
    "error": "high",
    "exception": "high",
    "5xx": "high",
    "timeout": "high",
    "warning": "medium",
    "warn": "medium",
    "slow": "medium",
    "latency": "medium",
    "info": "low",
    "deploy": "low",
    "success": "low",
}

_TYPE_KEYWORDS: dict[str, str] = {
    "deploy": "deploy",
    "release": "deploy",
    "rollback": "deploy",
    "cpu": "metric_alert",
    "memory": "metric_alert",
    "latency": "metric_alert",
    "p99": "metric_alert",
    "error": "app_error",
    "exception": "app_error",
    "traceback": "app_error",
    "panic": "app_error",
}


def _match_keyword(text: str, mapping: dict[str, str], default: str) -> str:
    text_lower = text.lower()
    for keyword, value in mapping.items():
        if keyword.lower() in text_lower:
            return value
    return default


def _extract_payload(prompt: str) -> str:
    """Extract the Payload section from a formatted prompt, falling back to full text."""
    lines = prompt.split("\n")
    in_payload = False
    payload_lines: list[str] = []

    for line in lines:
        if line.strip().startswith("Payload:"):
            in_payload = True
            continue
        if in_payload:
            if line.strip() == "---" or line.strip().startswith("Metadata:"):
                break
            payload_lines.append(line)

    return "\n".join(payload_lines).strip() if payload_lines else prompt


class DummyLLM:
    """Deterministic LLM that uses keyword heuristics. Implements LLMProvider protocol."""

    provider_name: str = "dummy"
    model_id: str = "dummy-heuristic-v1"

    async def generate(
        self,
        prompt: str,
        response_model: Type[T],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> T:
        start = time.perf_counter()

        if response_model is ClassificationResult:
            result = self._classify(prompt)
        elif response_model is ExtractionResult:
            result = self._extract(prompt)
        elif response_model is RootCauseResult:
            result = self._root_cause(prompt)
        else:
            result = response_model()

        _ = (time.perf_counter() - start) * 1000
        return result  # type: ignore[return-value]

    def _classify(self, prompt: str) -> ClassificationResult:
        payload = _extract_payload(prompt)
        severity = _match_keyword(payload, _SEVERITY_KEYWORDS, "low")
        event_type = _match_keyword(payload, _TYPE_KEYWORDS, "log")
        return ClassificationResult(
            event_type=event_type,
            severity=severity,
            confidence=0.85,
            reasoning="Heuristic classification based on keyword matching",
        )

    def _extract(self, prompt: str) -> ExtractionResult:
        lines = prompt.strip().split("\n")
        payload_line = ""
        for line in lines:
            if "payload" in line.lower() or "event" in line.lower():
                payload_line = line
                break
        if not payload_line and lines:
            payload_line = lines[-1]

        return ExtractionResult(
            summary=f"Event detected: {payload_line[:120]}",
            affected_component=_match_keyword(
                prompt,
                {"checkout": "checkout", "payment": "payments", "inventory": "inventory"},
                "unknown",
            ),
            error_code=_match_keyword(
                prompt,
                {"500": "HTTP 500", "502": "HTTP 502", "503": "HTTP 503", "OOM": "OOMKilled"},
                "",
            ),
            user_impact=_match_keyword(
                prompt,
                {"timeout": "Users experiencing timeouts", "error": "Users seeing errors"},
                "No direct user impact detected",
            ),
        )

    def _root_cause(self, prompt: str) -> RootCauseResult:
        cause = "Unable to determine root cause from available data"
        recommendations = ["Investigate logs further", "Check recent deployments"]

        if "memory" in prompt.lower() or "oom" in prompt.lower():
            cause = "Memory leak or insufficient memory allocation"
            recommendations = [
                "Increase memory limits",
                "Profile application memory usage",
                "Check for memory leaks in recent changes",
            ]
        elif "cpu" in prompt.lower():
            cause = "CPU saturation due to high load or inefficient processing"
            recommendations = [
                "Scale horizontally",
                "Profile CPU-intensive code paths",
                "Check for runaway processes",
            ]
        elif "5xx" in prompt.lower() or "500" in prompt.lower():
            cause = "Application errors causing 5xx responses"
            recommendations = [
                "Check application logs for stack traces",
                "Review recent deployments",
                "Verify downstream service health",
            ]
        elif "deploy" in prompt.lower():
            cause = "Recent deployment may have introduced issues"
            recommendations = [
                "Compare metrics before and after deploy",
                "Review changelog for breaking changes",
                "Consider rollback if issues persist",
            ]

        return RootCauseResult(
            root_cause=cause,
            confidence=0.7,
            contributing_factors=["Keyword-based heuristic analysis"],
            recommendations=recommendations,
            similar_incidents=[],
        )
