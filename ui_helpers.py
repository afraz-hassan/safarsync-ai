"""
ui_helpers.py — Shared UI helpers for SafarSync AI pages.

Extracted from app.py so that page modules can import them without
circular dependencies.
"""

from __future__ import annotations

from html import escape as _html_escape
from typing import Any

import streamlit as st

import database as db


# ---------------------------------------------------------------------------
# HTML escape
# ---------------------------------------------------------------------------
def esc(value: Any) -> str:
    """HTML-escape a value for safe use in unsafe_allow_html=True contexts."""
    return _html_escape(str(value)) if value is not None else ""


# ---------------------------------------------------------------------------
# Currency formatting
# ---------------------------------------------------------------------------
def fmt_pkr(amount: float | int | None) -> str:
    if amount is None:
        return "PKR 0"
    return f"PKR {amount:,.0f}"


# ---------------------------------------------------------------------------
# Vehicle guard
# ---------------------------------------------------------------------------
def require_vehicle() -> int | None:
    vid = st.session_state.get("vehicle_id")
    if not vid:
        st.markdown("""
        <div class="ss-card fade-in" style="text-align:center;padding:3.5rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">🚘</div>
            <div style="color:var(--ss-text);font-family:'Manrope',sans-serif;font-weight:700;font-size:1.4rem;margin-bottom:0.5rem;">
                No Vehicle Selected
            </div>
            <div style="color:var(--ss-text-soft);font-size:0.95rem;">
                Please select a vehicle from the sidebar to get started.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return None
    if not any(v["id"] == vid for v in db.get_vehicles()):
        st.session_state.pop("vehicle_id", None)
        st.warning("Selected vehicle no longer exists. Please select another.")
        return None
    return vid


# ---------------------------------------------------------------------------
# Badge / pill HTML
# ---------------------------------------------------------------------------
def badge(rec_type: str) -> str:
    cls = f"badge-{rec_type}" if rec_type in ("fuel", "maintenance", "insurance") else "badge-unknown"
    return f'<span class="badge {cls}">{esc(rec_type)}</span>'


def pill_severity(sev: str) -> str:
    colors = {"high": "#DC2626", "warning": "#B45309", "info": "#2563EB"}
    c = colors.get(sev, "#475569")
    symbol = "⬆" if sev == "high" else "▲" if sev == "warning" else "●"
    return (
        f'<span style="color:{c}; border: 1px solid {c}; padding: 4px 10px;'
        f' border-radius: 4px; font-size: 0.7rem; font-weight: 800;'
        f' text-transform: uppercase; letter-spacing: 0.1em;">'
        f'{symbol} {esc(sev)}</span>'
    )


# ---------------------------------------------------------------------------
# Page structural helpers
# ---------------------------------------------------------------------------
def page_hero(title: str, subtitle: str, icon: str = "") -> None:
    st.markdown(f"""
    <div class="page-hero fade-in">
        <h1>{icon} {esc(title)}</h1>
        <p>{esc(subtitle)}</p>
    </div>
    """, unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<div class="section-label fade-in">{label}</div>', unsafe_allow_html=True)


def empty_state(icon: str, title: str, body: str) -> None:
    st.markdown(f"""
    <div class="ss-card fade-in" style="text-align:center; padding:3rem 2rem;">
        <span style="font-size:3rem;display:block;margin-bottom:1rem;">{icon}</span>
        <div style="color:var(--ss-text);font-family:'Manrope',sans-serif;font-weight:700;font-size:1.1rem;margin-bottom:0.5rem;">{esc(title)}</div>
        <p style="color:var(--ss-text-soft);font-size:0.95rem;">{esc(body)}</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Plotly theme
# ---------------------------------------------------------------------------
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#475569", size=12),
    xaxis=dict(
        gridcolor="#EEF2F7",
        linecolor="#E2E8F0",
        tickfont=dict(color="#64748B"),
        title_font=dict(color="#475569"),
    ),
    yaxis=dict(
        gridcolor="#EEF2F7",
        linecolor="#E2E8F0",
        tickfont=dict(color="#64748B"),
        title_font=dict(color="#475569"),
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#E2E8F0",
        borderwidth=1,
        font=dict(color="#334155"),
    ),
    margin=dict(l=10, r=10, t=30, b=10),
    height=360,
)

COLOR_SEQ = ["#2563EB", "#0891B2", "#DC2626", "#059669", "#B45309", "#7C3AED"]
