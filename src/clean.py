from datetime import datetime, timezone

import pandas as pd

from db import get_conn, init_db

# (table, column, min, max): is range se bahar ki value galat maani jayegi
RULES = [
    ("live_readings", "temperature_c", -20, 55),
    ("live_readings", "pm2_5", 0, 1500),
    ("live_readings", "pm10", 0, 3000),
    ("daily_weather", "temp_mean_c", -20, 55),
    ("daily_weather", "precip_mm", 0, 1000),
    ("daily_air", "pm2_5_mean", 0, 1500),
]


def main():
    init_db()
    issues = 0
    with get_conn() as conn:
        print("--- Data quality check ---")

        for table, col, lo, hi in RULES:
            cur = conn.execute(
                f"DELETE FROM {table} WHERE {col} IS NOT NULL "
                f"AND ({col} < ? OR {col} > ?)", (lo, hi))
            if cur.rowcount:
                issues += cur.rowcount
                print(f"REMOVED {cur.rowcount} rows: {table}.{col} outside {lo}..{hi}")

        for table in ["live_readings", "daily_weather", "daily_air", "emissions_country"]:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {n} rows")

        last = conn.execute("SELECT MAX(fetched_at_utc) FROM live_readings").fetchone()[0]
        if last:
            age = datetime.now(timezone.utc) - datetime.strptime(
                last, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
            hours = age.total_seconds() / 3600
            print(f"Last live fetch: {last} UTC ({hours:.1f} hours ago)")
            if hours > 3:
                issues += 1
                print("WARNING: live data 3 ghante se purana hai")

        src = pd.read_sql_query(
            "SELECT source, COUNT(DISTINCT city) AS cities FROM live_readings GROUP BY source",
            conn)
        print("\nCities per source:\n", src.to_string(index=False))

        for table in ["daily_weather", "daily_air"]:
            d = pd.read_sql_query(
                f"SELECT city, COUNT(*) AS n, MIN(date) AS d0, MAX(date) AS d1 "
                f"FROM {table} GROUP BY city", conn)
            d["expected"] = (pd.to_datetime(d["d1"]) - pd.to_datetime(d["d0"])).dt.days + 1
            d["missing"] = d["expected"] - d["n"]
            bad = d[d["missing"] > 0]
            if len(bad):
                issues += int(bad["missing"].sum())
                print(f"\nWARNING {table}: missing days\n", bad.to_string(index=False))
            else:
                print(f"{table}: koi missing day nahi")

        conn.commit()
    print(f"\nIssues found: {issues}")
    return issues


if __name__ == "__main__":
    main()