import html
import math
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from db import DB_PATH  # noqa: E402
from report_data import load_queries  # noqa: E402

QUERIES = load_queries()

st.set_page_config(page_title="Climate Impact Dashboard", page_icon="🌍", layout="wide")

# =============================================================== theme palettes
LIGHT = {
    "name": "Light", "ink": "#12384F", "muted": "#5B7488", "teal": "#1AA6B7", "grid": "#D8E3EC",
    "vars": """
      --bg1:#EAF2F7; --bg2:#DCE9F1; --bg3:#E6EEF4; --globe:.40;
      --card:rgba(255,255,255,.68); --card-solid:#F7FAFC; --card-border:rgba(255,255,255,.9);
      --shadow:0 10px 32px rgba(18,56,79,.10);
      --ink:#12384F; --muted:#5B7488; --teal:#1AA6B7; --teal-soft:rgba(26,166,183,.15); --teal-ink:#0E7C8B;
      --side:rgba(255,255,255,.62); --field:rgba(255,255,255,.8); --field-border:rgba(18,56,79,.16);
      --chip:rgba(255,255,255,.75); --chip-border:rgba(18,56,79,.14); --chip-hover:rgba(26,166,183,.14);
      --digit-a:#2A2D33; --digit-b:#1E2126; --digit-fg:#F4F7F9; --digit-edge:rgba(255,255,255,.07);
      --solid:#0E8394; --on-solid:#FFFFFF; --th-bg:#E4EEF5; --zebra:rgba(18,56,79,.035); --row-line:rgba(18,56,79,.08); --pop:#FFFFFF; --cs:light;
    """,
}
DARK = {
    "name": "Dark", "ink": "#E8F3F8", "muted": "#9DB6C6", "teal": "#35C4D6", "grid": "#2B4A5E",
    "vars": """
      --bg1:#0A1822; --bg2:#0F2535; --bg3:#0B1D2B; --globe:.28;
      --card:rgba(22,44,61,.66); --card-solid:#12293A; --card-border:rgba(255,255,255,.09);
      --shadow:0 12px 34px rgba(0,0,0,.40);
      --ink:#E8F3F8; --muted:#9DB6C6; --teal:#35C4D6; --teal-soft:rgba(53,196,214,.18); --teal-ink:#7FE0EC;
      --side:rgba(10,24,34,.78); --field:rgba(255,255,255,.07); --field-border:rgba(255,255,255,.16);
      --chip:rgba(255,255,255,.07); --chip-border:rgba(255,255,255,.16); --chip-hover:rgba(53,196,214,.22);
      --digit-a:#0C1620; --digit-b:#08111A; --digit-fg:#BFF4FA; --digit-edge:rgba(53,196,214,.35);
      --solid:#35C4D6; --on-solid:#05222B; --th-bg:#183349; --zebra:rgba(255,255,255,.035); --row-line:rgba(255,255,255,.07); --pop:#16303F; --cs:dark;
    """,
}

# header first (theme switch must be read before the CSS is written)
hc1, hc2 = st.columns([5, 1.6], vertical_alignment="center")
title_slot = hc1.empty()
with hc2:
    theme_pick = st.segmented_control("Theme", ["Light", "Dark"], default="Light",
                                      key="theme_mode", label_visibility="collapsed")
PAL = DARK if theme_pick == "Dark" else LIGHT
INK, MUTED, TEAL, CORAL = PAL["ink"], PAL["muted"], PAL["teal"], "#E4572E"

GLOBE_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 600'>
<defs>
<radialGradient id='g' cx='36%' cy='32%' r='78%'><stop offset='0' stop-color='#7CC0EC'/><stop offset='.55' stop-color='#2B79B8'/><stop offset='1' stop-color='#0E3C63'/></radialGradient>
<radialGradient id='h' cx='50%' cy='50%' r='50%'><stop offset='.84' stop-color='#9EDDF2' stop-opacity='.55'/><stop offset='1' stop-color='#9EDDF2' stop-opacity='0'/></radialGradient>
<clipPath id='c'><circle cx='300' cy='300' r='250'/></clipPath>
</defs>
<circle cx='300' cy='300' r='292' fill='url(#h)'/>
<circle cx='300' cy='300' r='250' fill='url(#g)'/>
<g clip-path='url(#c)' fill='#86BE7E' opacity='.85'>
<path d='M120 170 C170 120 250 140 280 190 C300 240 250 270 230 320 C215 360 170 380 150 330 C130 290 90 220 120 170Z'/>
<path d='M330 120 C400 90 480 130 500 190 C515 240 460 250 430 230 C400 255 370 220 350 190 C330 170 320 140 330 120Z'/>
<path d='M360 300 C420 280 470 320 460 380 C450 440 400 480 370 440 C340 400 320 340 360 300Z'/>
<path d='M170 420 C210 400 250 430 240 470 C225 510 180 515 160 480 C150 455 150 435 170 420Z'/>
</g>
<g clip-path='url(#c)' fill='none' stroke='#fff' stroke-opacity='.16' stroke-width='1.5'>
<ellipse cx='300' cy='300' rx='250' ry='90'/><ellipse cx='300' cy='300' rx='250' ry='170'/>
<ellipse cx='300' cy='300' rx='90' ry='250'/><ellipse cx='300' cy='300' rx='170' ry='250'/>
<line x1='50' y1='300' x2='550' y2='300'/><line x1='300' y1='50' x2='300' y2='550'/>
</g></svg>"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { @@VARS@@ color-scheme: var(--cs); }
html, body, .stApp { font-family:'Plus Jakarta Sans','Segoe UI',sans-serif; color:var(--ink); }
.stApp { background: linear-gradient(160deg,var(--bg1) 0%,var(--bg2) 55%,var(--bg3) 100%); }
.stApp::before { content:""; position:fixed; inset:0; pointer-events:none; z-index:0; opacity:var(--globe);
  background:url("@@GLOBE@@") no-repeat 64% 48% / min(80vmin,780px); }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stAppDeployButton"], .stDeployButton, #MainMenu, footer { display:none !important; }
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style) { display:none; }
.block-container { position:relative; z-index:1; max-width:1380px; padding-top:1.6rem; container-type:inline-size; }

/* text colours that follow the chosen theme (not Streamlit's own) */
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stWidgetLabel"] *, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] * { color:var(--ink); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color:var(--muted) !important; }
h1,h2,h3,h4 { font-family:'Plus Jakarta Sans','Segoe UI',sans-serif !important; letter-spacing:-.01em; }

[data-testid="stSidebar"] { background:var(--side); backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); }
[data-testid="stSidebar"] * { color:var(--ink); }

/* glass cards */
[class*="st-key-card"] { background:var(--card); backdrop-filter:blur(16px) saturate(140%); -webkit-backdrop-filter:blur(16px) saturate(140%);
  border:1px solid var(--card-border); border-radius:22px; box-shadow:var(--shadow); padding:1.1rem 1.3rem; }
.ctitle { font-weight:700; font-size:1rem; color:var(--ink); margin:0 0 .2rem 0; }
.csub { color:var(--muted); font-size:.8rem; margin:0 0 .4rem 0; }
.chip { display:inline-block; padding:.12rem .65rem; border-radius:999px; background:var(--teal-soft); color:var(--teal-ink); font-weight:600; font-size:.74rem; }
.chip.warn { background:rgba(228,87,46,.16); color:#E0583A; }

/* KPI strip (css grid: 4 across, 2x2 on tablet/mobile) */
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:1rem; margin:.2rem 0 1.1rem 0; }
.kcard { background:var(--card); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); border:1px solid var(--card-border);
  border-left:5px solid var(--accent,var(--teal)); border-radius:18px; box-shadow:var(--shadow); padding:.85rem 1.1rem; }
.kcard .kl { color:var(--muted); font-size:.8rem; font-weight:600; }
.kcard .kv { font:700 1.8rem/1.15 'Space Grotesk','Segoe UI',sans-serif; color:var(--ink); margin:.1rem 0; }
.kcard .ks { color:var(--muted); font-size:.78rem; }

/* flip counter */
.flip-row { display:flex; align-items:flex-end; gap:.4rem; margin:.7rem 0 .5rem 0; flex-wrap:nowrap; }
.fd { position:relative; display:inline-flex; align-items:center; justify-content:center; width:clamp(40px,4.4vw,68px); height:clamp(62px,6.8vw,100px);
  width:clamp(40px,5.2cqw,68px); height:clamp(62px,8cqw,100px);
  border-radius:10px; background:linear-gradient(var(--digit-a) 0 50%,var(--digit-b) 50% 100%); color:var(--digit-fg);
  font:700 clamp(38px,4.2vw,68px)/1 'Space Grotesk','Segoe UI',sans-serif; font-size:clamp(38px,5cqw,68px);
  font-variant-numeric:tabular-nums; box-shadow:inset 0 0 0 1px var(--digit-edge),0 8px 16px rgba(0,0,0,.22); }
.fd::after { content:""; position:absolute; left:0; right:0; top:50%; height:2px; background:rgba(0,0,0,.6); }
.fdot { font:700 clamp(34px,3.6vw,56px)/1 'Space Grotesk',sans-serif; color:var(--ink); padding:0 .05rem; }
.funit { font:600 1.5rem 'Plus Jakarta Sans',sans-serif; color:var(--teal-ink); padding-bottom:.35rem; margin-left:.25rem; }
.flip-meta { color:var(--muted); font-size:.85rem; margin-top:.2rem; }
.flip-meta b { color:var(--ink); }

/* gauge */
.gauge { width:100%; max-width:320px; display:block; margin:0 auto; }
.needle { transform-origin:100px 100px; transform:rotate(var(--a)); animation:sweep 1s cubic-bezier(.2,.8,.2,1); }
@keyframes sweep { from { transform:rotate(-90deg); } to { transform:rotate(var(--a)); } }
@media (prefers-reduced-motion: reduce) { .needle { animation:none; } }
.g-num { text-align:center; font:700 2.2rem/1 'Space Grotesk',sans-serif; color:var(--ink); margin-top:-.2rem; }
.g-cat { text-align:center; color:var(--muted); font-size:.88rem; margin-top:.15rem; }

/* outlook card */
.o-big { font:700 2.3rem/1.1 'Space Grotesk',sans-serif; color:var(--ink); margin:.4rem 0 .1rem 0; }
.o-line { color:var(--muted); font-size:.85rem; margin:.25rem 0; }
.o-line b { color:var(--ink); }

/* buttons: normal / hover / pressed / keyboard focus, inner text always inherits */
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
  background:var(--chip); color:var(--ink); border:1px solid var(--chip-border); border-radius:999px; font-weight:600;
  transition:background .15s, border-color .15s, color .15s; }
[data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
  background:var(--chip-hover); border-color:var(--teal); color:var(--ink); }
[data-testid="stButton"] button:active, [data-testid="stDownloadButton"] button:active {
  background:var(--solid); border-color:var(--solid); color:var(--on-solid); }
[data-testid="stButton"] button:focus-visible, [data-testid="stDownloadButton"] button:focus-visible { outline:2px solid var(--teal); outline-offset:2px; box-shadow:none; }
[data-testid="stButton"] button *, [data-testid="stDownloadButton"] button * { color:inherit !important; }

/* pills + segmented control (city names, theme, windows).
   Selected state is matched by several selectors because Streamlit versions name it differently
   (aria-checked in new versions, pillsActive / segmented_controlActive in older ones). */
[data-testid="stButtonGroup"] button, button[data-testid^="stBaseButton-pills"], button[data-testid^="stBaseButton-segmented_control"] {
  background:var(--chip) !important; color:var(--ink) !important; border:1px solid var(--chip-border) !important;
  border-radius:999px !important; padding:.3rem .95rem; font-weight:600; box-shadow:none;
  transition:background .15s, border-color .15s, color .15s; }
[data-testid="stButtonGroup"] button:hover, button[data-testid^="stBaseButton-pills"]:hover, button[data-testid^="stBaseButton-segmented_control"]:hover {
  background:var(--chip-hover) !important; border-color:var(--teal) !important; color:var(--ink) !important; }
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"],
.stApp [data-testid="stButtonGroup"] button[aria-pressed="true"],
.stApp [data-testid="stButtonGroup"] button[data-selected="true"],
.stApp button[kind="pillsActive"],
.stApp button[kind="segmented_controlActive"],
.stApp button[data-testid="stBaseButton-pillsActive"],
.stApp button[data-testid="stBaseButton-segmented_controlActive"],
.stApp [data-testid="stButtonGroup"] button[aria-checked="true"]:hover,
.stApp [data-testid="stButtonGroup"] button[aria-pressed="true"]:hover,
.stApp [data-testid="stButtonGroup"] button[data-selected="true"]:hover,
.stApp button[kind="pillsActive"]:hover,
.stApp button[kind="segmented_controlActive"]:hover,
.stApp button[data-testid="stBaseButton-pillsActive"]:hover,
.stApp button[data-testid="stBaseButton-segmented_controlActive"]:hover {
  background:var(--solid) !important; border-color:var(--solid) !important; color:var(--on-solid) !important;
  box-shadow:0 4px 12px rgba(14,131,148,.30) !important; }
[data-testid="stButtonGroup"] button:focus-visible { outline:2px solid var(--teal); outline-offset:2px; }
[data-testid="stButtonGroup"] button *, button[data-testid^="stBaseButton-pills"] *,
button[data-testid^="stBaseButton-segmented_control"] * { color:inherit !important; }
[data-testid="stButtonGroup"] [role="radiogroup"], [data-testid="stButtonGroup"] > div:last-child { gap:.4rem; flex-wrap:wrap; }
.st-key-theme_mode { display:flex; justify-content:flex-end; }

/* tabs */
.stTabs [role="tablist"], .stTabs [data-baseweb="tab-list"] { gap:.3rem; background:var(--chip); padding:.3rem; border-radius:999px;
  width:fit-content; max-width:100%; overflow-x:auto; border-bottom:0 !important; box-shadow:none; }
.stTabs [role="tab"] { border-radius:999px; padding:.4rem 1.05rem; height:auto; color:var(--muted); white-space:nowrap; }
.stTabs [role="tab"]:hover { color:var(--ink); background:var(--chip-hover); }
.stTabs [role="tab"][aria-selected="true"] { background:var(--solid); color:var(--on-solid); }
.stTabs [role="tab"] * { color:inherit !important; }
.stTabs .react-aria-SelectionIndicator, .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none !important; }
.stTabs [role="tabpanel"], .stTabs [data-baseweb="tab-panel"] { background:var(--card); border-radius:20px; padding:1.2rem 1.3rem; margin-top:.7rem;
  border:1px solid var(--card-border); box-shadow:var(--shadow); }

/* inputs, dropdowns (Streamlit 1.5x+ react-aria DOM, older baseweb DOM kept as fallback) */
[data-testid="stSelectbox"] [role="group"], [data-testid="stTextAreaRootElement"], [data-testid="stTextInputRootElement"],
[data-baseweb="select"] > div, [data-baseweb="textarea"], [data-baseweb="base-input"] {
  background:var(--field) !important; border:1px solid var(--field-border) !important; border-radius:12px !important; }
[data-testid="stSelectbox"] input, textarea, [data-testid="stTextInputRootElement"] input {
  background:transparent !important; color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; caret-color:var(--ink); }
[data-testid="stSelectbox"] svg, [data-testid="stExpander"] svg, [data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapseButton"] svg { fill:var(--ink) !important; color:var(--ink) !important; }
[data-baseweb="select"] * { color:var(--ink) !important; }
[role="listbox"], [role="listbox"] > div, [data-baseweb="popover"] > div, [data-baseweb="popover"] ul { background:var(--pop) !important; border-radius:12px; }
div:has(> [role="listbox"]) { background:var(--pop) !important; border-radius:12px; box-shadow:var(--shadow); }
[role="option"], [data-baseweb="popover"] li { color:var(--ink) !important; }
[role="option"]:hover, [role="option"][data-focused="true"], [role="option"][aria-selected="true"],
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background:var(--teal-soft) !important; }
[data-testid="stExpander"] details { background:var(--card); border:1px solid var(--card-border); border-radius:14px; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color:var(--ink) !important; }
[data-testid="stAlert"] * { color:var(--ink) !important; }
[data-testid="stMetricDelta"] * { color:var(--muted) !important; }

/* html tables (follow the theme, unlike the canvas dataframe) */
.tbl-wrap { overflow:auto; max-height:430px; border-radius:14px; border:1px solid var(--card-border); background:var(--card-solid); }
.tbl { border-collapse:collapse; width:100%; font-size:.85rem; }
.tbl th { position:sticky; top:0; background:var(--th-bg); color:var(--ink); text-align:left; padding:.55rem .8rem; font-weight:700; white-space:nowrap; }
.tbl td { padding:.5rem .8rem; border-top:1px solid var(--row-line); color:var(--ink); white-space:nowrap; }
.tbl tr:nth-child(even) td { background:var(--zebra); }
.tbl td.num { text-align:right; font-variant-numeric:tabular-nums; }
.tbl td.flag { background:rgba(228,87,46,.30) !important; font-weight:700; }

/* wide screens: equal card heights */
@container (min-width: 821px) {
  .st-key-card_flip, .st-key-card_gauge, .st-key-card_outlook { min-height:310px; }
  .st-key-card_rain, .st-key-card_trend, .st-key-card_rank { min-height:345px; }
}
/* laptop with sidebar / tablet: two cards per row. phone: one per row */
@container (max-width: 820px) {
  [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; row-gap:1rem; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex:1 1 calc(50% - 1rem) !important; min-width:calc(50% - 1rem) !important; }
}
@container (max-width: 560px) {
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex:1 1 100% !important; min-width:100% !important; }
  .kpi-grid { grid-template-columns:repeat(2,1fr); gap:.7rem; }
  .kcard { padding:.7rem .85rem; } .kcard .kv { font-size:1.4rem; }
  .tabs-note { display:none; }
}
</style>
"""
st.markdown(CSS.replace("@@VARS@@", PAL["vars"]).replace("@@GLOBE@@", "data:image/svg+xml;utf8," + quote(GLOBE_SVG)),
            unsafe_allow_html=True)

if not DB_PATH.exists():
    st.error("Database nahi mili. Pehle `python src/run_daily.py` chalao.")
    st.stop()


# =================================================================== data layer
def _run(sql, params=()):
    """Database sirf padhne (read-only) mode mein khulta hai, dashboard kuch badal nahi sakta."""
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def run(sql, params=()):
    return _run(sql, params)


def marks(items):
    return ",".join("?" * len(items))


def to_dt(df, col):
    df = df.copy()
    df[col] = pd.to_datetime(df[col])
    return df


def esc(x):
    return html.escape(str(x))


def num(v, nd=1, dash="-"):
    return dash if v is None or pd.isna(v) else f"{v:.{nd}f}"


def style(ch):
    """Charts ko glass cards aur chuni hui theme ke saath match karta hai."""
    return (ch.configure(background="transparent", font="Plus Jakarta Sans, Segoe UI, sans-serif")
              .configure_view(stroke=None)
              .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor=PAL["grid"], domainColor=PAL["grid"],
                              tickColor=PAL["grid"], labelFontSize=11, titleFontSize=11)
              .configure_legend(labelColor=MUTED, titleColor=MUTED)
              .configure_title(color=INK, fontSize=13, anchor="start"))


@st.cache_data(ttl=3600, show_spinner=False)
def build_reports(data_stamp):
    """Aaj ka Excel aur PDF report current data se banata hai. data_stamp badalte hi naya report banta hai."""
    sys.path.insert(0, str(ROOT / "reports"))
    import make_excel_mis
    import make_pdf
    x, p = Path(make_excel_mis.main()), Path(make_pdf.main())
    return x.name, x.read_bytes(), p.name, p.read_bytes()


def show_chart(ch, width="stretch"):
    """Streamlit ke purane versions mein altair_chart(width=...) nahi hota, tab use_container_width chalta hai."""
    try:
        st.altair_chart(ch, width=width)
    except TypeError:
        st.altair_chart(ch, use_container_width=True)


def html_table(df, decimals=None, flags=None, max_rows=500):
    """DataFrame ko theme-friendly HTML table banata hai (canvas dataframe dark/light mein mismatch karta hai)."""
    decimals, flags = decimals or {}, flags or {}
    head = "".join(f"<th>{esc(c)}</th>" for c in df.columns)
    body = []
    for rec in df.head(max_rows).itertuples(index=False):
        tds = []
        for c, v in zip(df.columns, rec):
            cls = []
            if v is None or (isinstance(v, float) and math.isnan(v)):
                txt = "-"
            elif isinstance(v, (bool, np.bool_)):
                txt = esc(v)
            elif isinstance(v, (int, np.integer)):
                txt, cls = str(v), ["num"]
            elif isinstance(v, (float, np.floating)):
                nd = decimals.get(c, 0 if float(v).is_integer() else 2)
                txt, cls = f"{v:,.{nd}f}", ["num"]
            else:
                txt = esc(v)
            if c in flags and v is not None and not (isinstance(v, float) and math.isnan(v)) and flags[c](v):
                cls.append("flag")
            tds.append(f"<td class='{' '.join(cls)}'>{txt}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    note = f"<div class='csub' style='padding:.4rem .8rem'>Showing first {max_rows} of {len(df)} rows</div>" if len(df) > max_rows else ""
    return f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>{note}</div>"


def choose(widget, label, options, default, key, **kw):
    """pills / segmented control jo None (kuch nahi chuna) hone par default lautata hai."""
    val = widget(label, options, default=default, key=key, label_visibility="collapsed", **kw)
    return default if val is None else val


# ================================================================ html components
AQI_BANDS = [(0, 50, "#7BC96F", "🟢"), (51, 100, "#F2D14B", "🟡"), (101, 150, "#F59E42", "🟠"),
             (151, 200, "#E4572E", "🔴"), (201, 300, "#9B59B6", "🟣"), (301, 500, "#7E1F3D", "🟤")]


def aqi_color(v):
    if v is None or pd.isna(v):
        return "#B8C4CE"
    for lo, hi, c, _ in AQI_BANDS:
        if v <= hi:
            return c
    return AQI_BANDS[-1][2]


def aqi_dot(v):
    if v is None or pd.isna(v):
        return "⚪"
    for lo, hi, _, d in AQI_BANDS:
        if v <= hi:
            return d
    return AQI_BANDS[-1][3]


def aqi_frac(v):
    for i, (lo, hi, _, _) in enumerate(AQI_BANDS):
        if v <= hi:
            return min(max((i + (v - lo) / (hi - lo + 1)) / 6, 0), 1)
    return 1.0


def _pt(f, r):
    th = math.pi * (1 - f)
    return 100 + r * math.cos(th), 100 - r * math.sin(th)


def gauge_html(aqi):
    arcs = ""
    for i, band in enumerate(AQI_BANDS):
        a, b = i / 6 + 0.008, (i + 1) / 6 - 0.008
        (x0, y0), (x1, y1) = _pt(a, 78), _pt(b, 78)
        arcs += (f"<path d='M{x0:.1f} {y0:.1f} A78 78 0 0 1 {x1:.1f} {y1:.1f}' fill='none' "
                 f"stroke='{band[2]}' stroke-width='15'/>")
    needle = ""
    if aqi is not None and not pd.isna(aqi):
        ang = aqi_frac(aqi) * 180 - 90
        needle = (f"<g class='needle' style='--a:{ang:.1f}deg'>"
                  f"<path d='M100 100 L96.5 100 L100 34 L103.5 100 Z' style='fill:var(--ink)'/></g>")
    return ("<svg class='gauge' viewBox='0 0 200 118' role='img' aria-label='AQI gauge'>" + arcs + needle +
            "<circle cx='100' cy='100' r='7' style='fill:var(--ink)'/><circle cx='100' cy='100' r='2.6' fill='#fff'/>"
            "<text x='22' y='114' font-size='8' style='fill:var(--muted)' text-anchor='middle'>0</text>"
            "<text x='178' y='114' font-size='8' style='fill:var(--muted)' text-anchor='middle'>500</text></svg>")


def flip_html(value):
    if value is None or pd.isna(value):
        boxes = "<span class='fd'>-</span><span class='fd'>-</span>"
    else:
        boxes = ""
        for ch in f"{value:.1f}":
            boxes += "<span class='fdot'>.</span>" if ch == "." else f"<span class='fd'>{ch}</span>"
    return f"<div class='flip-row'>{boxes}<span class='funit'>&deg;C</span></div>"


def kcard(label, value, sub, accent):
    return (f"<div class='kcard' style='--accent:{accent}'><div class='kl'>{label}</div>"
            f"<div class='kv'>{value}</div><div class='ks'>{sub}</div></div>")


# ===================================================================== sidebar
all_cities = run("SELECT DISTINCT city FROM live_readings ORDER BY city")["city"].tolist()
if not all_cities:
    st.error("Database khali hai. Pehle `python src/run_daily.py` chalao.")
    st.stop()

with st.sidebar:
    with st.expander("Comparison cities", expanded=False):
        st.caption("Sirf rank aur trend charts ke liye. Ek city dekhne ke liye upar page par city pills dabao.")
        sel = st.pills("Cities", all_cities, selection_mode="multi", default=all_cities,
                       key="cities_pick", label_visibility="collapsed")
        if not sel:
            st.caption("Koi city nahi chuni, isliye sabhi shamil hain.")
    cities = [c for c in all_cities if c in sel] if sel else all_cities
    st.subheader("History (days)")
    window = choose(st.segmented_control, "Window (days)", [30, 60, 90, 180, 365], 90, "window_pick")
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.subheader("Reports")
    report_slot = st.container()

with st.sidebar.expander("Data health"):
    st.caption(f"DB: {DB_PATH}")
    for t in ["live_readings", "daily_weather", "daily_air", "forecasts", "emissions_country"]:
        try:
            st.caption(f"{t}: {int(run(f'SELECT COUNT(*) AS n FROM {t}')['n'].iloc[0])} rows")
        except Exception as e:
            st.caption(f"{t}: error ({e})")

ph = marks(cities)
latest_all = run(QUERIES["latest_city"])
latest = latest_all[latest_all["city"].isin(cities)].reset_index(drop=True)
pm = latest.dropna(subset=["pm25_openmeteo"])

# ======================================================================= header
fetched = run("SELECT MAX(fetched_at_utc) AS t FROM live_readings")["t"].iloc[0]
stamp = ""
if fetched:
    ist = pd.to_datetime(fetched) + timedelta(hours=5, minutes=30)
    stamp = f"<span class='chip'>Updated {ist:%d %b, %H:%M} IST</span>"
    age_h = (pd.Timestamp.now("UTC").tz_localize(None) - pd.to_datetime(fetched)).total_seconds() / 3600
    if age_h > 6:      # data purana hai: saaf warning
        age_txt = f"{age_h:.0f} hours" if age_h < 48 else f"{age_h / 24:.0f} days"
        stamp += (f" <span class='chip warn'>Data is {age_txt} old. "
                  f"It refreshes automatically 3 times a day.</span>")
title_slot.markdown(
    f"<h1 style='margin:0 0 .15rem 0;font-weight:800'>Climate Impact</h1>"
    f"<div style='color:{MUTED}'>Weather, air quality and emissions for {len(cities)} Indian "
    f"{'city' if len(cities) == 1 else 'cities'} &nbsp;{stamp}</div>", unsafe_allow_html=True)

# focus city pills, each with its live AQI colour dot
dots = {r.city: aqi_dot(r.us_aqi) for r in latest.itertuples()}
default_focus = "Delhi" if "Delhi" in cities else cities[0]
st.markdown("<div class='csub' style='margin:.9rem 0 .2rem 0'>Pick a city. The dot shows today's US AQI band.</div>",
            unsafe_allow_html=True)
cur = st.session_state.get("focus_city")
if cur not in cities:                       # pehli baar, ya city sidebar se hata di gayi, ya selected pill dobara dabayi
    last = st.session_state.get("_last_focus")
    st.session_state["focus_city"] = last if last in cities else default_focus
focus = st.pills("Focus city", cities, key="focus_city", label_visibility="collapsed",
                 format_func=lambda c: f"{dots.get(c, '⚪')} {c}") or st.session_state["focus_city"]
st.session_state["_last_focus"] = focus
frow = latest[latest["city"] == focus].iloc[0]
st.markdown(f"<div class='csub' style='margin:.3rem 0 .6rem 0'>Showing <b style='color:var(--ink)'>{esc(focus)}</b>: "
            f"every card and chart below follows this city.</div>", unsafe_allow_html=True)

# ================================================================== KPI strip (follows the focus city)
em_ind = run("SELECT year, co2_mt FROM emissions_country WHERE country = 'India' ORDER BY year")
last7 = run(QUERIES["last7"])
k = []

ft = frow["temp_c"]
if pd.notna(ft):
    avg_t = latest["temp_c"].mean()
    k.append(kcard(f"Temperature in {esc(focus)}", f"{ft:.1f} &deg;C",
                   f"{ft - avg_t:+.1f} &deg;C vs average of {len(latest)} cities", TEAL))

fp = frow["pm25_openmeteo"]
if pd.notna(fp) and len(pm):
    rank = int((pm["pm25_openmeteo"] > fp).sum()) + 1
    k.append(kcard(f"PM2.5 in {esc(focus)}", f"{fp:.0f} &micro;g/m&sup3;",
                   f"Rank {rank} of {len(pm)} (1 = most polluted)", aqi_color(frow["us_aqi"])))

l7 = last7[last7["city"] == focus]
if len(l7):
    r7 = l7.iloc[0]
    k.append(kcard(f"7-day average PM2.5, {esc(focus)}", f"{r7['avg_pm25_7d']:.0f} &micro;g/m&sup3;",
                   f"Worst day {r7['max_pm25_7d']:.0f} &micro;g/m&sup3;", "#E59A3B"))

if len(em_ind) >= 2:
    a_, b_ = em_ind.iloc[-2], em_ind.iloc[-1]
    k.append(kcard(f"India CO<sub>2</sub> in {int(b_['year'])}, annual", f"{b_['co2_mt']:,.0f} Mt",
                   f"{(b_['co2_mt'] / a_['co2_mt'] - 1) * 100:+.1f}% vs {int(a_['year'])}, national", "#7B8CDE"))
st.markdown("<div class='kpi-grid'>" + "".join(k) + "</div>", unsafe_allow_html=True)

# ======================================================================== hero
h1, h2, h3 = st.columns([1.15, 1, 0.85], gap="medium")

with h1:
    with st.container(key="card_flip"):
        st.markdown(
            f"<div class='ctitle'>Temperature now in {esc(focus)}</div>" + flip_html(frow["temp_c"]) +
            f"<div class='flip-meta'>Rain, last hour: {num(frow['rain_mm'])} mm"
            f" &nbsp;<span class='chip'>OpenWeather live</span></div>"
            f"<div class='flip-meta' style='margin-top:.5rem'>Average across selected cities: "
            f"<b>{num(latest['temp_c'].mean())} &deg;C</b></div>", unsafe_allow_html=True)

with h2:
    with st.container(key="card_gauge"):
        us = frow["us_aqi"]
        cat = frow["us_category"] if isinstance(frow["us_category"], str) else "No data"
        st.markdown(
            f"<div class='ctitle'>Air quality in {esc(focus)}</div><div class='csub'>US AQI scale, 0 to 500</div>"
            + gauge_html(us) + f"<div class='g-num'>{num(us, 0)}</div><div class='g-cat'>{esc(cat)}</div>"
            f"<div class='g-cat'>PM2.5 {num(frow['pm25_openmeteo'])} &micro;g/m&sup3; (Open-Meteo, modelled)</div>",
            unsafe_allow_html=True)

with h3:
    with st.container(key="card_outlook"):
        st.markdown(f"<div class='ctitle'>PM2.5 outlook, next 7 days</div><div class='csub'>{esc(focus)}</div>",
                    unsafe_allow_html=True)
        fo = run("SELECT yhat, lower, upper, method FROM forecasts WHERE city = ? AND metric = 'pm2_5' "
                 "AND run_date = (SELECT MAX(run_date) FROM forecasts)", (focus,))
        if fo.empty:
            st.caption("Forecast nahi mila. `python src/forecast.py` chalao.")
        else:
            base = fo["method"].iloc[0] == "naive_7d_mean"
            st.markdown(
                f"<div class='o-big'>{fo['yhat'].mean():.0f} <span style='font-size:1rem'>&micro;g/m&sup3;</span></div>"
                f"<div class='o-line'>Likely range <b>{fo['lower'].min():.0f} to {fo['upper'].max():.0f}</b> (80%)</div>"
                f"<div class='o-line'>Method: <span class='chip{' warn' if base else ''}'>"
                f"{'same as last week' if base else 'trend model'}</span></div>"
                f"<div class='o-line' style='margin-top:.6rem'>Short-term trend only, not a guarantee. "
                f"It cannot predict seasonal spikes.</div>", unsafe_allow_html=True)

# ================================================================== second row
r1, r2, r3 = st.columns([1, 1.7, 1.1], gap="medium")

with r1:
    with st.container(key="card_rain"):
        st.markdown(f"<div class='ctitle'>Rainfall by month</div><div class='csub'>{esc(focus)}, mm. "
                    f"First and last month may be partial.</div>", unsafe_allow_html=True)
        rain = run("SELECT substr(date,1,7) AS month, SUM(precip_mm) AS rain_mm, COUNT(*) AS days "
                   "FROM daily_weather WHERE city = ? AND date >= "
                   "date((SELECT MAX(date) FROM daily_weather), '-180 days') GROUP BY month ORDER BY month", (focus,))
        if rain.empty:
            st.caption("Is city ka rainfall data nahi mila.")
        else:
            rain["month"] = pd.to_datetime(rain["month"] + "-01")
            ch = alt.Chart(rain).mark_bar(size=24, cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=TEAL).encode(
                x=alt.X("month:T", timeUnit="yearmonth", title=None, axis=alt.Axis(format="%b", labelAngle=0)),
                y=alt.Y("rain_mm:Q", title=None),
                tooltip=[alt.Tooltip("month:T", format="%B %Y"), alt.Tooltip("rain_mm:Q", format=".0f", title="mm"), "days"]
            ).properties(height=210)
            show_chart(style(ch), width="stretch")

with r2:
    with st.container(key="card_trend"):
        st.markdown(f"<div class='ctitle'>PM2.5 trend</div><div class='csub'>{esc(focus)} (solid) and average of "
                    f"selected cities (dashed), &micro;g/m&sup3;</div>", unsafe_allow_html=True)
        days = int(min(window, 90))
        air = run(f"SELECT city, date, pm2_5_mean FROM daily_air WHERE city IN ({ph}) AND date >= "
                  f"date((SELECT MAX(date) FROM daily_air), '-{days} days') ORDER BY date", tuple(cities))
        if air.empty:
            st.caption("PM2.5 history nahi mili.")
        else:
            air = to_dt(air, "date")
            f_df = air[air["city"] == focus]
            avg = air.groupby("date", as_index=False)["pm2_5_mean"].mean()
            if f_df.empty:
                st.caption(f"{focus} ke liye PM2.5 history nahi mili.")
                f_df = None
            if f_df is not None:
                c_hi, c_lo = ("rgba(53,196,214,0.45)", "rgba(53,196,214,0.02)") if PAL["name"] == "Dark" \
                    else ("rgba(26,166,183,0.45)", "rgba(26,166,183,0.02)")
                grad = alt.Gradient(gradient="linear", stops=[alt.GradientStop(color=c_hi, offset=0),
                                                              alt.GradientStop(color=c_lo, offset=1)], x1=1, x2=1, y1=0, y2=1)
                area = alt.Chart(f_df).mark_area(color=grad, line={"color": TEAL, "strokeWidth": 2.5}).encode(
                    x=alt.X("date:T", title=None, axis=alt.Axis(format="%d %b")), y=alt.Y("pm2_5_mean:Q", title=None),
                    tooltip=[alt.Tooltip("date:T", format="%d %b"), alt.Tooltip("pm2_5_mean:Q", format=".1f", title=focus)])
                dashed = alt.Chart(avg).mark_line(strokeDash=[5, 4], color=INK, opacity=.6).encode(x="date:T", y="pm2_5_mean:Q")
                dot = alt.Chart(f_df.tail(1)).mark_point(filled=True, size=90, color=TEAL, stroke="white", strokeWidth=2).encode(
                    x="date:T", y="pm2_5_mean:Q")
                show_chart(style((area + dashed + dot).properties(height=230)), width="stretch")

with r3:
    with st.container(key="card_rank"):
        n_bad = int((latest["us_aqi"] > 150).sum())
        st.markdown(f"<div class='ctitle'>Cities by PM2.5 now</div><div class='csub'>{esc(focus)} is highlighted. "
                    f"{n_bad} of {len(latest)} cities are above US AQI 150.</div>", unsafe_allow_html=True)
        if pm.empty:
            st.caption("Live PM2.5 nahi mila.")
        else:
            rk = pm[["city", "pm25_openmeteo", "us_aqi"]].copy()
            rk["color"] = rk["us_aqi"].map(aqi_color)
            base_c = alt.Chart(rk).encode(y=alt.Y("city:N", sort="-x", title=None))
            bars = base_c.mark_bar(cornerRadiusEnd=5, size=14).encode(
                x=alt.X("pm25_openmeteo:Q", title=None), color=alt.Color("color:N", scale=None),
                opacity=alt.condition(alt.datum.city == focus, alt.value(1), alt.value(0.38)),
                tooltip=["city", alt.Tooltip("pm25_openmeteo:Q", format=".1f", title="PM2.5"), "us_aqi"])
            txt = base_c.mark_text(align="left", dx=4, color=MUTED, fontSize=11).encode(
                x="pm25_openmeteo:Q", text=alt.Text("pm25_openmeteo:Q", format=".0f"))
            show_chart(style((bars + txt).properties(height=max(120, 26 * len(rk)))), width="stretch")

# ================================================================== deep dive
st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
tab_live, tab_trend, tab_fc, tab_em, tab_sql = st.tabs(["Live table", "Trends", "Forecast", "Emissions", "SQL Explorer"])

with tab_live:
    show = latest.rename(columns={
        "city": "City", "temp_c": "Temp (°C)", "rain_mm": "Rain (mm)", "pm25_openmeteo": "PM2.5 Open-Meteo",
        "us_aqi": "US AQI", "us_category": "US category", "pm25_openweather": "PM2.5 OpenWeather",
        "ow_aqi": "OW AQI", "ow_category": "OW category"})
    st.markdown(html_table(show, decimals={"Temp (°C)": 1, "Rain (mm)": 1, "PM2.5 Open-Meteo": 1, "PM2.5 OpenWeather": 1,
                                           "US AQI": 0, "OW AQI": 0},
                           flags={"US AQI": lambda v: v > 150, "OW AQI": lambda v: v >= 4}), unsafe_allow_html=True)
    st.caption("Red = US AQI above 150, or OpenWeather AQI 4-5. Dono AQI scales alag hain "
               "(US: 0-500, OpenWeather: 1-5), seedha compare mat karo.")
    left, right = st.columns(2)
    with left:
        long = latest.melt(id_vars="city", value_vars=["pm25_openmeteo", "pm25_openweather"],
                           var_name="source", value_name="pm25").dropna()
        long["source"] = long["source"].map({"pm25_openmeteo": "Open-Meteo", "pm25_openweather": "OpenWeather"})
        chart = alt.Chart(long, title="Live PM2.5 by city, two sources (µg/m³)").mark_bar(
            cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("city:N", title=None, axis=alt.Axis(labelAngle=-30)), xOffset="source:N", y=alt.Y("pm25:Q", title="PM2.5"),
            color=alt.Color("source:N", title=None, scale=alt.Scale(range=["#7B8CDE", TEAL])),
            tooltip=["city", "source", alt.Tooltip("pm25:Q", format=".1f")])
        show_chart(style(chart), width="stretch")
    with right:
        pos = run(f"SELECT city, MAX(lat) AS lat, MAX(lon) AS lon FROM live_readings WHERE city IN ({ph}) GROUP BY city",
                  tuple(cities))
        mp = pos.merge(pm[["city", "pm25_openmeteo"]], on="city", how="inner")
        if len(mp):
            mp["size"] = mp["pm25_openmeteo"].clip(lower=5) * 1200
            st.caption("Map: circle size = PM2.5 (Open-Meteo)")
            st.map(mp, latitude="lat", longitude="lon", size="size", color="#E4572E")

with tab_trend:
    metric = choose(st.segmented_control, "Metric", ["Temperature", "PM2.5", "Rainfall (monthly)"], "Temperature", "trend_metric")
    if metric == "Temperature":
        df = run(f"SELECT city, date, temp_mean_c FROM daily_weather WHERE city IN ({ph}) AND date >= "
                 f"date((SELECT MAX(date) FROM daily_weather), '-{int(window)} days') ORDER BY date", tuple(cities))
        if df.empty:
            st.info("Data nahi mila.")
        else:
            ch = (alt.Chart(to_dt(df, "date"), title=f"Daily mean temperature, last {window} days (°C)")
                  .mark_line(strokeWidth=2).encode(
                      x=alt.X("date:T", title=None), y=alt.Y("temp_mean_c:Q", title="°C", scale=alt.Scale(zero=False)),
                      color=alt.Color("city:N", scale=alt.Scale(scheme="tableau10")),
                      tooltip=["city", "date:T", alt.Tooltip("temp_mean_c:Q", format=".1f")]).interactive())
            show_chart(style(ch), width="stretch")
            st.caption("Source: Open-Meteo archive (ERA5 model reanalysis), ~7 din ki deri se update.")
    elif metric == "PM2.5":
        df = run(f"SELECT city, date, pm2_5_mean FROM daily_air WHERE city IN ({ph}) AND date >= "
                 f"date((SELECT MAX(date) FROM daily_air), '-{int(min(window, 90))} days') ORDER BY date", tuple(cities))
        if df.empty:
            st.info("Data nahi mila.")
        else:
            ch = (alt.Chart(to_dt(df, "date"), title="Daily mean PM2.5 (µg/m³)").mark_line(strokeWidth=2).encode(
                x=alt.X("date:T", title=None), y=alt.Y("pm2_5_mean:Q", title="PM2.5"),
                color=alt.Color("city:N", scale=alt.Scale(scheme="tableau10")),
                tooltip=["city", "date:T", alt.Tooltip("pm2_5_mean:Q", format=".1f")]).interactive())
            show_chart(style(ch), width="stretch")
            st.caption("PM2.5 history sirf ~90 din ki hai (modelled data).")
    else:
        df = run(f"SELECT city, substr(date,1,7) AS month, SUM(precip_mm) AS rain_mm, COUNT(*) AS days "
                 f"FROM daily_weather WHERE city IN ({ph}) AND date >= "
                 f"date((SELECT MAX(date) FROM daily_weather), '-{int(window)} days') "
                 f"GROUP BY city, month ORDER BY month", tuple(cities))
        if df.empty:
            st.info("Data nahi mila.")
        else:
            heat = alt.Chart(df, title="Monthly rainfall (mm)").mark_rect(cornerRadius=3).encode(
                x=alt.X("month:O", title=None), y=alt.Y("city:N", title=None),
                color=alt.Color("rain_mm:Q", scale=alt.Scale(scheme="blues"), title="mm"),
                tooltip=["city", "month", alt.Tooltip("rain_mm:Q", format=".0f"), "days"])
            show_chart(style(heat), width="stretch")
            st.caption("Pehla aur aakhri mahina adhoora ho sakta hai (tooltip mein 'days' dekho).")

with tab_fc:
    fc_cities = run("SELECT DISTINCT city FROM forecasts ORDER BY city")["city"].tolist()
    if focus not in fc_cities:
        st.info(f"{focus} ka forecast nahi mila. `python src/forecast.py` chalao.")
    else:
        st.caption(f"City: {focus} (upar pills se badlo)")
        fm = choose(st.segmented_control, "Metric", ["PM2.5", "Temperature"], "PM2.5", "fc_metric")
        metric_key, table, col, unit = (("pm2_5", "daily_air", "pm2_5_mean", "µg/m³") if fm == "PM2.5"
                                        else ("temp_mean_c", "daily_weather", "temp_mean_c", "°C"))
        obs = run(f"SELECT date, {col} AS value FROM {table} WHERE city = ? ORDER BY date DESC LIMIT 30", (focus,))
        fc = run("SELECT forecast_date AS date, yhat, lower, upper, method FROM forecasts "
                 "WHERE city = ? AND metric = ? AND run_date = (SELECT MAX(run_date) FROM forecasts) "
                 "ORDER BY forecast_date", (focus, metric_key))
        bt = run("SELECT mae_model, mae_naive, chosen_method, folds FROM forecast_backtest "
                 "WHERE city = ? AND metric = ? AND run_date = (SELECT MAX(run_date) FROM forecast_backtest)",
                 (focus, metric_key))
        if fc.empty:
            st.info("Is metric ka forecast nahi hai.")
        else:
            obs, fc = to_dt(obs, "date"), to_dt(fc, "date")
            band = alt.Chart(fc).mark_area(opacity=0.2, color=CORAL).encode(
                x="date:T", y=alt.Y("lower:Q", title=f"{fm} ({unit})", scale=alt.Scale(zero=False)), y2="upper:Q")
            line_f = alt.Chart(fc).mark_line(strokeDash=[5, 4], color=CORAL, strokeWidth=2).encode(
                x="date:T", y="yhat:Q", tooltip=["date:T", alt.Tooltip("yhat:Q", format=".1f", title="forecast"),
                                                 alt.Tooltip("lower:Q", format=".1f"), alt.Tooltip("upper:Q", format=".1f")])
            line_o = alt.Chart(obs).mark_line(color=TEAL, strokeWidth=2.5).encode(
                x="date:T", y="value:Q", tooltip=["date:T", alt.Tooltip("value:Q", format=".1f")])
            show_chart(style((band + line_f + line_o).properties(
                title=f"{focus}: last 30 days (teal) and forecast (red dashed, 80% range)")), width="stretch")
            if len(bt):
                r = bt.iloc[0]
                m1, m2, m3 = st.columns(3)
                m1.metric("Method used", str(r["chosen_method"]))
                m2.metric("Backtest error: model", f"{r['mae_model']:.2f}")
                m3.metric("Backtest error: baseline", f"{r['mae_naive']:.2f}")
                st.caption("Backtest error = average absolute error on hidden weeks (kam = behtar). "
                           "Agar baseline jeeta, toh forecast sirf 'pichle hafte jaisa' hai.")
        st.warning("Statistical short-term trend hai, guarantee nahi. PM2.5 mein seasonal spike "
                   "(jaise winter smog) ye model nahi pakad sakta.")
        with st.expander("Saare backtest results"):
            allbt = run(QUERIES["backtest"])
            st.markdown(html_table(allbt[allbt["city"].isin(cities)], decimals={"mae_model": 2, "mae_naive": 2}),
                        unsafe_allow_html=True)

with tab_em:
    em = run("SELECT country, year, co2_mt, co2_per_capita_t FROM emissions_country ORDER BY country, year")
    if em.empty:
        st.info("Emissions data nahi mila. `python src/load_emissions.py` chalao.")
    else:
        st.caption("Annual, country-level (fossil fuel + cement), Our World in Data. Live data nahi hai, "
                   "aur kisi city ka number nahi hai.")
        ind = em[em["country"] == "India"].sort_values("year")
        if len(ind) >= 2:
            a_, b_ = ind.iloc[-2], ind.iloc[-1]
            k1, k2, k3 = st.columns(3)
            k1.metric(f"India CO₂ ({int(b_['year'])})", f"{b_['co2_mt']:,.0f} Mt",
                      f"{(b_['co2_mt'] / a_['co2_mt'] - 1) * 100:+.1f}% vs {int(a_['year'])}", delta_color="off")
            k2.metric("India per person", f"{b_['co2_per_capita_t']:.2f} t")
            world = em[(em["country"] == "World") & (em["year"] == b_["year"])]
            if len(world):
                k3.metric("India share of world", f"{b_['co2_mt'] / world['co2_mt'].iloc[0] * 100:.1f}%")
        kind = choose(st.segmented_control, "Show", ["Total (Mt CO₂)", "Per person (tonnes)"], "Total (Mt CO₂)", "em_kind")
        ycol = "co2_mt" if kind.startswith("Total") else "co2_per_capita_t"
        ch = alt.Chart(em, title=kind).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0, values=list(range(1990, 2030, 5)))),
            y=alt.Y(f"{ycol}:Q", title=kind), color=alt.Color("country:N", scale=alt.Scale(scheme="tableau10")),
            tooltip=["country", "year", alt.Tooltip(f"{ycol}:Q", format=",.2f")])
        show_chart(style(ch), width="stretch")

with tab_sql:
    st.caption("Yahan database par seedhe SQL chalao. Sirf SELECT / WITH allowed hai, "
               "aur database read-only mode mein khulta hai.")
    names = ["(custom)"] + list(QUERIES.keys())
    pick = st.selectbox("Report query chuno (sql/daily_report.sql se)", names)
    default = QUERIES[pick] if pick != "(custom)" else "SELECT * FROM v_latest_readings"
    sql = st.text_area("SQL", value=default, height=200, key=f"sql_{pick}")
    if st.button("Run query"):
        s = sql.strip().rstrip(";").strip()
        if ";" in s:
            st.error("Ek baar mein sirf ek query chalao.")
        elif not s.lower().startswith(("select", "with")):
            st.error("Sirf SELECT ya WITH se shuru hone wali query allowed hai.")
        else:
            try:
                out = _run(s).head(1000)
                st.success(f"{len(out)} rows (max 1000 dikhte hain)")
                st.markdown(html_table(out), unsafe_allow_html=True)
                st.download_button("Download CSV", out.to_csv(index=False).encode("utf-8"),
                                   file_name="query_result.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Query error: {e}")
    with st.expander("Tables aur views ki list"):
        objs = run("SELECT type, name FROM sqlite_master WHERE type IN ('table','view') "
                   "AND name NOT LIKE 'sqlite_%' ORDER BY type, name")
        st.markdown(html_table(objs), unsafe_allow_html=True)

# ================================================= reports (apne aap bante hain, koi python command nahi)
with report_slot:
    try:
        with st.spinner("Aaj ka report ban raha hai..."):
            x_name, x_bytes, p_name, p_bytes = build_reports(str(fetched))
        st.download_button(f"Download Excel MIS ({x_name[4:14]})", x_bytes, file_name=x_name,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button(f"Download PDF report ({p_name[7:17]})", p_bytes, file_name=p_name,
                           mime="application/pdf")
    except Exception as e:
        st.caption(f"Report abhi nahi ban saki: {str(e)[:120]}")