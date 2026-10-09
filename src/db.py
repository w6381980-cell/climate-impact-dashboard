import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "climate.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
VIEWS_PATH = ROOT / "sql" / "views.sql"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        try:
            conn.execute("ALTER TABLE live_readings ADD COLUMN ow_aqi INTEGER")
        except sqlite3.OperationalError:
            pass  # column pehle se hai
        conn.executescript(VIEWS_PATH.read_text(encoding="utf-8"))