from google.cloud import bigquery
import os


def load_to_bigquery(gcs_uri: str, dataset: str, table: str) -> None:
    """Load a Parquet file from GCS into a BigQuery table."""
    project = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=project)

    table_ref = f"{project}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    load_job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    load_job.result()
    print(f"Loaded {gcs_uri} -> {table_ref}")
