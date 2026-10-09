import re
from pathlib import Path

from mssql_conn import connect

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql" / "mssql"
SCRIPTS = ["01_database.sql", "02_tables.sql", "03_views.sql", "04_reports.sql"]


def batches(text):
    """SSMS ka 'GO' separator python mein nahi chalta, isliye script ko batches mein todte hain."""
    return [b.strip() for b in re.split(r"^\s*GO\s*$", text, flags=re.IGNORECASE | re.MULTILINE) if b.strip()]


def run_script(conn, path):
    cur = conn.cursor()
    parts = batches(path.read_text(encoding="utf-8"))
    for i, batch in enumerate(parts, start=1):
        cur.execute(batch)
        while cur.nextset():      # kuch batches multiple results dete hain
            pass
    print(f"OK   {path.name}: {len(parts)} batches")


def main():
    conn = connect(database="master", autocommit=True)     # CREATE DATABASE transaction ke andar nahi chalta
    run_script(conn, SQL_DIR / SCRIPTS[0])
    conn.close()

    conn = connect(autocommit=True)
    for name in SCRIPTS[1:]:
        run_script(conn, SQL_DIR / name)
    cur = conn.cursor()
    n_tables = cur.execute("SELECT COUNT(*) FROM sys.tables WHERE schema_id = SCHEMA_ID('climate')").fetchone()[0]
    n_views = cur.execute("SELECT COUNT(*) FROM sys.views WHERE schema_id = SCHEMA_ID('rpt')").fetchone()[0]
    n_dates = cur.execute("SELECT COUNT(*) FROM climate.DimDate").fetchone()[0]
    print(f"\nSQL Server taiyar: {n_tables} tables (climate), {n_views} views (rpt), calendar {n_dates} din")
    conn.close()


if __name__ == "__main__":
    main()