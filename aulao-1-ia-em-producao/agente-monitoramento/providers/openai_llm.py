from __future__ import annotations

import time
from typing import Type, TypeVar

import instructor
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from observability.logger import get_logger

log = get_logger(__name__)
T = TypeVar("T")


class OpenAILLM:
    """OpenAI GPT as fallback provider via Instructor. Implements LLMProvider protocol."""

    provider_name: str = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.model_id = model
        self._raw_client = AsyncOpenAI(api_key=api_key)
        self._client = instructor.from_openai(self._raw_client)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=8),
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

        parsed, completion = await self._client.chat.completions.create_with_completion(
            model=self.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
            max_retries=2,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        input_tokens = completion.usage.prompt_tokens if completion.usage else 0
        output_tokens = completion.usage.completion_tokens if completion.usage else 0

        log.info(
            "openai.generate.success",
            model=self.model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 2),
        )

        parsed._openai_usage = {  # type: ignore[attr-defined]
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(latency_ms, 2),
        }

        return parsed
