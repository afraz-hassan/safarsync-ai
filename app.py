"""
app.py — SafarSync AI  |  Modern Streamlit interface.

Full redesign: dark-navy design system, animated metric cards, glassmorphism
panels, gradient accents, and polished Plotly charts throughout.
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
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


# ============================================================
# DESIGN SYSTEM — inject once from main()
# ============================================================
_CSS = """
<style>
/* ── Google Font ─────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global reset ────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── App background ──────────────────────────── */
.stApp {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 50%, #0a1628 100%) !important;
    min-height: 100vh;
}

/* ── Sidebar ─────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #0a1628 100%) !important;
    border-right: 1px solid rgba(0,212,255,0.15) !important;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

/* ── Navigation ──────────────────────────────── */
[data-testid="stSidebarNav"] li span {
    color: #94a3b8 !important;
    font-weight: 500 !important;
    transition: color 0.2s;
}
[data-testid="stSidebarNav"] li:hover span,
[data-testid="stSidebarNav"] li[aria-selected="true"] span {
    color: #00d4ff !important;
}
[data-testid="stSidebarNav"] li[aria-selected="true"] {
    background: rgba(0,212,255,0.1) !important;
    border-radius: 8px;
    border-left: 3px solid #00d4ff !important;
}

/* ── Main content area ───────────────────────── */
.main .block-container {
    padding: 1.5rem 2.5rem 2rem !important;
    max-width: 1400px !important;
}

/* ── Page titles ─────────────────────────────── */
h1 { color: #f1f5f9 !important; font-weight: 800 !important; letter-spacing: -0.5px; }
h2 { color: #e2e8f0 !important; font-weight: 700 !important; }
h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
p, li, span, label { color: #94a3b8 !important; }

/* ── Metric cards ────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%) !important;
    border: 1px solid rgba(0,212,255,0.18) !important;
    border-radius: 16px !important;
    padding: 1.2rem 1.4rem !important;
    backdrop-filter: blur(12px) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
    position: relative;
    overflow: hidden;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 32px rgba(0,212,255,0.18) !important;
}
[data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00d4ff, #7c3aed, #00d4ff);
    background-size: 200% 100%;
    animation: shimmer 3s linear infinite;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.78rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.6rem !important; font-weight: 800 !important; }
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

/* ── Buttons ─────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%) !important;
    color: #0a0f1e !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(0,212,255,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0,212,255,0.45) !important;
    background: linear-gradient(135deg, #33ddff 0%, #00b3e6 100%) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Danger / delete button */
.danger-btn .stButton > button {
    background: linear-gradient(135deg, #ef4444, #dc2626) !important;
    color: #fff !important;
    box-shadow: 0 4px 15px rgba(239,68,68,0.25) !important;
}
.danger-btn .stButton > button:hover {
    box-shadow: 0 8px 25px rgba(239,68,68,0.45) !important;
}

/* Ghost / secondary button */
.ghost-btn .stButton > button {
    background: transparent !important;
    color: #00d4ff !important;
    border: 1px solid rgba(0,212,255,0.4) !important;
    box-shadow: none !important;
}
.ghost-btn .stButton > button:hover {
    background: rgba(0,212,255,0.08) !important;
    box-shadow: 0 4px 15px rgba(0,212,255,0.15) !important;
}

/* ── Forms & inputs ──────────────────────────── */
.stForm {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(0,212,255,0.12) !important;
    border-radius: 20px !important;
    padding: 1.8rem !important;
    backdrop-filter: blur(8px);
}
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 3px rgba(0,212,255,0.15) !important;
}
label { color: #94a3b8 !important; font-weight: 500 !important; font-size: 0.85rem !important; }

/* Form submit button */
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.35) !important;
    transition: all 0.2s;
}
.stFormSubmitButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(124,58,237,0.55) !important;
}

/* ── Alerts & banners ────────────────────────── */
.stAlert { border-radius: 12px !important; border-left-width: 4px !important; }
.stSuccess { background: rgba(16,185,129,0.1) !important; border-left-color: #10b981 !important; color: #6ee7b7 !important; }
.stError   { background: rgba(239,68,68,0.1)  !important; border-left-color: #ef4444 !important; color: #fca5a5 !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border-left-color: #f59e0b !important; color: #fcd34d !important; }
.stInfo    { background: rgba(59,130,246,0.1) !important; border-left-color: #3b82f6 !important; color: #93c5fd !important; }

/* ── Divider ─────────────────────────────────── */
hr { border-color: rgba(0,212,255,0.1) !important; margin: 1.5rem 0 !important; }

/* ── Expander ────────────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(0,212,255,0.12) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary { color: #94a3b8 !important; }

/* ── Dataframe ───────────────────────────────── */
.stDataFrame { border-radius: 12px !important; overflow: hidden; }

/* ── File uploader ───────────────────────────── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.03) !important;
    border: 2px dashed rgba(0,212,255,0.3) !important;
    border-radius: 16px !important;
    transition: border-color 0.2s, background 0.2s;
}
[data-testid="stFileUploader"]:hover {
    background: rgba(0,212,255,0.04) !important;
    border-color: rgba(0,212,255,0.6) !important;
}

/* ── Spinner ─────────────────────────────────── */
.stSpinner > div { border-top-color: #00d4ff !important; }

/* ── Scrollbar ───────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,212,255,0.6); }

/* ── Custom card utility ─────────────────────── */
.ss-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 18px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    transition: transform 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
}
.ss-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,212,255,0.12);
}
.ss-card-accent-top::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #00d4ff, #7c3aed);
    border-radius: 18px 18px 0 0;
}

/* Record type badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-fuel        { background: rgba(0,212,255,0.15); color: #00d4ff !important; border: 1px solid rgba(0,212,255,0.3); }
.badge-maintenance { background: rgba(245,158,11,0.15); color: #f59e0b !important; border: 1px solid rgba(245,158,11,0.3); }
.badge-insurance   { background: rgba(124,58,237,0.15); color: #a78bfa !important; border: 1px solid rgba(124,58,237,0.3); }
.badge-unknown     { background: rgba(100,116,139,0.15); color: #94a3b8 !important; border: 1px solid rgba(100,116,139,0.3); }

/* Anomaly severity pills */
.pill-high    { background: rgba(239,68,68,0.15);   color: #f87171 !important; border: 1px solid rgba(239,68,68,0.35);   padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
.pill-warning { background: rgba(245,158,11,0.15);  color: #fbbf24 !important; border: 1px solid rgba(245,158,11,0.35);  padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
.pill-info    { background: rgba(59,130,246,0.15);  color: #60a5fa !important; border: 1px solid rgba(59,130,246,0.35);  padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }

/* Insight box */
.insight-box {
    background: linear-gradient(135deg, rgba(0,212,255,0.06), rgba(124,58,237,0.06));
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    color: #e2e8f0 !important;
    font-size: 0.95rem;
    line-height: 1.7;
    position: relative;
}
.insight-box::before {
    content: "✦";
    position: absolute;
    top: -10px; left: 18px;
    background: #0a0f1e;
    padding: 0 6px;
    color: #00d4ff;
    font-size: 0.9rem;
}

/* Chat bubble */
.chat-bubble {
    background: linear-gradient(135deg, rgba(124,58,237,0.12), rgba(0,212,255,0.08));
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 0 16px 16px 16px;
    padding: 1.2rem 1.5rem;
    margin-top: 1rem;
    color: #e2e8f0 !important;
    font-size: 0.95rem;
    line-height: 1.7;
}

/* Maintenance status rows */
.maint-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: 0.6rem;
    transition: background 0.2s;
}
.maint-row:hover { background: rgba(255,255,255,0.05); }

/* Shimmer animation */
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position:  200% 0; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,212,255,0); }
    50%       { box-shadow: 0 0 20px 4px rgba(0,212,255,0.18); }
}
.fade-in { animation: fadeInUp 0.4s ease forwards; }
.pulse   { animation: pulse-glow 2.5s ease-in-out infinite; }

/* Logo area in sidebar */
.sidebar-logo {
    text-align: center;
    padding: 1rem 0 0.5rem;
}
.sidebar-logo .logo-mark {
    font-size: 2.2rem;
    background: linear-gradient(135deg, #00d4ff, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 900;
    letter-spacing: -1px;
    display: block;
}
.sidebar-logo .logo-sub {
    font-size: 0.65rem !important;
    color: #475569 !important;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    font-weight: 600 !important;
}
.sidebar-vehicle-pill {
    background: rgba(0,212,255,0.08);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 10px;
    padding: 0.5rem 0.9rem;
    margin-top: 0.4rem;
    font-size: 0.78rem !important;
    color: #00d4ff !important;
}

/* Page hero header */
.page-hero {
    margin-bottom: 1.8rem;
}
.page-hero h1 {
    margin: 0 !important;
    font-size: 2rem !important;
    background: linear-gradient(90deg, #f1f5f9, #94a3b8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.page-hero p {
    margin: 0.3rem 0 0 !important;
    color: #475569 !important;
    font-size: 0.9rem !important;
}

/* Upload zone label */
.upload-label {
    color: #64748b !important;
    font-size: 0.82rem !important;
    text-align: center;
    margin-top: 0.3rem;
}

/* Vehicle cards on manage page */
.vehicle-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
    border: 1px solid rgba(0,212,255,0.12);
    border-radius: 14px;
    padding: 1rem 1.4rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.vehicle-card.active-vehicle {
    border-color: rgba(0,212,255,0.4);
    background: linear-gradient(135deg, rgba(0,212,255,0.06), rgba(0,212,255,0.02));
    box-shadow: 0 0 20px rgba(0,212,255,0.1);
}
.vc-icon {
    font-size: 1.8rem;
    flex-shrink: 0;
}
.vc-name { color: #f1f5f9 !important; font-weight: 700; font-size: 0.95rem; }
.vc-reg  { color: #475569 !important; font-size: 0.78rem; }

/* Step progress for scan receipt */
.step-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}
.step {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: rgba(255,255,255,0.1);
}
.step.active   { background: linear-gradient(90deg, #00d4ff, #7c3aed); }
.step.complete { background: #10b981; }

/* Section label */
.section-label {
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #475569 !important;
    margin-bottom: 0.6rem;
}

/* Plotly chart container */
.js-plotly-plot { border-radius: 12px; }

/* No data placeholder */
.empty-state {
    text-align: center;
    padding: 3rem 2rem;
    color: #334155 !important;
}
.empty-state .icon { font-size: 3rem; margin-bottom: 0.8rem; display: block; }
.empty-state p { color: #475569 !important; font-size: 0.9rem; }
</style>
"""

# ============================================================
# PLOTLY THEME  — dark, on-brand
# ============================================================
_PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8", size=12),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(color="#64748b"),
        title_font=dict(color="#64748b"),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.1)",
        tickfont=dict(color="#64748b"),
        title_font=dict(color="#64748b"),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
    ),
    margin=dict(l=10, r=10, t=30, b=10),
    height=340,
)
_COLOR_SEQ = ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b", "#ef4444", "#ec4899"]


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
        <div class="ss-card" style="text-align:center;padding:2.5rem;">
            <div style="font-size:2.5rem;margin-bottom:0.8rem;">🚗</div>
            <div style="color:#f1f5f9;font-weight:700;font-size:1.05rem;margin-bottom:0.4rem;">
                No Vehicle Selected
            </div>
            <div style="color:#475569;font-size:0.88rem;">
                Pick a vehicle from the sidebar to get started.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return None
    return vid


def _badge(rec_type: str) -> str:
    cls = f"badge-{rec_type}" if rec_type in ("fuel","maintenance","insurance") else "badge-unknown"
    return f'<span class="badge {cls}">{rec_type}</span>'


def _pill_severity(sev: str) -> str:
    return f'<span class="pill-{sev}">{"⬆" if sev=="high" else "▲" if sev=="warning" else "●"} {sev.upper()}</span>'


def _page_hero(title: str, subtitle: str, icon: str = "") -> None:
    st.markdown(f"""
    <div class="page-hero fade-in">
        <h1>{icon} {title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def _section(label: str) -> None:
    st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)


def _empty_state(icon: str, title: str, body: str) -> None:
    st.markdown(f"""
    <div class="empty-state">
        <span class="icon">{icon}</span>
        <div style="color:#94a3b8;font-weight:700;margin-bottom:0.4rem;">{title}</div>
        <p>{body}</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# PAGE: DASHBOARD
# ============================================================
def page_dashboard():
    _page_hero("Dashboard", "Your vehicle financial summary at a glance", "📊")

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
    st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
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
                line=dict(color="#00d4ff", width=2.5),
                marker=dict(size=7, color="#00d4ff",
                            line=dict(color="#0a0f1e", width=2)),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,0.07)",
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
        _section("MONTHLY SPENDING BY CATEGORY")
        monthly = analytics.monthly_spending_summary(vid)
        if monthly:
            df = pd.DataFrame(monthly)
            fig = px.bar(
                df, x="month", y="total_amount", color="record_type",
                barmode="stack",
                color_discrete_map={
                    "fuel": "#00d4ff",
                    "maintenance": "#f59e0b",
                    "insurance": "#7c3aed",
                },
            )
            fig.update_layout(
                **_PLOT_LAYOUT,
                xaxis_title="Month",
                yaxis_title="Amount (PKR)",
                bargap=0.25,
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
            bg  = {"high":"rgba(239,68,68,0.08)", "warning":"rgba(245,158,11,0.08)", "info":"rgba(59,130,246,0.08)"}.get(sev,"")
            bd  = {"high":"rgba(239,68,68,0.3)",  "warning":"rgba(245,158,11,0.3)",  "info":"rgba(59,130,246,0.3)"}.get(sev,"")
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bd};border-radius:12px;
                        padding:0.9rem 1.2rem;margin-bottom:0.5rem;display:flex;
                        align-items:center;gap:0.9rem;">
                {_pill_severity(sev)}
                <span style="color:#e2e8f0;font-size:0.88rem;">{a['message']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
                    border-radius:12px;padding:0.9rem 1.2rem;color:#6ee7b7;font-size:0.88rem;">
            ✅ &nbsp;No anomalies detected — everything looks normal.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Insight Card ────────────────────────────────────
    _section("AI INSIGHT")
    col_btn, col_spacer = st.columns([1, 4])
    with col_btn:
        if st.button("✦ Generate Insight", key="gen_insight"):
            with st.spinner("Analyzing your vehicle data..."):
                insight_text = insights.get_vehicle_insight(vid)
                st.session_state["last_insight"] = insight_text

    if "last_insight" in st.session_state:
        st.markdown(f"""
        <div class="insight-box fade-in">
            {st.session_state["last_insight"]}
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# PAGE: SCAN RECEIPT
# ============================================================
def page_scan_receipt():
    _page_hero("Scan Receipt", "Upload a receipt image — AI extracts and structures the data", "📷")

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
    <div class="step-bar">
        <div class="step {'complete' if step>1 else 'active'}"></div>
        <div class="step {'complete' if step>2 else ('active' if step>=2 else '')}"></div>
        <div class="step {'active' if step>=3 else ''}"></div>
    </div>
    <div style="display:flex;gap:1rem;margin-bottom:1.5rem;font-size:0.78rem;">
        <span style="color:{'#10b981' if step>1 else '#00d4ff'};flex:1;">① Upload</span>
        <span style="color:{'#10b981' if step>2 else ('#00d4ff' if step>=2 else '#334155')};flex:1;">② AI Extraction</span>
        <span style="color:{'#00d4ff' if step>=3 else '#334155'};flex:1;">③ Review & Save</span>
    </div>
    """, unsafe_allow_html=True)

    # File uploader
    uploaded = st.file_uploader(
        "Drop your receipt image here, or click to browse",
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
            st.image(uploaded, use_container_width=True,
                     caption="Uploaded receipt")
        with col_info:
            with st.spinner("Step 1/2 — Running OCR..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                ocr_result = receipt_scanner.extract_text_from_image(tmp_path)
                st.session_state["_scan_ocr"] = ocr_result

            if "error" in ocr_result:
                st.error(f"OCR failed: {ocr_result['error']}")
                return

            with st.spinner("Step 2/2 — Parsing with AI..."):
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
            st.image(uploaded, use_container_width=True, caption="Scanned receipt")

            # Confidence badge
            data = st.session_state["_scan_validated"].get("data", {})
            conf = data.get("confidence", "low")
            conf_colors = {"high":"#10b981","medium":"#f59e0b","low":"#ef4444"}
            conf_bg     = {"high":"rgba(16,185,129,0.1)","medium":"rgba(245,158,11,0.1)","low":"rgba(239,68,68,0.1)"}
            st.markdown(f"""
            <div style="text-align:center;margin-top:0.8rem;">
                <span style="background:{conf_bg.get(conf,'')};border:1px solid {conf_colors.get(conf,'#475569')};
                             color:{conf_colors.get(conf,'#94a3b8')};padding:4px 14px;border-radius:20px;
                             font-size:0.78rem;font-weight:700;">
                    AI Confidence: {conf.upper()}
                </span>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Raw OCR Text"):
                st.code(st.session_state["_scan_ocr"].get("raw_text",""), language=None)

        with c_form:
            st.markdown("""
            <div style="color:#10b981;font-size:0.85rem;font-weight:600;margin-bottom:1rem;">
                ✅ Receipt parsed — review and save below
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

                if st.form_submit_button("💾  Save Expense", use_container_width=True):
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
                        st.success("Expense saved!")
                        for k in ("_scan_validated","_scan_parsed","_scan_ocr","_scan_file_name"):
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to save: {exc}")


# ============================================================
# PAGE: ADD EXPENSE
# ============================================================
def page_add_expense():
    _page_hero("Add Expense", "Manually record fuel, maintenance, or insurance costs", "➕")

    vid = require_vehicle()
    if not vid:
        return

    st.markdown("<div style='max-width:640px;'>", unsafe_allow_html=True)
    with st.form("expense_form"):
        type_col, date_col = st.columns(2)
        with type_col:
            rec_type = st.selectbox("Expense Type", ["fuel", "maintenance", "insurance"])
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

        vendor = st.text_input("Vendor / Station", placeholder="e.g. PSO Lahore")
        desc   = st.text_area("Description", placeholder="Optional notes...", height=80)

        if st.form_submit_button("💾  Save Expense", use_container_width=True):
            if amount <= 0:
                st.error("Amount must be greater than zero.")
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
                st.success(f"✅ Saved {rec_type} expense: {fmt_pkr(amount)}")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PAGE: VEHICLE LOGBOOK
# ============================================================
def page_logbook():
    _page_hero("Vehicle Logbook", "Complete searchable record of all expenses", "📖")

    vid = require_vehicle()
    if not vid:
        return

    # Controls
    sc, fc = st.columns([3, 1])
    with sc:
        search = st.text_input("🔍  Search by vendor or description", key="log_search",
                               label_visibility="collapsed",
                               placeholder="🔍  Search by vendor or description...")
    with fc:
        filter_type = st.selectbox("Type", ["All", "fuel", "maintenance", "insurance"],
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
        _empty_state("📭", "No records found",
                     "Add expenses manually or scan a receipt to get started.")
        return

    st.markdown(f"""
    <div style="color:#475569;font-size:0.82rem;margin-bottom:1rem;">
        Showing <strong style="color:#94a3b8">{len(records)}</strong> record{"s" if len(records)!=1 else ""}
    </div>
    """, unsafe_allow_html=True)

    for rec in records:
        rtype = rec.get("record_type","unknown")
        is_editing = st.session_state.get("editing_id") == rec["id"]

        # Build detail chips
        chips = []
        if rec.get("amount_pkr"):
            chips.append(f'<span style="color:#f1f5f9;font-weight:700">{fmt_pkr(rec["amount_pkr"])}</span>')
        if rec.get("odometer_km"):
            chips.append(f'<span style="color:#64748b">{rec["odometer_km"]:,} km</span>')
        if rec.get("liters"):
            chips.append(f'<span style="color:#64748b">{rec["liters"]:.1f} L</span>')
        if rec.get("vendor_name"):
            chips.append(f'<span style="color:#64748b">{rec["vendor_name"]}</span>')
        chips_html = ' <span style="color:#1e293b;margin:0 2px">·</span> '.join(chips)

        with st.container():
            st.markdown(f"""
            <div class="ss-card ss-card-accent-top" style="margin-bottom:0.3rem;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;">
                    <div style="display:flex;align-items:center;gap:0.6rem;">
                        {_badge(rtype)}
                        <span style="color:#475569;font-size:0.82rem;">📅 {rec.get('date','—')}</span>
                    </div>
                </div>
                <div style="font-size:0.9rem;">{chips_html}</div>
                {"<div style='color:#475569;font-size:0.8rem;margin-top:0.3rem;'>" + rec['description'] + "</div>" if rec.get('description') else ""}
            </div>
            """, unsafe_allow_html=True)

            btn_c1, btn_c2, spacer = st.columns([1, 1, 6])
            with btn_c1:
                if st.button("✏️ Edit", key=f"edit_{rec['id']}", use_container_width=True):
                    st.session_state["editing_id"] = rec["id"]
                    st.rerun()
            with btn_c2:
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button("🗑 Delete", key=f"del_{rec['id']}", use_container_width=True):
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
                        new_desc = st.text_area("Description",
                            value=rec.get("description") or "", height=80)

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
                            db.update_record(
                                rec["id"],
                                amount_pkr=new_amount if new_amount > 0 else None,
                                description=new_desc or None,
                                vendor_name=new_vendor or None,
                            )
                            st.success("Updated!")
                            st.session_state.pop("editing_id", None)
                            st.rerun()
                    with sc2:
                        if st.form_submit_button("✕ Cancel", use_container_width=True):
                            st.session_state.pop("editing_id", None)
                            st.rerun()


# ============================================================
# PAGE: MAINTENANCE
# ============================================================
def page_maintenance():
    _page_hero("Maintenance", "Track service intervals, get AI advice, and download reports", "🔧")

    vid = require_vehicle()
    if not vid:
        return

    import plotly.graph_objects as go

    # ── Service Status Cards ────────────────────────────────
    _section("SERVICE STATUS")
    status = maintenance.check_due_maintenance(vid)

    status_meta = {
        "overdue":  ("🔴", "#ef4444", "rgba(239,68,68,0.1)",  "rgba(239,68,68,0.3)"),
        "due_soon": ("🟡", "#f59e0b", "rgba(245,158,11,0.1)", "rgba(245,158,11,0.3)"),
        "not_due":  ("🟢", "#10b981", "rgba(16,185,129,0.1)", "rgba(16,185,129,0.15)"),
        "unknown":  ("⚪", "#64748b", "rgba(100,116,139,0.1)","rgba(100,116,139,0.15)"),
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
                overdue_txt = f'<div style="color:#ef4444;font-size:0.75rem;margin-top:0.3rem;">⬆ {svc["overdue_by"]:,} km overdue</div>'
            with cols[idx]:
                st.markdown(f"""
                <div style="background:{bg};border:1px solid {border};border-radius:14px;
                            padding:1.2rem 1rem;text-align:center;height:100%;">
                    <div style="font-size:1.8rem;margin-bottom:0.4rem;">{icon}</div>
                    <div style="color:#f1f5f9;font-weight:700;font-size:0.88rem;">{name}</div>
                    <div style="color:{color};font-size:0.72rem;font-weight:700;
                                text-transform:uppercase;margin:0.3rem 0;">{s.replace('_',' ')}</div>
                    <div style="color:#64748b;font-size:0.75rem;">Since last: {since}</div>
                    <div style="color:#475569;font-size:0.72rem;">Interval: {interval}</div>
                    {overdue_txt}
                </div>
                """, unsafe_allow_html=True)
    else:
        _empty_state("🔧", "No maintenance data", "Add maintenance records to track service intervals.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Advice ───────────────────────────────────────────
    _section("AI MAINTENANCE ADVICE")
    if st.button("🤖  Get AI Advice", key="ai_advice"):
        with st.spinner("Consulting AI advisor..."):
            advice = maintenance.get_ai_maintenance_advice(vid)
            st.session_state["last_advice"] = advice

    if "last_advice" in st.session_state:
        st.markdown(f"""
        <div class="insight-box fade-in" style="margin-top:0.8rem;">
            {st.session_state["last_advice"]}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PDF Report ──────────────────────────────────────────
    _section("LOGBOOK REPORT")
    st.markdown("""
    <div class="ss-card" style="display:flex;align-items:center;gap:1rem;padding:1.2rem 1.5rem;">
        <div style="font-size:2rem;">📄</div>
        <div>
            <div style="color:#f1f5f9;font-weight:700;font-size:0.95rem;">Download Full Logbook PDF</div>
            <div style="color:#475569;font-size:0.82rem;">
                Includes vehicle summary, spending totals, and all expense records.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("📥  Generate PDF Report", key="gen_pdf"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_path = pdf_report.generate_logbook_pdf(vid, "logbook_report.pdf")
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "⬇  Download PDF",
                        f,
                        file_name="logbook_report.pdf",
                        mime="application/pdf",
                        use_container_width=False,
                    )
            except Exception as exc:
                st.error(f"Failed to generate PDF: {exc}")


# ============================================================
# PAGE: ASK SAFARSYNC
# ============================================================
def page_ask():
    _page_hero("Ask SafarSync", "Ask anything about your vehicle — answers backed by real data", "💬")

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
            <div style="display:flex;justify-content:flex-end;margin-bottom:0.5rem;">
                <div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.2);
                            border-radius:16px 0 16px 16px;padding:0.8rem 1.2rem;max-width:70%;
                            color:#e2e8f0;font-size:0.9rem;">
                    {entry['question']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            # AI bubble
            st.markdown(f"""
            <div class="chat-bubble fade-in" style="max-width:80%;margin-bottom:1rem;">
                <div style="font-size:0.7rem;color:#475569;font-weight:600;
                            text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">
                    ✦ SafarSync AI
                </div>
                {entry['answer']}
            </div>
            """, unsafe_allow_html=True)

        col_clr, _ = st.columns([1, 5])
        with col_clr:
            st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
            if st.button("Clear chat", key="clear_chat"):
                st.session_state["chat_history"] = []
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Input
    question = st.text_input("",
        placeholder="e.g. How much did I spend on fuel last month?",
        key="ask_input", label_visibility="collapsed")

    if st.button("Send  ➤", key="ask_btn") and question.strip():
        metrics      = analytics.get_summary_metrics(vid)
        maint_status = maintenance.check_due_maintenance(vid)
        anomalies_list = anomaly.find_anomalies(vid)

        facts = [f"Total spending: {fmt_pkr(metrics['total_spend'])}"]
        if metrics["fuel_spend"]:
            facts.append(f"Fuel spending: {fmt_pkr(metrics['fuel_spend'])}")
        if metrics["maintenance_spend"]:
            facts.append(f"Maintenance spending: {fmt_pkr(metrics['maintenance_spend'])}")
        if metrics["insurance_spend"]:
            facts.append(f"Insurance spending: {fmt_pkr(metrics['insurance_spend'])}")
        if metrics["total_distance"]:
            facts.append(f"Total distance tracked: {metrics['total_distance']:,} km")
        if metrics["average_fuel_efficiency"]:
            facts.append(f"Average fuel efficiency: {metrics['average_fuel_efficiency']:.1f} km/L")
        if metrics["cost_per_km"]:
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

        with st.spinner("Thinking..."):
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
                st.error("Cannot reach the AI service. Check your connection.")
            except TimeoutError:
                st.error("Request timed out. Please try again.")
            except RuntimeError as exc:
                st.error(f"AI service error: {exc}")
    elif not st.session_state["chat_history"]:
        # Suggested questions
        _section("SUGGESTED QUESTIONS")
        suggestions = [
            "How much have I spent on fuel this year?",
            "What is my average fuel efficiency?",
            "Which services are overdue?",
            "What is my cost per kilometre?",
        ]
        s_cols = st.columns(2)
        for i, sug in enumerate(suggestions):
            with s_cols[i % 2]:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(0,212,255,0.1);
                            border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.5rem;
                            color:#64748b;font-size:0.85rem;cursor:pointer;">
                    💬 &nbsp;{sug}
                </div>
                """, unsafe_allow_html=True)


# ============================================================
# PAGE: MANAGE VEHICLES
# ============================================================
def page_manage():
    _page_hero("Manage Vehicles", "Add new vehicles and switch your active vehicle", "🚗")

    # ── Add Vehicle Form ────────────────────────────────────
    _section("ADD NEW VEHICLE")
    st.markdown("<div style='max-width:560px;'>", unsafe_allow_html=True)
    with st.form("add_vehicle_form"):
        name = st.text_input("Vehicle Name", placeholder="e.g. My Toyota Corolla")
        reg  = st.text_input("Registration Number", placeholder="e.g. ABC-1234")
        if st.form_submit_button("➕  Add Vehicle", use_container_width=True):
            if not name.strip():
                st.error("Vehicle name is required.")
            else:
                new_id = db.add_vehicle(name.strip(), reg.strip())
                st.success(f"Vehicle '{name}' added!")
                st.session_state["vehicle_id"] = new_id
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Vehicle List ────────────────────────────────────────
    vehicles = db.get_vehicles()
    if not vehicles:
        _empty_state("🚗", "No vehicles yet", "Add your first vehicle above.")
        return

    _section(f"YOUR VEHICLES  ({len(vehicles)})")
    current_id = st.session_state.get("vehicle_id")

    for v in vehicles:
        is_active = current_id == v["id"]
        active_cls = "active-vehicle" if is_active else ""
        reg_txt = v.get("registration_number") or "—"

        st.markdown(f"""
        <div class="vehicle-card {active_cls}">
            <div class="vc-icon">{"🚗" if not is_active else "✅"}</div>
            <div style="flex:1;">
                <div class="vc-name">{v['name']}</div>
                <div class="vc-reg">Reg: {reg_txt}</div>
            </div>
            {"<span style='background:rgba(0,212,255,0.12);color:#00d4ff;border:1px solid rgba(0,212,255,0.3);padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;'>ACTIVE</span>" if is_active else ""}
        </div>
        """, unsafe_allow_html=True)

        if not is_active:
            col_sel, _ = st.columns([1, 5])
            with col_sel:
                if st.button(f"Select", key=f"sel_{v['id']}", use_container_width=True):
                    st.session_state["vehicle_id"] = v["id"]
                    st.rerun()


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
        <div style="max-width:600px;margin:4rem auto;text-align:center;">
            <div style="font-size:3rem;margin-bottom:1rem;">⚙️</div>
            <h2 style="color:#f1f5f9;">Configuration Required</h2>
            <p style="color:#64748b;">One or more required secrets are missing.</p>
        </div>
        """, unsafe_allow_html=True)
        st.code(_config_error)
        st.info("Add the missing secrets to your `.env` file (local) or "
                "Streamlit Community Cloud secrets.")
        return

    # ── Startup ─────────────────────────────────────────────
    db.init_db()
    vehicles = db.get_vehicles()
    if not vehicles:
        demo_data.seed_demo_data()
        vehicles = db.get_vehicles()

    # ── Sidebar ─────────────────────────────────────────────
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
            <span class="logo-mark">SafarSync</span>
            <span style="background:linear-gradient(135deg,#00d4ff,#7c3aed);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                         font-weight:800;font-size:0.9rem;letter-spacing:0.05em;">AI</span>
            <div class="logo-sub">Vehicle Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Vehicle selector
        st.markdown('<div style="font-size:0.7rem;font-weight:700;color:#334155;'
                    'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;">'
                    'ACTIVE VEHICLE</div>', unsafe_allow_html=True)

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
                <div class="sidebar-vehicle-pill">
                    📋 &nbsp;{reg}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No vehicles found.")

        # Quick stats in sidebar
        vid = st.session_state.get("vehicle_id")
        if vid:
            st.divider()
            st.markdown('<div style="font-size:0.7rem;font-weight:700;color:#334155;'
                        'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;">'
                        'QUICK STATS</div>', unsafe_allow_html=True)
            try:
                m = analytics.get_summary_metrics(vid)
                st.markdown(f"""
                <div style="font-size:0.8rem;color:#64748b;line-height:2;">
                    <div>💰 Total: <strong style="color:#f1f5f9">{fmt_pkr(m['total_spend'])}</strong></div>
                    <div>⛽ Fuel eff: <strong style="color:#00d4ff">{f"{m['average_fuel_efficiency']:.1f} km/L" if m['average_fuel_efficiency'] else '—'}</strong></div>
                    <div>📏 Distance: <strong style="color:#f1f5f9">{m['total_distance']:,} km</strong></div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                pass

        st.divider()
        st.markdown('<div style="font-size:0.68rem;color:#1e293b;text-align:center;'
                    'padding-bottom:0.5rem;">SafarSync AI · Built for Pakistan 🇵🇰</div>',
                    unsafe_allow_html=True)

    # ── Navigation ───────────────────────────────────────────
    pages = [
        st.Page(page_dashboard,    title="Dashboard",        icon="📊"),
        st.Page(page_scan_receipt, title="Scan Receipt",     icon="📷"),
        st.Page(page_add_expense,  title="Add Expense",      icon="➕"),
        st.Page(page_logbook,      title="Vehicle Logbook",  icon="📖"),
        st.Page(page_maintenance,  title="Maintenance",      icon="🔧"),
        st.Page(page_ask,          title="Ask SafarSync",    icon="💬"),
        st.Page(page_manage,       title="Manage Vehicles",  icon="🚗"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
