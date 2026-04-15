"""Environment-driven configuration using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_primary_model: str = "claude-sonnet-4-20250514"
    llm_fallback_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # --- BigQuery ---
    gcp_project_id: str = ""
    bq_dataset: str = "monitoring_agent"
    bq_raw_table: str = "raw_events"
    bq_enriched_table: str = "enriched_events"
    bq_llm_calls_table: str = "llm_calls"

    # --- RAG ---
    rag_top_k: int = 5
    rag_data_dir: str = "rag_data"

    # --- Alerting ---
    slack_webhook_url: str = ""
    alert_risk_threshold: int = 60

    # --- Pipeline ---
    pipeline_batch_size: int = 10
    pipeline_mode: Literal["full", "dry"] = "full"
    prompt_version: str = "v1"

    # --- Continuous mode ---
    continuous_interval_seconds: int = 300
    continuous_event_count: int = 10
    anomaly_state_file: str = ".anomaly_state.json"

    # --- Observability ---
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    @property
    def is_dry_run(self) -> bool:
        return self.pipeline_mode == "dry"

    @property
    def bq_raw_table_id(self) -> str:
        return f"{self.gcp_project_id}.{self.bq_dataset}.{self.bq_raw_table}"

    @property
    def bq_enriched_table_id(self) -> str:
        return f"{self.gcp_project_id}.{self.bq_dataset}.{self.bq_enriched_table}"

    @property
    def bq_llm_calls_table_id(self) -> str:
        return f"{self.gcp_project_id}.{self.bq_dataset}.{self.bq_llm_calls_table}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
