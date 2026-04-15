"""Create BigQuery dataset and tables for the monitoring agent."""

from __future__ import annotations

import sys

from google.cloud import bigquery
from google.cloud.exceptions import Conflict

from config.settings import get_settings


RAW_EVENTS_SCHEMA = [
    bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("service", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("raw_payload", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("metadata", "JSON"),
    bigquery.SchemaField("processed", "BOOL", default_value_expression="FALSE"),
]

ENRICHED_EVENTS_SCHEMA = [
    bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("event_type", "STRING"),
    bigquery.SchemaField("severity", "STRING"),
    bigquery.SchemaField("classification_confidence", "FLOAT"),
    bigquery.SchemaField("classification_method", "STRING"),
    bigquery.SchemaField("extracted_summary", "STRING"),
    bigquery.SchemaField("is_anomaly", "BOOL"),
    bigquery.SchemaField("z_score", "FLOAT"),
    bigquery.SchemaField("root_cause", "STRING"),
    bigquery.SchemaField("risk_score", "INTEGER"),
    bigquery.SchemaField("risk_level", "STRING"),
    bigquery.SchemaField("recommendations", "JSON"),
    bigquery.SchemaField("pipeline_run_id", "STRING"),
    bigquery.SchemaField("prompt_version", "STRING"),
]

LLM_CALLS_SCHEMA = [
    bigquery.SchemaField("call_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("step", "STRING"),
    bigquery.SchemaField("provider", "STRING"),
    bigquery.SchemaField("model_id", "STRING"),
    bigquery.SchemaField("input_tokens", "INTEGER"),
    bigquery.SchemaField("output_tokens", "INTEGER"),
    bigquery.SchemaField("estimated_cost_usd", "FLOAT"),
    bigquery.SchemaField("latency_ms", "FLOAT"),
    bigquery.SchemaField("success", "BOOL"),
    bigquery.SchemaField("parse_success", "BOOL"),
    bigquery.SchemaField("fallback_used", "BOOL"),
]


def create_schema() -> None:
    settings = get_settings()

    if not settings.gcp_project_id:
        print("❌ GCP_PROJECT_ID não configurado. Defina no .env")
        sys.exit(1)

    client = bigquery.Client(project=settings.gcp_project_id)
    dataset_id = f"{settings.gcp_project_id}.{settings.bq_dataset}"

    # --- Dataset ---
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    try:
        client.create_dataset(dataset, exists_ok=True)
        print(f"✅ Dataset: {dataset_id}")
    except Exception as e:
        print(f"❌ Erro ao criar dataset: {e}")
        sys.exit(1)

    # --- Tables ---
    tables = [
        (settings.bq_raw_table, RAW_EVENTS_SCHEMA),
        (settings.bq_enriched_table, ENRICHED_EVENTS_SCHEMA),
        (settings.bq_llm_calls_table, LLM_CALLS_SCHEMA),
    ]

    for table_name, schema in tables:
        table_id = f"{dataset_id}.{table_name}"
        table = bigquery.Table(table_id, schema=schema)
        try:
            client.create_table(table, exists_ok=True)
            print(f"✅ Tabela: {table_id}")
        except Exception as e:
            print(f"❌ Erro ao criar tabela {table_id}: {e}")
            sys.exit(1)

    print("\n🎉 Schema criado com sucesso!")


if __name__ == "__main__":
    create_schema()
