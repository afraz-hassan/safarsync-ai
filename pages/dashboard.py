"""Dashboard page — spending overview, efficiency charts, anomaly alerts, AI insights."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import database as db
import analytics
import anomaly
import insights

from database import get_db_version

from ui_helpers import (
    esc,
    fmt_pkr,
    require_vehicle,
    pill_severity,
    page_hero,
    section,
    empty_state,
    PLOT_LAYOUT,
)


def render() -> None:
    page_hero("Dashboard", "An overview of your vehicle's costs and performance", "")

    vid = require_vehicle()
    if not vid:
        return

    # ── Date range filter (shown right after the hero) ─────────────────────
    col_from, col_to = st.columns(2)
    with col_from:
        start: date = st.date_input(
            "From",
            value=date.today() - timedelta(days=30),
            key="dash_start",
        )
    with col_to:
        end: date = st.date_input(
            "To",
            value=date.today(),
            key="dash_end",
        )

    # ── Lifetime (unfiltered) metrics — always show all-time total ───────────
    try:
        lifetime_metrics = analytics.get_summary_metrics(vid, db_version=get_db_version())
    except Exception:
        st.error("Unable to load lifetime metrics. Please try again later.")
        lifetime_metrics = {
            "total_spend": 0.0, "fuel_spend": 0.0,
            "maintenance_spend": 0.0, "insurance_spend": 0.0,
            "average_fuel_efficiency": None, "total_distance": 0,
            "cost_per_km": None,
        }

    st.markdown(
        "<div style='margin-top:1.5rem'></div>",
        unsafe_allow_html=True,
    )
    section("TOTAL LIFETIME EXPENSE")
    st.metric(
        "All-Time Total",
        fmt_pkr(lifetime_metrics["total_spend"]),
    )

    # ── Filtered records + metrics for the selected date range ───────────────
    filtered = db.get_records(vid, start_date=str(start), end_date=str(end))
    try:
        metrics = analytics.get_summary_metrics_for_records(filtered, vid)
    except Exception:
        st.error("Unable to compute filtered metrics. Please try again later.")
        metrics = {
            "total_spend": 0.0, "fuel_spend": 0.0,
            "maintenance_spend": 0.0, "insurance_spend": 0.0,
            "average_fuel_efficiency": None, "total_distance": 0,
            "cost_per_km": None,
        }

    # ── KPI Row 1 ────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='margin-top:1.5rem'></div>",
        unsafe_allow_html=True,
    )
    section("SPENDING OVERVIEW")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Spend", fmt_pkr(metrics["total_spend"]))
    with c2:
        st.metric("Fuel Spend", fmt_pkr(metrics["fuel_spend"]))
    with c3:
        st.metric("Maintenance", fmt_pkr(metrics["maintenance_spend"]))
    with c4:
        st.metric("Insurance", fmt_pkr(metrics["insurance_spend"]))

    # ── KPI Row 2 ────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='margin-top:1.5rem'></div>",
        unsafe_allow_html=True,
    )
    section("EFFICIENCY & DISTANCE")
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
        odometers = [r["odometer_km"] for r in filtered if r.get("odometer_km")]
        latest_odo = f"{max(odometers):,} km" if odometers else "—"
        st.metric("Latest Odometer", latest_odo)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ───────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        section("FUEL EFFICIENCY TREND")

        # Inline fuel-efficiency calculation over the filtered record set
        # (same algorithm as analytics.calculate_fuel_efficiency).
        fuel_recs = sorted(
            [r for r in filtered if r.get("record_type") == "fuel"],
            key=lambda r: r.get("date", ""),
        )
        eff_data: list[dict] = []
        prev_odo: int | None = None

        for rec in fuel_recs:
            cur_odo: int | None = rec.get("odometer_km")
            cur_liters: float | None = rec.get("liters")

            if cur_odo is None:
                continue
            if cur_liters is None or cur_liters == 0:
                prev_odo = cur_odo
                continue
            if prev_odo is None:
                prev_odo = cur_odo
                continue

            dist: int = cur_odo - prev_odo
            if dist <= 0:
                prev_odo = cur_odo
                continue

            eff_data.append({
                "date": rec.get("date"),
                "distance_km": dist,
                "liters": cur_liters,
                "efficiency_km_per_l": round(dist / cur_liters, 2),
                "record_id": rec["id"],
            })
            prev_odo = cur_odo

        if eff_data:
            df = pd.DataFrame(eff_data)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["efficiency_km_per_l"],
                mode="lines+markers",
                line=dict(color="#0891B2", width=3),
                marker=dict(size=8, color="#0891B2",
                            line=dict(color="#ffffff", width=2)),
                fill="tozeroy",
                fillcolor="rgba(8,145,178,0.10)",
                name="km/L",
            ))
            fig.update_layout(
                **PLOT_LAYOUT,
                xaxis_title="Date",
                yaxis_title="km/L",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state(
                "⛽", "No efficiency data in range",
                "Add at least two fuel records with odometer readings in the selected period.",
            )

    with ch2:
        section("MONTHLY SPENDING")

        # Inline monthly aggregation over the filtered record set.
        monthly_groups: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"total_amount": 0.0, "count": 0}
        )
        for rec in filtered:
            date_str: str = rec.get("date", "")
            month_key: str = date_str[:7] if len(date_str) >= 7 else date_str
            record_type: str = rec.get("record_type", "unknown")
            amount: float = rec.get("amount_pkr") or 0.0
            monthly_groups[(month_key, record_type)]["total_amount"] += amount
            monthly_groups[(month_key, record_type)]["count"] += 1

        monthly: list[dict] = [
            {
                "month": month,
                "record_type": rtype,
                "total_amount": round(data["total_amount"], 2),
                "count": data["count"],
            }
            for (month, rtype), data in monthly_groups.items()
        ]
        monthly.sort(key=lambda r: r["month"], reverse=True)

        if monthly:
            df = pd.DataFrame(monthly)
            fig = px.bar(
                df, x="month", y="total_amount", color="record_type",
                barmode="stack",
                color_discrete_map={
                    "fuel": "#2563EB",
                    "maintenance": "#B45309",
                    "insurance": "#DC2626",
                },
            )
            fig.update_layout(
                **PLOT_LAYOUT,
                xaxis_title="Month",
                yaxis_title="Amount (PKR)",
                bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state(
                "📅", "No spending in range",
                "No expenses found in the selected date range.",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Anomaly Alerts ───────────────────────────────────────────────────────
    section("SPENDING ALERTS")
    try:
        anomalies = anomaly.find_anomalies(vid, db_version=get_db_version())
    except Exception:
        st.error("Unable to run anomaly detection. Please try again later.")
        anomalies = []
    if anomalies:
        for a in anomalies:
            sev = a["severity"]
            bg = {"high": "#FEF2F2", "warning": "#FFFBEB", "info": "#EEF4FF"}.get(sev, "")
            bd = {"high": "#FECACA", "warning": "#FDE68A", "info": "#BFDBFE"}.get(sev, "")
            st.markdown(f"""
            <div class="fade-in" style="background:{bg};border:1px solid {bd};border-radius:10px;
                        padding:1rem 1.5rem;margin-bottom:0.8rem;display:flex;
                        align-items:center;gap:1rem;">
                {pill_severity(sev)}
                <span style="color:var(--ss-text);font-size:0.95rem;">{esc(a['message'])}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="fade-in" style="background:#ECFDF5;border:1px solid #A7F3D0;
                    border-radius:10px;padding:1rem 1.5rem;color:#059669;font-size:0.95rem;">
            ✅ &nbsp;No spending anomalies detected — everything looks normal.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Insight Card ──────────────────────────────────────────────────────
    section("AI INSIGHTS")
    col_btn, col_spacer = st.columns([1, 4])
    with col_btn:
        if st.button("✨ Generate Insight", key="gen_insight"):
            with st.spinner("Analyzing your spending patterns..."):
                try:
                    insight_text = insights.get_vehicle_insight(vid)
                    st.session_state["last_insight"] = insight_text
                except Exception:
                    st.error("Unable to generate AI insight. Please try again later.")

    if "last_insight" in st.session_state:
        st.markdown(f"""
        <div class="insight-box fade-in">
            {esc(st.session_state["last_insight"])}
        </div>
        """, unsafe_allow_html=True)
