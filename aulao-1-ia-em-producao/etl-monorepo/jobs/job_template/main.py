from shared.gcs import save_to_raw
from shared.bq import load_to_bigquery


def extract():
    # TODO: implement extraction logic
    raise NotImplementedError


def main():
    df = extract()
    uri = save_to_raw(df, dataset_name="dataset_name")
    load_to_bigquery(uri, "trusted", "table_name")


if __name__ == "__main__":
    main()
