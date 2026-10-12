"""Lood the big trip file in chuncks and zone lookup table."""

from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

def find_input(raw_dir: Path) -> Path:
    """Return the yellow_tripdata file in raw_dir (Parquet is preferred over CSV)."""
    parquet = sorted(raw_dir.glob("yellow_tripdata*.parquet"))
    csv = sorted(raw_dir.glob("yellow_tripdata*.csv"))
    if parquet:
        return parquet[0]
    if csv:
        return csv[0]
    raise FileNotFoundError(f"No yellow_tripdata*.parquet or .csv found in {raw_dir}")


def iter_raw_chunks(path: Path, chunk_size: int):
    """Yield the raw trips as DataFrames of chunk_size rows, from a Parquet or a CSV file."""
    if path.suffix.lower() == ".parquet":
        for batch in pq.ParquetFile(path).iter_batches(batch_size=chunk_size):
            yield batch.to_pandas()
    else:
        yield from pd.read_csv(path, chunksize=chunk_size, low_memory=False)


def load_lookup(lookup_csv: Path) -> pd.DataFrame:
    """Read taxi_zone_lookup.csv.

    keep_default_na=False stops pandas from turning the text "N/A" (used for zones 264
    and 265) into a missing value.
    """
    df = pd.read_csv(lookup_csv, keep_default_na=False, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"LocationID": "location_id", "Borough": "borough",
                            "Zone": "zone_name", "service_zone": "service_zone"})
    for c in ("borough", "zone_name", "service_zone"):
        df[c] = df[c].str.strip().replace({"N/A": "Unknown", "": "Unknown"})
    df["location_id"] = df["location_id"].astype(int)
    if df["location_id"].duplicated().any():
        raise ValueError("taxi_zone_lookup.csv contains duplicate LocationIDs")
    return df[["location_id", "borough", "zone_name", "service_zone"]]