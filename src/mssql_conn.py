import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def pick_driver(pyodbc):
    """Installed ODBC drivers mein se sabse naya 'ODBC Driver NN for SQL Server' chunta hai."""
    wanted = os.getenv("MSSQL_DRIVER")
    if wanted:
        return wanted
    found = []
    for name in pyodbc.drivers():
        m = re.fullmatch(r"ODBC Driver (\d+) for SQL Server", name)
        if m:
            found.append((int(m.group(1)), name))
    if found:
        return max(found)[1]
    if "SQL Server" in pyodbc.drivers():          # purana Windows ka built-in driver
        return "SQL Server"
    raise RuntimeError(
        "SQL Server ka ODBC driver nahi mila. 'Microsoft ODBC Driver 18 for SQL Server' install karo. "
        f"Abhi installed drivers: {pyodbc.drivers()}")


def connect(database=None, autocommit=False):
    import pyodbc
    server = os.getenv("MSSQL_SERVER", r"localhost\SQLEXPRESS")
    database = database or os.getenv("MSSQL_DATABASE", "ClimateImpact")
    user, pwd = os.getenv("MSSQL_USER"), os.getenv("MSSQL_PASSWORD")
    parts = [f"DRIVER={{{pick_driver(pyodbc)}}}", f"SERVER={server}", f"DATABASE={database}",
             "TrustServerCertificate=yes"]
    parts += [f"UID={user}", f"PWD={pwd}"] if user else ["Trusted_Connection=yes"]
    return pyodbc.connect(";".join(parts), autocommit=autocommit, timeout=15)