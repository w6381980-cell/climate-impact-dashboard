import re
from pathlib import Path

import pandas as pd

from db import get_conn, init_db

ROOT = Path(__file__).resolve().parent.parent
REPORT_SQL = ROOT / "sql" / "daily_report.sql"


def load_queries():
    """daily_report.sql ko '-- name: xyz' ke hisaab se alag-alag queries mein todta hai."""
    text = REPORT_SQL.read_text(encoding="utf-8")
    parts = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.MULTILINE)
    queries = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        queries[name] = body.strip().rstrip(";")
    return queries


def _run_all(queries):
    with get_conn() as conn:
        return {name: pd.read_sql_query(sql, conn) for name, sql in queries.items()}


def get_report_data():
    """Saari report queries chalakar {name: DataFrame} lautata hai.
    Normal case mein database ko sirf padhta hai (online server par file likhne ki zaroorat nahi).
    Views/tables na hon (naya khali database) tabhi unhe banata hai."""
    queries = load_queries()
    try:
        return _run_all(queries)
    except Exception:
        init_db()
        return _run_all(queries)


if __name__ == "__main__":
    for name, df in get_report_data().items():
        print(f"\n=== {name} ({len(df)} rows) ===")
        print(df.head(12).to_string(index=False))