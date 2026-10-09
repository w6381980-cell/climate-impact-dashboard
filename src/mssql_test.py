"""SQL Server connection ko ek-ek step mein jaanchta hai. Chalao: python src/mssql_test.py"""
import os
import sys

from mssql_conn import connect, pick_driver

HINTS = [
    (("IM002", "Data source name not found"),
     "ODBC driver nahi mila. Chalao: winget install -e --id Microsoft.msodbcsql.18  (phir terminal band karke dobara kholo)"),
    (("18456", "Login failed"),
     "Login fail. Windows login ke liye apna user SQL Server mein admin hona chahiye. "
     "Ya .env mein MSSQL_USER aur MSSQL_PASSWORD daalo (iske liye SQL Server 'Mixed mode' chahiye)."),
    (("4060", "Cannot open database"),
     "Server mil gaya par database nahi bana. Pehle chalao: python src/mssql_setup.py"),
    (("certificate", "SSL", "TLS"),
     "Certificate ka masla. Is project mein TrustServerCertificate=yes pehle se laga hai, toh driver purana ho sakta hai. "
     "Naya ODBC Driver 18 install karo."),
    (("Login timeout", "timeout", "08001", "Named Pipes", "could not open a connection", "[53]", "(40)", "[2]"),
     "Server tak pahunch nahi paaye. Check karo: (1) Services mein 'SQL Server (SQLEXPRESS)' Running hai? "
     "PowerShell: Get-Service 'MSSQL$SQLEXPRESS'   (2) .env mein MSSQL_SERVER ka naam sahi hai? "
     "Instance alag ho toh uska naam likho (jaise localhost\\MSSQLSERVER ya sirf localhost)."),
]


def explain(err):
    text = str(err)
    for keys, hint in HINTS:
        if any(k.lower() in text.lower() for k in keys):
            return hint
    return "Error ka poora text mujhe bhej do."


def step(n, title):
    print(f"\nStep {n}: {title}")


def main():
    step(1, "pyodbc installed hai?")
    try:
        import pyodbc
    except ImportError:
        print("  FAIL  pyodbc nahi mila.  Chalao: python -m pip install pyodbc")
        return 1
    print(f"  OK    pyodbc {pyodbc.version}")

    step(2, "SQL Server ke ODBC drivers")
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    print("  Mile:", drivers or "koi nahi")
    if not drivers:
        print("  FAIL  Chalao: winget install -e --id Microsoft.msodbcsql.18")
        return 1
    print(f"  OK    use hoga: {pick_driver(pyodbc)}")

    step(3, ".env ki settings")
    server = os.getenv("MSSQL_SERVER", r"localhost\SQLEXPRESS")
    database = os.getenv("MSSQL_DATABASE", "ClimateImpact")
    login = f"SQL login ({os.getenv('MSSQL_USER')})" if os.getenv("MSSQL_USER") else "Windows login (aapka user)"
    print(f"  Server: {server}\n  Database: {database}\n  Login: {login}")

    step(4, "Server se connect (master database)")
    try:
        conn = connect(database="master", autocommit=True)
        row = conn.cursor().execute("SELECT @@SERVERNAME, SUSER_SNAME(), LEFT(@@VERSION, 40)").fetchone()
        print(f"  OK    server={row[0]} | user={row[1]}\n        {row[2]}")
    except Exception as e:
        print("  FAIL ", str(e)[:300])
        print("  AASAN FIX:", explain(e))
        return 1

    step(5, f"Database '{database}' bani hai?")
    exists = conn.cursor().execute("SELECT DB_ID(?)", database).fetchone()[0]
    if exists is None:
        print("  NAHI   Chalao: python src/mssql_setup.py")
        conn.close()
        return 0
    print("  OK    database maujood hai")
    conn.close()

    step(6, "Tables mein kitni rows hain")
    try:
        conn = connect()
        cur = conn.cursor()
        for t in ["City", "LiveReading", "DailyWeather", "DailyAir", "EmissionsCountry", "Forecast", "ForecastBacktest", "DimDate"]:
            n = cur.execute(f"SELECT COUNT(*) FROM climate.{t}").fetchone()[0]
            print(f"  climate.{t:<17} {n:>6} rows")
        fresh = cur.execute("SELECT LastFetchIst, AgeHours FROM rpt.DataFreshness").fetchone()
        print(f"  Latest data: {fresh[0]} IST ({fresh[1]} hours pehle)" if fresh and fresh[0] else
              "  Data abhi khali hai. Chalao: python src/mssql_sync.py")
        conn.close()
    except Exception as e:
        print("  FAIL ", str(e)[:300])
        print("  AASAN FIX:", explain(e) + "  (tables nahi bani hon toh: python src/mssql_setup.py)")
        return 1

    print("\nSab theek hai. Ab Power BI se connect kar sakte ho.")
    return 0


if __name__ == "__main__":
    sys.exit(main())