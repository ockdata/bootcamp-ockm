"""Upload an Excel file to BigQuery."""
import pandas as pd
from shared.bq import load_to_bigquery
from shared.gcs import save_to_raw


def main(file_path: str, dataset: str, table: str):
    df = pd.read_excel(file_path)
    uri = save_to_raw(df, dataset_name=table)
    load_to_bigquery(uri, dataset, table)


if __name__ == "__main__":
    import sys
    main(sys.argv[1], sys.argv[2], sys.argv[3])
