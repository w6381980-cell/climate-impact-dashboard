import importlib
import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reports"))   # make_excel_mis.py aur make_pdf.py yahan hain
load_dotenv(ROOT / ".env")


def module_step(module_name):
    """Module tabhi import hota hai jab uska step chale (GitHub par kam packages se kaam chal jata hai)."""
    def _run():
        importlib.import_module(module_name).main()
    return _run


def report_step(module_name):
    def _run():
        if os.getenv("MAKE_REPORTS", "1") == "0":
            print("MAKE_REPORTS=0: report skip kiya (online dashboard khud banata hai)")
            return
        importlib.import_module(module_name).main()
    return _run


def sync_mssql():
    """SQL Server mein data bhejta hai. Sirf tab chalta hai jab .env mein MSSQL_ENABLED=1 ho."""
    if os.getenv("MSSQL_ENABLED", "0") != "1":
        print("MSSQL_ENABLED=1 nahi hai, SQL Server sync skip kiya")
        return
    importlib.import_module("mssql_sync").main()


STEPS = [
    ("Live data", module_step("collect_live")),
    ("History data", module_step("collect_history")),
    ("Emissions data", module_step("load_emissions")),
    ("Forecast", module_step("forecast")),
    ("Data check", module_step("clean")),
    ("SQL Server sync", sync_mssql),
    ("Excel MIS report", report_step("make_excel_mis")),
    ("PDF report", report_step("make_pdf")),
]


def main():
    failed = []
    for name, fn in STEPS:
        print(f"\n===== {name} =====")
        try:
            fn()
        except Exception:
            failed.append(name)
            traceback.print_exc()
    print("\n===== SUMMARY =====")
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(1)
    print("Sab steps pass hue")


if __name__ == "__main__":
    main()