from __future__ import annotations

import time
from typing import Type, TypeVar

import anthropic
import instructor
from tenacity import retry, stop_after_attempt, wait_exponential

from observability.logger import get_logger

log = get_logger(__name__)
T = TypeVar("T")


class AnthropicLLM:
    """Claude LLM provider via Anthropic SDK + Instructor. Implements LLMProvider protocol."""

    provider_name: str = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.model_id = model
        self._raw_client = anthropic.AsyncAnthropic(api_key=api_key)
        self._client = instructor.from_anthropic(self._raw_client)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        response_model: Type[T],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> T:
        start = time.perf_counter()

        parsed, completion = await self._client.messages.create_with_completion(
            model=self.model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
            max_retries=2,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        log.info(
            "anthropic.generate.success",
            model=self.model_id,
            input_tokens=completion.usage.input_tokens,
            output_tokens=completion.usage.output_tokens,
            latency_ms=round(latency_ms, 2),
        )

        # Attach usage metadata for metrics collection
        parsed._anthropic_usage = {  # type: ignore[attr-defined]
            "input_tokens": completion.usage.input_tokens,
            "output_tokens": completion.usage.output_tokens,
            "latency_ms": round(latency_ms, 2),
        }

        return parsed
