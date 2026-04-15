from google.cloud import storage
import pandas as pd
import io
import os
from datetime import date


def save_to_raw(df: pd.DataFrame, dataset_name: str, bucket: str = None) -> str:
    """Save a DataFrame as Parquet to the GCS raw layer. Returns the GCS URI."""
    bucket = bucket or os.environ["GCS_BUCKET"]
    project = os.environ["GCP_PROJECT"]
    today = date.today().isoformat()
    blob_path = f"raw/{dataset_name}/{today}/{dataset_name}.parquet"

    client = storage.Client(project=project)
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    client.bucket(bucket).blob(blob_path).upload_from_file(buffer, content_type="application/octet-stream")

    uri = f"gs://{bucket}/{blob_path}"
    print(f"Saved to {uri}")
    return uri
