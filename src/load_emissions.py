import time
from pathlib import Path

import pandas as pd
import requests

from db import get_conn, init_db

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CSV_PATH = RAW_DIR / "owid-co2-data.csv"
URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"

COUNTRIES = ["India", "China", "United States", "World"]
FROM_YEAR = 1990
MAX_AGE_DAYS = 7  # itni purani file ho tabhi dobara download hogi


def download_if_needed():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if CSV_PATH.exists():
        age_days = (time.time() - CSV_PATH.stat().st_mtime) / 86400
        if age_days < MAX_AGE_DAYS:
            print("Local file use ho rahi hai (download nahi kiya)")
            return
    print("OWID CO2 dataset download ho raha hai...")
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    CSV_PATH.write_bytes(r.content)


def main():
    init_db()
    download_if_needed()

    df = pd.read_csv(CSV_PATH)
    df = df[df["country"].isin(COUNTRIES) & (df["year"] >= FROM_YEAR)]
    out = df[["country", "year", "co2", "co2_per_capita",
              "share_global_co2", "co2_including_luc", "population"]].copy()
    out.columns = ["country", "year", "co2_mt", "co2_per_capita_t",
                   "share_global_co2_pct", "co2_incl_luc_mt", "population"]
    out = out.astype(object).where(out.notna(), None)

    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO emissions_country VALUES (?,?,?,?,?,?,?)",
            list(out.itertuples(index=False, name=None)),
        )
        summary = pd.read_sql_query(
            """SELECT country, year, ROUND(co2_mt,0) AS co2_mt,
                      ROUND(co2_per_capita_t,2) AS per_capita_t
               FROM emissions_country
               WHERE year >= (SELECT MAX(year) FROM emissions_country) - 4
               ORDER BY country, year""", conn)
    print("\nSaved", len(out), "rows. Last 5 years:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()