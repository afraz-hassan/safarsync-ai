"""Maintenance page — service status cards, AI advice, and PDF report export."""

from __future__ import annotations

import streamlit as st

import database as db
import maintenance

from database import get_db_version

from ui_helpers import esc, require_vehicle, page_hero, section, empty_state


def render() -> None:
    page_hero("Maintenance", "Track service intervals, get AI advice, and export reports", "🔧")

    vid = require_vehicle()
    if not vid:
        return

    # ── Service Status Cards ────────────────────────────────
    section("SERVICE STATUS")
    status = maintenance.check_due_maintenance(vid, db_version=get_db_version())

    status_meta = {
        "overdue":  ("🔴", "#DC2626", "#FEF2F2", "#FECACA"),
        "due_soon": ("🟡", "#B45309", "#FFFBEB", "#FDE68A"),
        "not_due":  ("🟢", "#059669", "#ECFDF5", "#A7F3D0"),
        "unknown":  ("⚪", "#64748B", "#F1F5F9", "#E2E8F0"),
    }
    labels = {"oil_change": "Oil Change", "air_filter": "Air Filter",
              "brake_check": "Brake Check", "tire_rotation": "Tire Rotation"}

    if status:
        cols = st.columns(len(status))
        for idx, svc in enumerate(status):
            s = svc["status"]
            icon, color, bg, border = status_meta.get(s, status_meta["unknown"])
            name = labels.get(svc["type"], svc["type"].replace("_", " ").title())
            since = f'{svc["km_since_last"]:,} km' if svc.get("km_since_last") is not None else "—"
            interval = f'{svc["interval_km"]:,} km'
            overdue_txt = ""
            if svc.get("overdue_by") is not None:
                overdue_txt = f'<div style="color:#DC2626;font-size:0.8rem;margin-top:0.8rem;font-weight:700;">⬆ {svc["overdue_by"]:,} km overdue</div>'
            with cols[idx]:
                st.markdown(f"""
                <div class="fade-in" style="background:{bg};border:1px solid {border};border-radius:12px;
                            padding:2rem 1.5rem;text-align:center;height:100%;">
                    <div style="font-size:2.2rem;margin-bottom:0.8rem;">{icon}</div>
                    <div style="color:var(--ss-text);font-family:'Manrope',sans-serif;font-weight:700;font-size:1.1rem;">{esc(name)}</div>
                    <div style="color:{color};font-size:0.75rem;font-weight:800;
                                text-transform:uppercase;letter-spacing:0.1em;margin:0.8rem 0;">{s.replace('_',' ')}</div>
                    <div style="color:var(--ss-text-soft);font-size:0.85rem;margin-bottom:0.3rem;">Last: <span style="color:var(--ss-text)">{since}</span></div>
                    <div style="color:var(--ss-text-muted);font-size:0.8rem;">Interval: {interval}</div>
                    {overdue_txt}
                </div>
                """, unsafe_allow_html=True)
    else:
        empty_state("🔧", "No Maintenance Data Yet", "Add maintenance records to start tracking service intervals.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Advice ───────────────────────────────────────────
    section("AI MAINTENANCE ADVICE")
    if st.button("🤖 Get Maintenance Advice", key="ai_advice"):
        with st.spinner("Analyzing maintenance logs..."):
            advice = maintenance.get_ai_maintenance_advice(vid)
            st.session_state["last_advice"] = advice

    if "last_advice" in st.session_state:
        st.markdown(f"""
        <div class="insight-box fade-in" style="margin-top:1rem;">
            {esc(st.session_state["last_advice"])}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PDF Report ──────────────────────────────────────────
    section("EXPORT REPORT")
    st.markdown("""
    <div class="ss-card fade-in" style="display:flex;align-items:center;gap:1.5rem;padding:1.5rem 2rem;">
        <div style="font-size:2.5rem;">📄</div>
        <div>
            <div style="color:var(--ss-text);font-family:'Manrope',sans-serif;font-weight:700;font-size:1.2rem;margin-bottom:0.2rem;">Generate Logbook Report</div>
            <div style="color:var(--ss-text-soft);font-size:0.9rem;">
                Compiles vehicle details, cost summaries, and the full transaction history into a PDF.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("\U0001F4C4 Generate PDF Report", key="gen_pdf", use_container_width=True):
        with st.spinner("Generating report..."):
            try:
                from pdf_report import generate_logbook_pdf_bytes
                pdf_bytes = generate_logbook_pdf_bytes(vid)
                st.session_state["pdf_bytes"] = pdf_bytes
                st.session_state["pdf_ready"] = True
            except Exception as exc:
                st.error(f"Report generation failed: {exc}")

    if st.session_state.get("pdf_ready"):
        st.download_button(
            label="\u2B07\uFE0F Download PDF Report",
            data=st.session_state["pdf_bytes"],
            file_name="safarsync_logbook.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
