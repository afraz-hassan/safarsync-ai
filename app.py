"""
app.py — SafarSync AI  |  Cinematic High-Contrast UI/UX Redesign

Full redesign: Deep obsidian theme, vintage golden hour accents,
dramatic high-contrast lighting, custom SVG logo, and cinematic animations.
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from html import escape as _html_escape
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Module imports — wrapped so a missing secret shows a styled error page.
# ---------------------------------------------------------------------------
try:
    import database as db
    import analytics
    import anomaly
    import insights
    import maintenance
    import receipt_scanner
    import validation
    import pdf_report
    import demo_data
    import config as _config
    from ai_client import ask_text
    _modules_loaded = True
    _config_error: str = ""
except RuntimeError as _exc:
    _modules_loaded = False
    _config_error = str(_exc)


def _esc(value: Any) -> str:
    """HTML-escape a value for safe use in unsafe_allow_html=True contexts."""
    return _html_escape(str(value)) if value is not None else ""


# ============================================================
# DESIGN SYSTEM — Cinematic High-Contrast & Golden Hour
# ============================================================
_CSS = """
<style>
/* ── Google Fonts ─────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;700;900&display=swap');

/* ── Global reset ────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}
h1, h2, h3, .logo-mark, [data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ── App background (Cinematic Obsidian) ─────── */
.stApp {
    background: radial-gradient(circle at 50% 0%, #151515 0%, #050505 80%, #000000 100%) !important;
    min-height: 100vh;
}

/* ── Sidebar ─────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid rgba(245, 166, 35, 0.15) !important;
}
[data-testid="stSidebar"] * { color: #d4d4d8 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(245, 166, 35, 0.3) !important;
    border-radius: 8px !important;
    color: #fafafa !important;
}

/* ── Navigation ──────────────────────────────── */
[data-testid="stSidebarNav"] li span {
    color: #a1a1aa !important;
    font-weight: 500 !important;
    transition: all 0.3s ease;
}
[data-testid="stSidebarNav"] li:hover span {
    color: #F5A623 !important;
    text-shadow: 0 0 10px rgba(245,166,35,0.4);
}
[data-testid="stSidebarNav"] li[aria-selected="true"] span {
    color: #F8E71C !important;
}
[data-testid="stSidebarNav"] li[aria-selected="true"] {
    background: linear-gradient(90deg, rgba(245,166,35,0.15) 0%, transparent 100%) !important;
    border-radius: 0 8px 8px 0;
    border-left: 3px solid #F5A623 !important;
}

/* ── Main content area ───────────────────────── */
.main .block-container {
    padding: 2rem 3rem 3rem !important;
    max-width: 1400px !important;
}

/* ── Page titles ─────────────────────────────── */
h1 { color: #ffffff !important; font-weight: 900 !important; letter-spacing: -1px; text-shadow: 0 4px 20px rgba(0,0,0,0.8); }
h2 { color: #f4f4f5 !important; font-weight: 700 !important; }
h3 { color: #e4e4e7 !important; font-weight: 700 !important; }
p, li, span, label { color: #a1a1aa !important; }

/* ── Metric cards ────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(30,30,30,0.6) 0%, rgba(10,10,10,0.8) 100%) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-bottom: 2px solid #F5A623 !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    backdrop-filter: blur(16px) !important;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
[data-testid="stMetric"]:hover {
    transform: translateY(-5px) !important;
    border-color: rgba(245, 166, 35, 0.4) !important;
    box-shadow: 0 15px 40px rgba(245, 166, 35, 0.15), 0 0 15px rgba(245, 166, 35, 0.1) inset !important;
}
[data-testid="stMetricLabel"] { color: #a1a1aa !important; font-size: 0.8rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.1em; }
[data-testid="stMetricValue"] { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 900 !important; text-shadow: 0 2px 10px rgba(0,0,0,0.5); }
[data-testid="stMetricDelta"] { font-size: 0.85rem !important; }

/* ── Buttons ─────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #F5A623 0%, #D0021B 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 6px 20px rgba(208, 2, 27, 0.3) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(245, 166, 35, 0.5) !important;
    background: linear-gradient(135deg, #F8E71C 0%, #F5A623 100%) !important;
    color: #050505 !important;
}

/* Danger / delete button */
.danger-btn .stButton > button {
    background: rgba(220, 38, 38, 0.1) !important;
    color: #ef4444 !important;
    border: 1px solid rgba(239,68,68,0.4) !important;
    box-shadow: none !important;
}
.danger-btn .stButton > button:hover {
    background: #ef4444 !important;
    color: #fff !important;
    box-shadow: 0 4px 15px rgba(239,68,68,0.4) !important;
}

/* Ghost / secondary button */
.ghost-btn .stButton > button {
    background: transparent !important;
    color: #F5A623 !important;
    border: 1px solid rgba(245, 166, 35, 0.4) !important;
    box-shadow: none !important;
}
.ghost-btn .stButton > button:hover {
    background: rgba(245, 166, 35, 0.1) !important;
    box-shadow: 0 0 15px rgba(245, 166, 35, 0.2) !important;
}

/* ── Forms & inputs ──────────────────────────── */
.stForm {
    background: rgba(15,15,15,0.6) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
    padding: 2rem !important;
    backdrop-filter: blur(12px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(0,0,0,0.4) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #fafafa !important;
    transition: all 0.3s ease;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #F5A623 !important;
    box-shadow: 0 0 0 2px rgba(245,166,35,0.2) !important;
}

/* Form submit button */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #00E5FF, #007BFF) !important;
    color: #fff !important;
    box-shadow: 0 6px 20px rgba(0, 229, 255, 0.3) !important;
}
.stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #33EBFF, #0056b3) !important;
    box-shadow: 0 8px 25px rgba(0, 229, 255, 0.5) !important;
}

/* ── Divider ─────────────────────────────────── */
hr { border-color: rgba(255,255,255,0.08) !important; margin: 2rem 0 !important; }

/* ── Custom card utility (Cinematic) ─────────── */
.ss-card {
    background: linear-gradient(145deg, rgba(20,20,20,0.8), rgba(5,5,5,0.9));
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
    position: relative;
}
.ss-card:hover {
    transform: translateY(-2px);
    border-color: rgba(245,166,35,0.3);
    box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 15px rgba(245,166,35,0.05) inset;
}
.ss-card-accent-top::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #F5A623, #00E5FF);
    border-radius: 12px 12px 0 0;
}

/* Record type badges */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.badge-fuel        { background: rgba(0,229,255,0.1); color: #00E5FF !important; border: 1px solid rgba(0,229,255,0.3); }
.badge-maintenance { background: rgba(245,166,35,0.1); color: #F5A623 !important; border: 1px solid rgba(245,166,35,0.3); }
.badge-insurance   { background: rgba(208,2,27,0.1); color: #FF4D4D !important; border: 1px solid rgba(208,2,27,0.3); }
.badge-unknown     { background: rgba(161,161,170,0.1); color: #d4d4d8 !important; border: 1px solid rgba(161,161,170,0.3); }

/* Insight box (High Contrast) */
.insight-box {
    background: rgba(10,10,10,0.8);
    border-left: 4px solid #F5A623;
    border-right: 1px solid rgba(255,255,255,0.05);
    border-top: 1px solid rgba(255,255,255,0.05);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    border-radius: 0 12px 12px 0;
    padding: 1.5rem 2rem;
    color: #e4e4e7 !important;
    font-size: 1rem;
    line-height: 1.8;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    position: relative;
}
.insight-box::before {
    content: "✦";
    position: absolute;
    top: 1.5rem; left: -14px;
    background: #F5A623;
    color: #000;
    width: 24px; height: 24px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%;
    font-size: 0.8rem;
    font-weight: bold;
    box-shadow: 0 0 10px #F5A623;
}

/* Chat bubble */
.chat-bubble {
    background: linear-gradient(135deg, rgba(30,30,30,0.8), rgba(15,15,15,0.9));
    border: 1px solid rgba(245,166,35,0.2);
    border-radius: 0 12px 12px 12px;
    padding: 1.5rem;
    margin-top: 1rem;
    color: #fafafa !important;
    font-size: 0.95rem;
    line-height: 1.7;
    box-shadow: 0 5px 20px rgba(0,0,0,0.4);
}

/* Animations (Cinematic Reveal) */
@keyframes cinematic-reveal {
    0% { opacity: 0; filter: blur(10px); transform: scale(0.98) translateY(15px); }
    100% { opacity: 1; filter: blur(0); transform: scale(1) translateY(0); }
}
.fade-in { animation: cinematic-reveal 0.7s cubic-bezier(0.165, 0.84, 0.44, 1) forwards; }

/* Logo area in sidebar */
.sidebar-logo {
    text-align: center;
    padding: 1rem 0;
    margin-bottom: 1rem;
}
.sidebar-logo .logo-mark {
    font-size: 2.2rem;
    color: #ffffff;
    font-weight: 900;
    letter-spacing: -1.5px;
    display: block;
    margin-top: 5px;
    text-shadow: 0 0 20px rgba(255,255,255,0.2);
}
.sidebar-logo .logo-sub {
    font-size: 0.7rem !important;
    color: #a1a1aa !important;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    font-weight: 600 !important;
    margin-top: -5px;
}
.sidebar-vehicle-pill {
    background: rgba(245,166,35,0.05);
    border: 1px solid rgba(245,166,35,0.3);
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-top: 0.5rem;
    font-size: 0.8rem !important;
    color: #F5A623 !important;
    text-align: center;
    letter-spacing: 0.1em;
}

/* Page hero header */
.page-hero {
    margin-bottom: 2.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding-bottom: 1.5rem;
}
.page-hero h1 {
    margin: 0 !important;
    font-size: 2.5rem !important;
}
.page-hero p {
    margin: 0.5rem 0 0 !important;
    color: #a1a1aa !important;
    font-size: 1.05rem !important;
    letter-spacing: 0.02em;
}

/* Section label */
.section-label {
    font-size: 0.75rem !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #71717a !important;
    margin-bottom: 1rem;
    border-left: 2px solid #F5A623;
    padding-left: 10px;
}
</style>
"""

# ============================================================
# PLOTLY THEME  — Cinematic High Contrast
# ============================================================
_PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#a1a1aa", size=12),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.03)",
        linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(color="#71717a"),
        title_font=dict(color="#a1a1aa"),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.03)",
        linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(color="#71717a"),
        title_font=dict(color="#a1a1aa"),
    ),
    legend=dict(
        bgcolor="rgba(10,10,10,0.8)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
        font=dict(color="#e4e4e7"),
    ),
    margin=dict(l=10, r=10, t=30, b=10),
    height=360,
)
_COLOR_SEQ = ["#F5A623", "#00E5FF", "#FF4D4D", "#F8E71C", "#B8E986", "#9B51E0"]


# ============================================================
# HELPERS
# ============================================================
def fmt_pkr(amount: float | int | None) -> str:
    if amount is None:
        return "PKR 0"
    return f"PKR {amount:,.0f}"


def require_vehicle() -> int | None:
    vid = st.session_state.get("vehicle_id")
    if not vid:
        st.markdown("""
        <div class="ss-card fade-in" style="text-align:center;padding:3.5rem;">
            <div style="font-size:3rem;margin-bottom:1rem; text-shadow: 0 0 20px rgba(245,166,35,0.5);">🚘</div>
            <div style="color:#ffffff;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.4rem;margin-bottom:0.5rem;">
                No Vehicle Selected
            </div>
            <div style="color:#a1a1aa;font-size:0.95rem;">
                Please select a vehicle from the cinematic sidebar to begin.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return None
    if not any(v["id"] == vid for v in db.get_vehicles()):
        st.session_state.pop("vehicle_id", None)
        st.warning("Selected vehicle no longer exists. Please select another.")
        return None
    return vid


def _badge(rec_type: str) -> str:
    cls = f"badge-{rec_type}" if rec_type in ("fuel","maintenance","insurance") else "badge-unknown"
    return f'<span class="badge {cls}">{_esc(rec_type)}</span>'


def _pill_severity(sev: str) -> str:
    colors = {"high":"#ef4444", "warning":"#F5A623", "info":"#00E5FF"}
    c = colors.get(sev, "#fff")
    return f'<span style="color:{c}; border: 1px solid {c}; padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em;">{"⬆" if sev=="high" else "▲" if sev=="warning" else "●"} {_esc(sev)}</span>'


def _page_hero(title: str, subtitle: str, icon: str = "") -> None:
    st.markdown(f"""
    <div class="page-hero fade-in">
        <h1>{icon} {_esc(title)}</h1>
        <p>{_esc(subtitle)}</p>
    </div>
    """, unsafe_allow_html=True)


def _section(label: str) -> None:
    st.markdown(f'<div class="section-label fade-in">{label}</div>', unsafe_allow_html=True)


def _empty_state(icon: str, title: str, body: str) -> None:
    st.markdown(f"""
    <div class="ss-card fade-in" style="text-align:center; padding:3rem 2rem;">
        <span style="font-size:3rem;display:block;margin-bottom:1rem;">{icon}</span>
        <div style="color:#f4f4f5;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem;margin-bottom:0.5rem;">{_esc(title)}</div>
        <p style="color:#a1a1aa;font-size:0.95rem;">{_esc(body)}</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# PAGE: DASHBOARD
# ============================================================
def page_dashboard():
    _page_hero("Dashboard", "Cinematic overview of your vehicle's financial data", "📊")

    vid = require_vehicle()
    if not vid:
        return

    metrics = analytics.get_summary_metrics(vid)

    # ── KPI Row 1 ──────────────────────────────────────────
    _section("SPENDING OVERVIEW")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Spend", fmt_pkr(metrics["total_spend"]))
    with c2:
        st.metric("Fuel Spend", fmt_pkr(metrics["fuel_spend"]))
    with c3:
        st.metric("Maintenance", fmt_pkr(metrics["maintenance_spend"]))
    with c4:
        st.metric("Insurance", fmt_pkr(metrics["insurance_spend"]))

    # ── KPI Row 2 ──────────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    _section("EFFICIENCY & DISTANCE")
    c5, c6, c7, c8 = st.columns(4)
    avg_eff = metrics.get("average_fuel_efficiency")
    cpk = metrics.get("cost_per_km")
    with c5:
        st.metric("Avg km/L", f"{avg_eff:.1f} km/L" if avg_eff else "—")
    with c6:
        st.metric("Cost/km", f"PKR {cpk:.2f}" if cpk else "—")
    with c7:
        st.metric("Distance Tracked", f"{metrics['total_distance']:,} km")
    with c8:
        records = db.get_records(vid)
        odometers = [r["odometer_km"] for r in records if r.get("odometer_km")]
        latest_odo = f"{max(odometers):,} km" if odometers else "—"
        st.metric("Latest Odometer", latest_odo)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ─────────────────────────────────────────────
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    ch1, ch2 = st.columns(2)

    with ch1:
        _section("FUEL EFFICIENCY TREND")
        eff_data = analytics.calculate_fuel_efficiency(vid)
        valid_eff = [e for e in eff_data if "efficiency_km_per_l" in e]
        if valid_eff:
            df = pd.DataFrame(valid_eff)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["efficiency_km_per_l"],
                mode="lines+markers",
                line=dict(color="#00E5FF", width=3),
                marker=dict(size=8, color="#00E5FF",
                            line=dict(color="#050505", width=2)),
                fill="tozeroy",
                fillcolor="rgba(0,229,255,0.1)",
                name="km/L",
            ))
            fig.update_layout(
                **_PLOT_LAYOUT,
                xaxis_title="Date",
                yaxis_title="km/L",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            _empty_state("⛽", "No efficiency data yet",
                         "Add at least two fuel records with odometer readings.")

    with ch2:
        _section("MONTHLY SPENDING")
        monthly = analytics.monthly_spending_summary(vid)
        if monthly:
            df = pd.DataFrame(monthly)
            fig = px.bar(
                df, x="month", y="total_amount", color="record_type",
                barmode="stack",
                color_discrete_map={
                    "fuel": "#00E5FF",
                    "maintenance": "#F5A623",
                    "insurance": "#FF4D4D",
                },
            )
            fig.update_layout(
                **_PLOT_LAYOUT,
                xaxis_title="Month",
                yaxis_title="Amount (PKR)",
                bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            _empty_state("📅", "No monthly data yet", "Start adding expenses to see spending trends.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Anomaly Alerts ─────────────────────────────────────
    _section("ANOMALY ALERTS")
    anomalies = anomaly.find_anomalies(vid)
    if anomalies:
        for a in anomalies:
            sev = a["severity"]
            bg  = {"high":"rgba(220,38,38,0.1)", "warning":"rgba(245,166,35,0.1)", "info":"rgba(0,229,255,0.1)"}.get(sev,"")
            bd  = {"high":"rgba(220,38,38,0.4)",  "warning":"rgba(245,166,35,0.4)",  "info":"rgba(0,229,255,0.4)"}.get(sev,"")
            st.markdown(f"""
            <div class="fade-in" style="background:{bg};border:1px solid {bd};border-radius:8px;
                        padding:1rem 1.5rem;margin-bottom:0.8rem;display:flex;
                        align-items:center;gap:1rem;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
                {_pill_severity(sev)}
                <span style="color:#fafafa;font-size:0.95rem;">{_esc(a['message'])}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="fade-in" style="background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.3);
                    border-radius:8px;padding:1rem 1.5rem;color:#34d399;font-size:0.95rem;">
            ✅ &nbsp;System checks clear — no spending anomalies detected.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Insight Card ────────────────────────────────────
    _section("AI INTELLIGENCE")
    col_btn, col_spacer = st.columns([1, 4])
    with col_btn:
        if st.button("✦ Generate Insight", key="gen_insight"):
            with st.spinner("Analyzing high-contrast data patterns..."):
                insight_text = insights.get_vehicle_insight(vid)
                st.session_state["last_insight"] = insight_text

    if "last_insight" in st.session_state:
        st.markdown(f"""
        <div class="insight-box fade-in">
            {_esc(st.session_state["last_insight"])}
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# PAGE: SCAN RECEIPT
# ============================================================
def page_scan_receipt():
    _page_hero("Scan Receipt", "Upload documentation for AI extraction", "📷")

    vid = require_vehicle()
    if not vid:
        return

    # Determine current step for progress bar
    step = 1
    if "_scan_ocr" in st.session_state:
        step = 2
    if "_scan_validated" in st.session_state:
        step = 3

    st.markdown(f"""
    <div style="display:flex; gap:1rem; margin-bottom:1.5rem;">
        <div style="flex:1; height:4px; border-radius:2px; background:{'#F5A623' if step>=1 else 'rgba(255,255,255,0.1)'}; box-shadow:0 0 10px {'rgba(245,166,35,0.5)' if step>=1 else 'transparent'};"></div>
        <div style="flex:1; height:4px; border-radius:2px; background:{'#F5A623' if step>=2 else 'rgba(255,255,255,0.1)'}; box-shadow:0 0 10px {'rgba(245,166,35,0.5)' if step>=2 else 'transparent'};"></div>
        <div style="flex:1; height:4px; border-radius:2px; background:{'#F5A623' if step>=3 else 'rgba(255,255,255,0.1)'}; box-shadow:0 0 10px {'rgba(245,166,35,0.5)' if step>=3 else 'transparent'};"></div>
    </div>
    <div style="display:flex;gap:1rem;margin-bottom:2rem;font-size:0.8rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em;">
        <span style="color:{'#F5A623' if step>=1 else '#71717a'};flex:1;">① Upload</span>
        <span style="color:{'#F5A623' if step>=2 else '#71717a'};flex:1;text-align:center;">② Extraction</span>
        <span style="color:{'#F5A623' if step>=3 else '#71717a'};flex:1;text-align:right;">③ Review</span>
    </div>
    """, unsafe_allow_html=True)

    # File uploader
    uploaded = st.file_uploader(
        "Drop receipt image here...",
        type=["png", "jpg", "jpeg"],
        key="receipt_uploader",
    )

    if uploaded is not None:
        if st.session_state.get("_scan_file_name") != uploaded.name:
            st.session_state["_scan_file_name"] = uploaded.name
            for k in ("_scan_ocr", "_scan_parsed", "_scan_validated"):
                st.session_state.pop(k, None)

    if uploaded is not None and "_scan_ocr" not in st.session_state:
        col_img, col_info = st.columns([1, 2])
        with col_img:
            st.image(uploaded, use_container_width=True, caption="Target Document")
        with col_info:
            with st.spinner("Step 1/2 — Initiating OCR..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                ocr_result = receipt_scanner.extract_text_from_image(tmp_path)
                st.session_state["_scan_ocr"] = ocr_result

            if "error" in ocr_result:
                st.error(f"OCR failed: {ocr_result['error']}")
                return

            with st.spinner("Step 2/2 — Deep parsing with AI..."):
                parsed = receipt_scanner.parse_receipt_text(ocr_result["raw_text"])
                st.session_state["_scan_parsed"] = parsed

            if "error" in parsed:
                st.error(f"AI parsing failed: {parsed['error']}")
                return

            validated = validation.validate_receipt(parsed)
            st.session_state["_scan_validated"] = validated
            st.rerun()

    # Show image preview if scan already done
    if "_scan_validated" in st.session_state and uploaded is not None:
        c_img, c_form = st.columns([1, 2])
        with c_img:
            st.image(uploaded, use_container_width=True, caption="Processed Document")

            # Confidence badge
            data = st.session_state["_scan_validated"].get("data", {})
            conf = data.get("confidence", "low")
            conf_colors = {"high":"#10b981","medium":"#F5A623","low":"#ef4444"}
            st.markdown(f"""
            <div style="text-align:center;margin-top:1rem;">
                <span style="border:1px solid {conf_colors.get(conf,'#71717a')};
                             color:{conf_colors.get(conf,'#a1a1aa')};padding:6px 16px;border-radius:4px;
                             font-size:0.8rem;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;">
                    AI Confidence: {conf}
                </span>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Raw OCR Data"):
                st.code(st.session_state["_scan_ocr"].get("raw_text",""), language=None)

        with c_form:
            st.markdown("""
            <div class="fade-in" style="color:#00E5FF;font-size:0.95rem;font-weight:700;margin-bottom:1.5rem; letter-spacing:0.05em; text-transform:uppercase;">
                ✦ Extraction Complete — Verify Details
            </div>
            """, unsafe_allow_html=True)

            validated = st.session_state["_scan_validated"]
            data = validated.get("data", {})

            with st.form("scan_form"):
                type_opts = ["fuel", "maintenance", "insurance", "unknown"]
                rec_type = st.selectbox("Record Type", type_opts,
                    index=type_opts.index(data.get("record_type","fuel")))
                rec_date = st.date_input("Date", value=date.today())
                amount = st.number_input("Amount (PKR)", min_value=0.0,
                    value=float(data.get("amount_pkr") or 0), step=100.0)
                col_l, col_o = st.columns(2)
                with col_l:
                    liters = st.number_input("Liters", min_value=0.0,
                        value=float(data.get("liters") or 0), step=0.5)
                with col_o:
                    odo = st.number_input("Odometer (km)", min_value=0,
                        value=int(data.get("odometer_km") or 0), step=10)
                vendor = st.text_input("Vendor", value=data.get("vendor_name") or "")
                desc   = st.text_area("Description", value=data.get("description") or "", height=80)

                if st.form_submit_button("💾 Commit Record", use_container_width=True):
                    try:
                        db.add_record(
                            vehicle_id=vid,
                            record_type=rec_type,
                            date=rec_date.isoformat(),
                            amount_pkr=amount if amount > 0 else None,
                            liters=liters if liters > 0 else None,
                            odometer_km=odo if odo > 0 else None,
                            vendor_name=vendor or None,
                            description=desc or None,
                            source="ai_scan",
                            confidence=data.get("confidence"),
                            raw_ocr_json=json.dumps(
                                st.session_state.get("_scan_parsed", {})),
                        )
                        st.success("Record committed successfully!")
                        for k in ("_scan_validated","_scan_parsed","_scan_ocr","_scan_file_name"):
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Commit failed: {exc}")


# ============================================================
# PAGE: ADD EXPENSE
# ============================================================
def page_add_expense():
    _page_hero("Add Expense", "Manually inject service and fueling data", "➕")

    vid = require_vehicle()
    if not vid:
        return

    st.markdown("<div class='fade-in' style='max-width:700px;'>", unsafe_allow_html=True)
    with st.form("expense_form"):
        type_col, date_col = st.columns(2)
        with type_col:
            rec_type = st.selectbox("Expense Class", ["fuel", "maintenance", "insurance"])
        with date_col:
            rec_date = st.date_input("Date", value=date.today())

        amount = st.number_input("Amount (PKR)", min_value=0.0, step=100.0,
                                 placeholder="0.00")

        if rec_type == "fuel":
            lc, oc = st.columns(2)
            with lc:
                liters = st.number_input("Liters", min_value=0.0, step=0.5)
            with oc:
                odo = st.number_input("Odometer (km)", min_value=0, step=10)
        elif rec_type == "maintenance":
            liters = None
            odo = st.number_input("Odometer (km)", min_value=0, step=10)
        else:
            liters = None
            odo = None

        vendor = st.text_input("Vendor / Station", placeholder="e.g. PSO High-Octane")
        desc   = st.text_area("Remarks", placeholder="Additional telemetry...", height=80)

        if st.form_submit_button("💾 Inject Record", use_container_width=True):
            if amount <= 0:
                st.error("Amount magnitude must be greater than zero.")
            else:
                db.add_record(
                    vehicle_id=vid,
                    record_type=rec_type,
                    date=rec_date.isoformat(),
                    amount_pkr=amount,
                    liters=liters if rec_type == "fuel" else None,
                    odometer_km=odo if rec_type in ("fuel","maintenance") else None,
                    vendor_name=vendor or None,
                    description=desc or None,
                    source="manual",
                )
                st.success(f"✅ Record injected: {rec_type.upper()} | {fmt_pkr(amount)}")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PAGE: VEHICLE LOGBOOK
# ============================================================
def page_logbook():
    _page_hero("Logbook Archive", "Comprehensive cinematic ledger of all vehicle transactions", "📖")

    vid = require_vehicle()
    if not vid:
        return

    # Controls
    sc, fc = st.columns([3, 1])
    with sc:
        search = st.text_input("🔍  Search Archive", key="log_search",
                               label_visibility="collapsed",
                               placeholder="🔍  Search logs by vendor or metadata...")
    with fc:
        filter_type = st.selectbox("Class Filter", ["All", "fuel", "maintenance", "insurance"],
                                   key="log_filter", label_visibility="collapsed")

    records = db.get_records(
        vid, record_type=None if filter_type == "All" else filter_type
    )

    if search:
        sl = search.lower()
        records = [r for r in records
                   if sl in (r.get("description") or "").lower()
                   or sl in (r.get("vendor_name") or "").lower()]

    if not records:
        _empty_state("📭", "Archive Empty",
                     "Inject records manually or run a receipt scan to populate data.")
        return

    st.markdown(f"""
    <div style="color:#71717a;font-size:0.85rem;margin-bottom:1.5rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
        Displaying <strong style="color:#F5A623">{len(records)}</strong> record{"s" if len(records)!=1 else ""}
    </div>
    """, unsafe_allow_html=True)

    for rec in records:
        rtype = rec.get("record_type","unknown")
        is_editing = st.session_state.get("editing_id") == rec["id"]

        # Build detail chips
        chips = []
        if rec.get("amount_pkr"):
            chips.append(f'<span style="color:#ffffff;font-weight:700;font-size:1.05rem;">{fmt_pkr(rec["amount_pkr"])}</span>')
        if rec.get("odometer_km"):
            chips.append(f'<span style="color:#a1a1aa">{rec["odometer_km"]:,} km</span>')
        if rec.get("liters"):
            chips.append(f'<span style="color:#a1a1aa">{rec["liters"]:.1f} L</span>')
        if rec.get("vendor_name"):
            chips.append(f'<span style="color:#a1a1aa">{_esc(rec["vendor_name"])}</span>')
        chips_html = ' <span style="color:#3f3f46;margin:0 8px">|</span> '.join(chips)

        with st.container():
            st.markdown(f"""
            <div class="ss-card ss-card-accent-top fade-in" style="margin-bottom:0.5rem; padding: 1.2rem 1.8rem;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.8rem;">
                    <div style="display:flex;align-items:center;gap:1rem;">
                        {_badge(rtype)}
                        <span style="color:#71717a;font-size:0.85rem;font-weight:600;letter-spacing:0.05em;">DATE: {_esc(rec.get('date','—'))}</span>
                    </div>
                </div>
                <div style="font-size:0.95rem; margin-bottom:0.5rem;">{chips_html}</div>
                {"<div style='color:#71717a;font-size:0.85rem;font-style:italic;'>" + _esc(rec['description']) + "</div>" if rec.get('description') else ""}
            </div>
            """, unsafe_allow_html=True)

            btn_c1, btn_c2, spacer = st.columns([1, 1, 6])
            with btn_c1:
                st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
                if st.button("✏️ Modify", key=f"edit_{rec['id']}", use_container_width=True):
                    st.session_state["editing_id"] = rec["id"]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with btn_c2:
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button("✕ Purge", key=f"del_{rec['id']}", use_container_width=True):
                    db.delete_record(rec["id"])
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            if is_editing:
                with st.form(f"edit_form_{rec['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        new_amount = st.number_input("Amount (PKR)",
                            value=float(rec.get("amount_pkr") or 0), step=100.0)
                        new_vendor = st.text_input("Vendor",
                            value=rec.get("vendor_name") or "")
                    with ec2:
                        new_desc = st.text_area("Remarks",
                            value=rec.get("description") or "", height=80)

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("💾 Commit Changes", use_container_width=True):
                            db.update_record(
                                rec["id"],
                                amount_pkr=new_amount if new_amount > 0 else None,
                                description=new_desc or None,
                                vendor_name=new_vendor or None,
                            )
                            st.success("Record updated!")
                            st.session_state.pop("editing_id", None)
                            st.rerun()
                    with sc2:
                        if st.form_submit_button("✕ Abort", use_container_width=True):
                            st.session_state.pop("editing_id", None)
                            st.rerun()


# ============================================================
# PAGE: MAINTENANCE
# ============================================================
def page_maintenance():
    _page_hero("Maintenance", "Service telemetry, AI diagnostics, and archive exports", "🔧")

    vid = require_vehicle()
    if not vid:
        return

    import plotly.graph_objects as go

    # ── Service Status Cards ────────────────────────────────
    _section("SERVICE TELEMETRY")
    status = maintenance.check_due_maintenance(vid)

    status_meta = {
        "overdue":  ("🔴", "#ef4444", "rgba(220,38,38,0.05)",  "rgba(220,38,38,0.4)"),
        "due_soon": ("🟡", "#F5A623", "rgba(245,166,35,0.05)", "rgba(245,166,35,0.4)"),
        "not_due":  ("🟢", "#10b981", "rgba(16,185,129,0.05)", "rgba(16,185,129,0.2)"),
        "unknown":  ("⚪", "#71717a", "rgba(113,113,122,0.05)","rgba(113,113,122,0.2)"),
    }
    labels = {"oil_change":"Oil Change","air_filter":"Air Filter",
              "brake_check":"Brake Check","tire_rotation":"Tire Rotation"}

    if status:
        cols = st.columns(len(status))
        for idx, svc in enumerate(status):
            s = svc["status"]
            icon, color, bg, border = status_meta.get(s, status_meta["unknown"])
            name = labels.get(svc["type"], svc["type"].replace("_"," ").title())
            since = f'{svc["km_since_last"]:,} km' if svc.get("km_since_last") is not None else "—"
            interval = f'{svc["interval_km"]:,} km'
            overdue_txt = ""
            if svc.get("overdue_by") is not None:
                overdue_txt = f'<div style="color:#ef4444;font-size:0.8rem;margin-top:0.8rem;font-weight:700;">⬆ {svc["overdue_by"]:,} km overdue</div>'
            with cols[idx]:
                st.markdown(f"""
                <div class="fade-in" style="background:{bg};border:1px solid {border};border-radius:12px;
                            padding:2rem 1.5rem;text-align:center;height:100%; box-shadow:0 8px 25px rgba(0,0,0,0.4);">
                    <div style="font-size:2.2rem;margin-bottom:0.8rem;">{icon}</div>
                    <div style="color:#ffffff;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem;">{_esc(name)}</div>
                    <div style="color:{color};font-size:0.75rem;font-weight:800;
                                text-transform:uppercase;letter-spacing:0.1em;margin:0.8rem 0;">{s.replace('_',' ')}</div>
                    <div style="color:#a1a1aa;font-size:0.85rem;margin-bottom:0.3rem;">Last: <span style="color:#e4e4e7">{since}</span></div>
                    <div style="color:#71717a;font-size:0.8rem;">Interval: {interval}</div>
                    {overdue_txt}
                </div>
                """, unsafe_allow_html=True)
    else:
        _empty_state("🔧", "No telemetry data", "Inject maintenance records to track service intervals.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Advice ───────────────────────────────────────────
    _section("AI DIAGNOSTICS")
    if st.button("🤖 Run Diagnostics", key="ai_advice"):
        with st.spinner("Analyzing maintenance logs..."):
            advice = maintenance.get_ai_maintenance_advice(vid)
            st.session_state["last_advice"] = advice

    if "last_advice" in st.session_state:
        st.markdown(f"""
        <div class="insight-box fade-in" style="margin-top:1rem;">
            {_esc(st.session_state["last_advice"])}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PDF Report ──────────────────────────────────────────
    _section("ARCHIVE EXPORT")
    st.markdown("""
    <div class="ss-card fade-in" style="display:flex;align-items:center;gap:1.5rem;padding:1.5rem 2rem;">
        <div style="font-size:2.5rem;">📄</div>
        <div>
            <div style="color:#ffffff;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.2rem;margin-bottom:0.2rem;">Generate Master Logbook Report</div>
            <div style="color:#a1a1aa;font-size:0.9rem;">
                Compiles vehicle metadata, financial summaries, and complete raw transaction logs into a PDF.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("📥 Render PDF Export", key="gen_pdf"):
        with st.spinner("Rendering document..."):
            try:
                pdf_path = pdf_report.generate_logbook_pdf(vid, "logbook_report.pdf")
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "⬇ Download Payload",
                        f,
                        file_name="logbook_report.pdf",
                        mime="application/pdf",
                        use_container_width=False,
                    )
            except Exception as exc:
                st.error(f"Render failed: {exc}")


# ============================================================
# PAGE: ASK SAFARSYNC
# ============================================================
def page_ask():
    _page_hero("Ask SafarSync", "Interrogate your vehicle's metadata via AI", "💬")

    vid = require_vehicle()
    if not vid:
        return

    # Chat history display
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if st.session_state["chat_history"]:
        for entry in st.session_state["chat_history"]:
            # User bubble
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;margin-bottom:1rem;">
                <div style="background:rgba(245,166,35,0.1);border:1px solid rgba(245,166,35,0.3);
                            border-radius:12px 0 12px 12px;padding:1rem 1.5rem;max-width:70%;
                            color:#fafafa;font-size:0.95rem;box-shadow:0 4px 15px rgba(0,0,0,0.3);">
                    {_esc(entry['question'])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            # AI bubble
            st.markdown(f"""
            <div class="chat-bubble fade-in" style="max-width:80%;margin-bottom:1.5rem;">
                <div style="font-size:0.75rem;color:#F5A623;font-weight:800;
                            text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;">
                    ✦ SafarSync AI Core
                </div>
                {_esc(entry['answer'])}
            </div>
            """, unsafe_allow_html=True)

        col_clr, _ = st.columns([1, 5])
        with col_clr:
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("Purge Chat Logs", key="clear_chat"):
                st.session_state["chat_history"] = []
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Input
    question = st.text_input("",
        placeholder="e.g. Total financial allocation for fuel last month?",
        key="ask_input", label_visibility="collapsed")

    if st.button("Transmit Query  ➤", key="ask_btn") and question.strip():
        metrics      = analytics.get_summary_metrics(vid)
        maint_status = maintenance.check_due_maintenance(vid)
        anomalies_list = anomaly.find_anomalies(vid)

        facts = [f"Total spending: {fmt_pkr(metrics['total_spend'])}"]
        if metrics["fuel_spend"] is not None:
            facts.append(f"Fuel spending: {fmt_pkr(metrics['fuel_spend'])}")
        if metrics["maintenance_spend"] is not None:
            facts.append(f"Maintenance spending: {fmt_pkr(metrics['maintenance_spend'])}")
        if metrics["insurance_spend"] is not None:
            facts.append(f"Insurance spending: {fmt_pkr(metrics['insurance_spend'])}")
        if metrics["total_distance"] is not None:
            facts.append(f"Total distance tracked: {metrics['total_distance']:,} km")
        if metrics["average_fuel_efficiency"] is not None:
            facts.append(f"Average fuel efficiency: {metrics['average_fuel_efficiency']:.1f} km/L")
        if metrics["cost_per_km"] is not None:
            facts.append(f"Cost per km: PKR {metrics['cost_per_km']:.2f}")

        overdue   = [s for s in maint_status if s["status"] == "overdue"]
        due_soon  = [s for s in maint_status if s["status"] == "due_soon"]
        if overdue:
            facts.append(f"Overdue services: {', '.join(s['type'].replace('_',' ') for s in overdue)}")
        if due_soon:
            facts.append(f"Services due soon: {', '.join(s['type'].replace('_',' ') for s in due_soon)}")
        if not overdue and not due_soon:
            facts.append("All maintenance is up to date.")
        if anomalies_list:
            for a in anomalies_list[:5]:
                facts.append(f"Anomaly [{a['severity'].upper()}]: {a['message']}")
        else:
            facts.append("No spending anomalies detected.")

        prompt = (
            "You are SafarSync AI, a friendly and knowledgeable vehicle expense advisor.\n"
            "Below are VERIFIED facts calculated by our system — use only these, "
            "do NOT invent numbers.\n\n"
            + "\n".join(facts)
            + f"\n\nUser question: {question.strip()}\n\n"
            "Answer clearly and concisely in 2-4 sentences."
        )

        with st.spinner("Processing telemetry..."):
            try:
                answer = ask_text(prompt, model=_config.QWEN_PLUS_CHARACTER, max_tokens=300)
                st.session_state["chat_history"].append({
                    "question": question.strip(),
                    "answer": answer,
                })
                st.rerun()
            except PermissionError:
                st.error("Authentication failed. Check your API key.")
            except ConnectionError:
                st.error("Cannot reach the AI core. Check your connection.")
            except TimeoutError:
                st.error("Request timed out. Please try again.")
            except RuntimeError as exc:
                st.error(f"Core failure: {exc}")
    elif not st.session_state["chat_history"]:
        # Suggested questions
        _section("RECOMMENDED QUERIES")
        suggestions = [
            "What is my overall fuel expenditure this year?",
            "Detail my average fuel efficiency.",
            "Are there any maintenance services overdue?",
            "What is the calculated cost per kilometre?",
        ]
        s_cols = st.columns(2)
        for i, sug in enumerate(suggestions):
            with s_cols[i % 2]:
                st.markdown(f"""
                <div class="fade-in" style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);
                            border-radius:8px;padding:1rem 1.5rem;margin-bottom:0.8rem;
                            color:#a1a1aa;font-size:0.9rem;cursor:pointer; transition:all 0.3s;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.2);"
                     onmouseover="this.style.borderColor='rgba(245,166,35,0.5)'; this.style.color='#f4f4f5';" 
                     onmouseout="this.style.borderColor='rgba(255,255,255,0.08)'; this.style.color='#a1a1aa';">
                    💬 &nbsp;&nbsp;{_esc(sug)}
                </div>
                """, unsafe_allow_html=True)


# ============================================================
# PAGE: MANAGE VEHICLES
# ============================================================
def page_manage():
    _page_hero("Vehicle Registry", "Register new assets and configure active tracking", "🚗")

    # ── Add Vehicle Form ────────────────────────────────────
    _section("REGISTER NEW ASSET")
    st.markdown("<div class='fade-in' style='max-width:600px;'>", unsafe_allow_html=True)
    with st.form("add_vehicle_form"):
        name = st.text_input("Asset Designation", placeholder="e.g. Primary Commuter")
        reg  = st.text_input("Registration Plate", placeholder="e.g. ISB-9876")
        if st.form_submit_button("➕ Register Asset", use_container_width=True):
            if not name.strip():
                st.error("Asset designation is required.")
            else:
                new_id = db.add_vehicle(name.strip(), reg.strip())
                st.success(f"Asset '{name}' registered successfully.")
                st.session_state["vehicle_id"] = new_id
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Vehicle List ────────────────────────────────────────
    vehicles = db.get_vehicles()
    if not vehicles:
        _empty_state("🚗", "No Assets Registered", "Register your first vehicle above.")
        return

    _section(f"ACTIVE REGISTRY  ({len(vehicles)})")
    current_id = st.session_state.get("vehicle_id")

    for v in vehicles:
        is_active = current_id == v["id"]
        
        # We manually build the card for high contrast
        bg = "linear-gradient(145deg, rgba(245,166,35,0.1), rgba(0,0,0,0.8))" if is_active else "rgba(15,15,15,0.6)"
        border = "rgba(245,166,35,0.5)" if is_active else "rgba(255,255,255,0.08)"
        shadow = "0 10px 30px rgba(0,0,0,0.5)" if is_active else "none"

        st.markdown(f"""
        <div class="fade-in" style="background:{bg}; border:1px solid {border}; border-radius:12px;
                    padding:1.5rem 2rem; margin-bottom:1rem; display:flex; align-items:center; gap:1.5rem;
                    box-shadow:{shadow}; transition:all 0.3s;">
            <div style="font-size:2.5rem; flex-shrink:0;">{"🚘" if is_active else "🚗"}</div>
            <div style="flex:1;">
                <div style="color:#ffffff; font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.2rem; margin-bottom:0.2rem;">{_esc(v['name'])}</div>
                <div style="color:#a1a1aa; font-size:0.85rem; letter-spacing:0.05em;">REG: <span style="color:#e4e4e7">{_esc(v.get('registration_number', '')) or '—'}</span></div>
            </div>
            {"<span style='background:#F5A623;color:#050505;padding:6px 16px;border-radius:4px;font-size:0.8rem;font-weight:900;letter-spacing:0.1em;box-shadow:0 0 15px rgba(245,166,35,0.4);'>ACTIVE</span>" if is_active else ""}
        </div>
        """, unsafe_allow_html=True)

        if not is_active:
            col_sel, _ = st.columns([1, 5])
            with col_sel:
                st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
                if st.button(f"Initialize", key=f"sel_{v['id']}", use_container_width=True):
                    st.session_state["vehicle_id"] = v["id"]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# MAIN  — wires everything together
# ============================================================
def main():
    st.set_page_config(
        page_title="SafarSync AI",
        page_icon="🚘",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject design system CSS
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Config error screen ─────────────────────────────────
    if not _modules_loaded:
        st.markdown("""
        <div class="fade-in" style="max-width:600px;margin:6rem auto;text-align:center;">
            <div style="font-size:4rem;margin-bottom:1.5rem;text-shadow:0 0 30px rgba(220,38,38,0.6);">⚙️</div>
            <h2 style="color:#ffffff;font-family:'Space Grotesk',sans-serif;">Configuration Required</h2>
            <p style="color:#a1a1aa;">One or more critical core secrets are missing.</p>
        </div>
        """, unsafe_allow_html=True)
        st.code(_config_error)
        st.info("Inject the missing parameters into your `.env` file or Streamlit deployment secrets.")
        return

    # ── Startup ─────────────────────────────────────────────
    db.init_db()
    vehicles = db.get_vehicles()
    if not vehicles:
        demo_data.seed_demo_data()
        vehicles = db.get_vehicles()

    # ── Sidebar ─────────────────────────────────────────────
    with st.sidebar:
        # High-Contrast SVG Custom Logo injection
        st.markdown("""
        <div class="sidebar-logo fade-in">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-bottom: 5px; filter: drop-shadow(0 0 12px rgba(245,166,35,0.7));">
                <path d="M4 16L4 10C4 8.89543 4.89543 8 6 8H18C19.1046 8 20 8.89543 20 10V16M4 16L2.59325 18.1098C2.21323 18.6798 2.62254 19.5 3.30806 19.5H20.6919C21.3775 19.5 21.7868 18.6798 21.4067 18.1098L20 16M4 16H20M8 12H16M7 16V17.5M17 16V17.5" stroke="url(#goldGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <defs>
                    <linearGradient id="goldGradient" x1="2" y1="8" x2="22" y2="19.5" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#F5A623"/>
                        <stop offset="1" stop-color="#F8E71C"/>
                    </linearGradient>
                </defs>
            </svg>
            <div class="logo-mark">SafarSync <span style="color:#F5A623;">AI</span></div>
            <div class="logo-sub">Intelligent Logbook</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Vehicle selector
        st.markdown('<div style="font-size:0.75rem;font-weight:800;color:#71717a;'
                    'text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.8rem;">'
                    'ACTIVE ASSET</div>', unsafe_allow_html=True)

        if vehicles:
            options = {v["id"]: v["name"] for v in vehicles}
            current_id = st.session_state.get("vehicle_id")
            if current_id not in options:
                current_id = list(options.keys())[0]
                st.session_state["vehicle_id"] = current_id

            selected = st.selectbox(
                "vehicle",
                options=list(options.keys()),
                format_func=lambda x: options[x],
                index=list(options.keys()).index(current_id),
                key="vehicle_selector",
                label_visibility="collapsed",
            )
            if selected != st.session_state.get("vehicle_id"):
                st.session_state["vehicle_id"] = selected
                st.rerun()

            current_v = next((v for v in vehicles if v["id"] == current_id), None)
            if current_v:
                reg = current_v.get("registration_number") or "—"
                st.markdown(f"""
                <div class="sidebar-vehicle-pill fade-in">
                    📋 &nbsp;{_esc(reg)}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No assets located.")

        # Quick stats in sidebar
        vid = st.session_state.get("vehicle_id")
        if vid:
            st.divider()
            st.markdown('<div style="font-size:0.75rem;font-weight:800;color:#71717a;'
                        'text-transform:uppercase;letter-spacing:0.15em;margin-bottom:1rem;">'
                        'TELEMETRY SNAPSHOT</div>', unsafe_allow_html=True)
            try:
                m = analytics.get_summary_metrics(vid)
                st.markdown(f"""
                <div class="fade-in" style="font-size:0.85rem;color:#a1a1aa;line-height:2.2;">
                    <div style="display:flex; justify-content:space-between;"><span>💰 Total:</span> <strong style="color:#ffffff">{fmt_pkr(m['total_spend'])}</strong></div>
                    <div style="display:flex; justify-content:space-between;"><span>⛽ Efficiency:</span> <strong style="color:#00E5FF">{f"{m['average_fuel_efficiency']:.1f} km/L" if m['average_fuel_efficiency'] else '—'}</strong></div>
                    <div style="display:flex; justify-content:space-between;"><span>📏 Distance:</span> <strong style="color:#ffffff">{m['total_distance']:,} km</strong></div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                pass

        st.divider()
        st.markdown('<div style="font-size:0.7rem;color:#52525b;text-align:center;'
                    'padding-bottom:1rem;font-weight:600;letter-spacing:0.05em;">SafarSync AI Core · 🇵🇰</div>',
                    unsafe_allow_html=True)

    # ── Navigation ───────────────────────────────────────────
    pages = [
        st.Page(page_dashboard,    title="Dashboard",        icon=":material/space_dashboard:"),
        st.Page(page_scan_receipt, title="Scan Receipt",     icon=":material/document_scanner:"),
        st.Page(page_add_expense,  title="Inject Data",      icon=":material/add_circle:"),
        st.Page(page_logbook,      title="Archive Logs",     icon=":material/menu_book:"),
        st.Page(page_maintenance,  title="Maintenance",      icon=":material/build_circle:"),
        st.Page(page_ask,          title="Ask AI Core",      icon=":material/smart_toy:"),
        st.Page(page_manage,       title="Asset Registry",   icon=":material/directions_car:"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()