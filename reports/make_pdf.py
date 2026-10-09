import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # bina screen ke chart banane ke liye
import matplotlib.dates as mdates           # noqa: E402
import matplotlib.pyplot as plt            # noqa: E402
import numpy as np                          # noqa: E402
import pandas as pd                         # noqa: E402
from reportlab.lib import colors            # noqa: E402
from reportlab.lib.enums import TA_CENTER   # noqa: E402
from reportlab.lib.pagesizes import A4      # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm          # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from report_data import get_report_data  # noqa: E402

OUT_DIR = ROOT / "reports" / "output"
IST = timezone(timedelta(hours=5, minutes=30))
NAVY = colors.HexColor("#1F4E78")
LIGHT = colors.HexColor("#EAF1F8")
RED = colors.HexColor("#F8CBAD")
GREY = colors.HexColor("#595959")
W = A4[0] - 30 * mm        # use-yogya chaudai

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20,
                    textColor=NAVY, alignment=0, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=8.5, textColor=GREY, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12,
                    textColor=NAVY, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("SMALL", parent=ss["Normal"], fontSize=8, leading=10.5, textColor=GREY)
CELL = ParagraphStyle("CELL", parent=ss["Normal"], fontSize=8.5, leading=10)
KPI_V = ParagraphStyle("KPI_V", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=15,
                       textColor=NAVY, alignment=TA_CENTER, leading=18)
KPI_L = ParagraphStyle("KPI_L", parent=ss["Normal"], fontSize=7.5, textColor=GREY,
                       alignment=TA_CENTER, leading=9)

UG = "ug/m<super>3</super>"


def f(v, nd=1, dash="-"):
    return dash if v is None or pd.isna(v) else f"{v:.{nd}f}"


def fig_image(fig, width):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = width, width * ratio
    return img


def chart_pm25_sources(lat):
    d = lat.dropna(subset=["pm25_openmeteo", "pm25_openweather"], how="all")
    x = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    ax.bar(x - 0.2, d["pm25_openmeteo"], 0.4, label="Open-Meteo", color="#1F4E78")
    ax.bar(x + 0.2, d["pm25_openweather"], 0.4, label="OpenWeather", color="#E59A3B")
    ax.set_xticks(x)
    ax.set_xticklabels(d["city"], rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("PM2.5 (ug/m3)", fontsize=8)
    ax.set_title("Live PM2.5 by city: two data sources", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=2, loc="lower right", bbox_to_anchor=(1, 1.0))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=8)
    return fig_image(fig, W)


def chart_trend(trend, last7):
    top = list(last7.head(5)["city"])
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    for c in top:
        t = trend[trend["city"] == c]
        ax.plot(pd.to_datetime(t["date"]), t["pm2_5_mean"], marker="o", ms=2.5, lw=1.5, label=c)
    ax.set_ylabel("Daily mean PM2.5 (ug/m3)", fontsize=8)
    ax.set_title("Last 14 days: 5 cities with highest 7-day average PM2.5", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    return fig_image(fig, W)


def chart_forecast(trend, fc, last7):
    top = list(last7.head(3)["city"])
    fig, axes = plt.subplots(1, len(top), figsize=(7.2, 2.2), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, c in zip(axes, top):
        t = trend[trend["city"] == c]
        p = fc[fc["city"] == c]
        ax.plot(pd.to_datetime(t["date"]), t["pm2_5_mean"], color="#1F4E78", lw=1.5, label="Observed")
        if len(p):
            dts = pd.to_datetime(p["forecast_date"])
            ax.plot(dts, p["yhat"], color="#C0392B", ls="--", lw=1.5, label="Forecast")
            ax.fill_between(dts, p["lower"], p["upper"], color="#C0392B", alpha=0.15, label="80% range")
        ax.set_title(c, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axes[0].set_ylabel("PM2.5 (ug/m3)", fontsize=8)
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Short-term PM2.5 forecast (statistical, not a guarantee)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    return fig_image(fig, W)


def chart_emissions(em):
    d = em[em["country"] == "India"].sort_values("year")
    fig, ax = plt.subplots(figsize=(7.2, 1.9))
    ax.plot(d["year"], d["co2_mt"], color="#1F4E78", marker="o", ms=3)
    ax.set_ylabel("Million tonnes CO2", fontsize=8)
    ax.set_title("India: annual CO2 emissions (fossil fuel + cement)", fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.set_ylim(bottom=0)
    return fig_image(fig, W)


def kpi_row(items):
    cells = [[Paragraph(v, KPI_V), Paragraph(l, KPI_L)] for v, l in items]
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[W / len(items)] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 2, colors.white),
        ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def summary_lines(lat, last7, fc):
    out = []
    t = lat.dropna(subset=["temp_c"])
    if len(t):
        hot = t.loc[t["temp_c"].idxmax()]
        out.append(f"Average temperature across {len(t)} cities is {t['temp_c'].mean():.1f} &deg;C; "
                   f"hottest is <b>{hot['city']}</b> at {hot['temp_c']:.1f} &deg;C.")
    p = lat.dropna(subset=["pm25_openmeteo"])
    if len(p):
        w = p.loc[p["pm25_openmeteo"].idxmax()]
        cat = w["us_category"] if isinstance(w["us_category"], str) else "n/a"
        out.append(f"Highest live PM2.5 (Open-Meteo) is <b>{w['city']}</b> at "
                   f"{w['pm25_openmeteo']:.1f} {UG} (US AQI category: {cat}).")
    bad_us = list(lat[lat["us_aqi"] > 150]["city"])
    out.append("Cities with US AQI above 150 (Unhealthy or worse): <b>"
               + (", ".join(bad_us) if bad_us else "none") + "</b>.")
    bad_ow = list(lat[lat["ow_aqi"] >= 4]["city"])
    out.append("Cities rated Poor/Very Poor by OpenWeather (AQI 4-5): <b>"
               + (", ".join(bad_ow) if bad_ow else "none") + "</b>.")
    if len(last7):
        r = last7.iloc[0]
        s = f"Highest 7-day average PM2.5 is <b>{r['city']}</b> ({r['avg_pm25_7d']:.1f} {UG}, " \
            f"peak day {r['max_pm25_7d']:.1f})."
        p2 = fc[fc["city"] == r["city"]]
        if len(p2):
            s += (f" Statistical forecast for the next {len(p2)} days: about {p2['yhat'].mean():.0f} "
                  f"{UG} (80% range {p2['lower'].min():.0f} to {p2['upper'].max():.0f}).")
        out.append(s)
    return out


def latest_table(lat):
    head = ["City", "Temp\n(C)", "Rain\n(mm)", "PM2.5\nOpen-Meteo", "US\nAQI", "US category",
            "PM2.5\nOpenWeather", "OW\nAQI"]
    rows = [head]
    for r in lat.itertuples(index=False):
        rows.append([r.city, f(r.temp_c), f(r.rain_mm), f(r.pm25_openmeteo),
                     f(r.us_aqi, 0), Paragraph(r.us_category if isinstance(r.us_category, str) else "-", CELL),
                     f(r.pm25_openweather), f(r.ow_aqi, 0)])
    cw = [W * x for x in (0.14, 0.08, 0.08, 0.13, 0.08, 0.25, 0.14, 0.10)]
    t = Table(rows, colWidths=cw, repeatRows=1)
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("ALIGN", (5, 1), (5, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]),
    ]
    for i, r in enumerate(lat.itertuples(index=False), start=1):
        if pd.notna(r.us_aqi) and r.us_aqi > 150:
            st.append(("BACKGROUND", (4, i), (5, i), RED))
        if pd.notna(r.ow_aqi) and r.ow_aqi >= 4:
            st.append(("BACKGROUND", (7, i), (7, i), RED))
    t.setStyle(TableStyle(st))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(15 * mm, 9 * mm, "Climate Impact Dashboard | Data: Open-Meteo, OpenWeather, Our World in Data")
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def main():
    now = datetime.now(IST)
    d = get_report_data()
    lat, trend, last7 = d["latest_city"], d["trend_14d"], d["last7"]
    fc, bt, em = d["forecast_pm25"], d["backtest"], d["emissions"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"Report_{now:%Y-%m-%d}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Climate Impact Daily Report", author="Climate Impact Dashboard")
    S = []

    # ---- Page 1
    S += [Paragraph("Climate Impact: Daily Report", H1),
          Paragraph(f"Generated {now:%d %b %Y, %H:%M} IST | {len(lat)} Indian cities", SUB)]
    t = lat.dropna(subset=["temp_c"])
    p = lat.dropna(subset=["pm25_openmeteo"])
    kp = [
        (f"{t['temp_c'].mean():.1f} C" if len(t) else "-", "Average temperature"),
        (str(p.loc[p['pm25_openmeteo'].idxmax(), 'city']) if len(p) else "-", "Highest PM2.5 city"),
        (f"{p['pm25_openmeteo'].max():.0f}" if len(p) else "-", "Highest PM2.5 (ug/m3)"),
        (str(int((lat["us_aqi"] > 150).sum())), "Cities: US AQI above 150"),
    ]
    S += [kpi_row(kp), Spacer(1, 6), Paragraph("Key points", H2)]
    for line in summary_lines(lat, last7, fc):
        S.append(Paragraph("&bull; " + line, BODY))
        S.append(Spacer(1, 2))
    S += [Paragraph("Latest readings", H2), latest_table(lat), Spacer(1, 3),
          Paragraph("Red = US AQI above 150, or OpenWeather AQI 4-5. The two AQI scales differ "
                    "(US: 0-500, OpenWeather: 1-5) and must not be compared directly.", SMALL),
          Spacer(1, 6), chart_pm25_sources(lat)]

    # ---- Page 2
    S += [PageBreak(), Paragraph("Trend and forecast", H2)]
    if len(trend):
        S.append(chart_trend(trend, last7))
        S.append(Spacer(1, 6))
        if len(fc):
            S.append(chart_forecast(trend, fc, last7))
    n_ets = int((bt["chosen_method"] == "damped_trend_ets").sum()) if len(bt) else 0
    S += [Spacer(1, 4),
          Paragraph(f"Forecast method: each series is tested against a simple baseline (last 7-day average) "
                    f"by hiding the last 3 weeks, three times. The better method is used. "
                    f"Today the smoothing model won for {n_ets} of {len(bt)} series; elsewhere the baseline "
                    f"was used. Treat forecasts as short-term trends only: they cannot predict seasonal "
                    f"spikes (for example winter smog).", SMALL)]

    if len(em):
        ind = em[em["country"] == "India"].sort_values("year")
        S += [Paragraph("Emissions context (annual, not live)", H2), chart_emissions(em)]
        if len(ind) >= 2:
            a, b = ind.iloc[-2], ind.iloc[-1]
            S.append(Paragraph(
                f"India emitted about <b>{b['co2_mt']:,.0f} Mt CO2</b> in {int(b['year'])} "
                f"({b['co2_per_capita_t']:.2f} t per person), "
                f"{(b['co2_mt'] / a['co2_mt'] - 1) * 100:+.1f}% versus {int(a['year'])}.", BODY))

    S += [KeepTogether([Paragraph("Data notes", H2),
          Paragraph("Air quality values are modelled estimates (Open-Meteo/CAMS and OpenWeather), not readings "
                    "from ground sensors. Daily PM2.5 history covers about the last 90 days. "
                    "Emissions are national annual totals from Our World in Data and are not city-level or live. "
                    "Times are IST unless stated.", SMALL)])]

    doc.build(S, onFirstPage=footer, onLaterPages=footer)
    print("PDF report bani:", path)
    return path


if __name__ == "__main__":
    main()