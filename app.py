"""
app.py — SafarSync AI  |  Entry Point

Slim orchestrator: loads CSS, renders the global sidebar, and wires
page modules via st.navigation().  All page logic lives in pages/.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Module imports — wrapped so a missing secret shows a styled error page.
# ---------------------------------------------------------------------------
try:
    import database as db
    import analytics
    import demo_data
    import config as _config
    _modules_loaded = True
    _config_error: str = ""
except RuntimeError as _exc:
    _modules_loaded = False
    _config_error = str(_exc)

# Page modules
from pages import (
    dashboard,
    scan_receipt,
    add_expense,
    logbook,
    maintenance_page,
    ask_ai,
    manage_vehicles,
)

from ui_helpers import esc, fmt_pkr


# ---------------------------------------------------------------------------
# CSS loader
# ---------------------------------------------------------------------------
_CSS_PATH = Path(__file__).parent / "static" / "style.css"


@st.cache_data
def _load_css() -> str:
    """Read static/style.css and wrap it in a <style> tag (cached)."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    return f"<style>\n{css}\n</style>"


# ---------------------------------------------------------------------------
# Vehicle list — session-state cache, invalidated by DB version counter.
# ---------------------------------------------------------------------------
def _get_vehicles_cached():
    """Return vehicles list, cached until DB version changes."""
    version = db.get_db_version() if hasattr(db, "get_db_version") else 0
    cache_key = "_vehicles_cache"
    version_key = "_vehicles_version"
    if (st.session_state.get(version_key) != version or cache_key not in st.session_state):
        st.session_state[cache_key] = db.get_vehicles()
        st.session_state[version_key] = version
    return st.session_state[cache_key]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def _render_sidebar(vehicles: list[dict]) -> None:
    with st.sidebar:
        # SafarSync AI minimalist SVG logo
        st.markdown("""
        <div class="sidebar-logo fade-in">
            <svg width="72" height="72" viewBox="0 0 72 72" fill="none"
                 xmlns="http://www.w3.org/2000/svg"
                 aria-label="SafarSync AI logo">
                <defs>
                    <linearGradient id="ssLogoGradient" x1="12" y1="12" x2="60" y2="60" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#2563EB"/>
                        <stop offset="1" stop-color="#0891B2"/>
                    </linearGradient>
                </defs>
                <rect x="6" y="6" width="60" height="60" rx="18" fill="#FFFFFF" stroke="#E4E9F1" stroke-width="1.5"/>
                <rect x="6" y="6" width="60" height="60" rx="18" fill="url(#ssLogoGradient)" fill-opacity="0.08"/>
                <path d="M18 44L22.6 29.4C23.2 27.4 25 26 27.1 26H44.9C47 26 48.8 27.4 49.4 29.4L54 44"
                      stroke="url(#ssLogoGradient)" stroke-width="3.2"
                      stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M17.8 41.6H54.2V47.2C54.2 49.1 52.7 50.6 50.8 50.6H21.2C19.3 50.6 17.8 49.1 17.8 47.2V41.6Z"
                      fill="url(#ssLogoGradient)" fill-opacity="0.12"
                      stroke="url(#ssLogoGradient)" stroke-width="2.2"/>
                <circle cx="25.5" cy="45.8" r="2.2" fill="#0F172A"/>
                <circle cx="46.5" cy="45.8" r="2.2" fill="#0F172A"/>
                <path d="M33 28.5H39" stroke="#0F172A" stroke-width="2.2" stroke-linecap="round"/>
                <path d="M51 15L52.1 17.7L54.8 18.8L52.1 19.9L51 22.6L49.9 19.9L47.2 18.8L49.9 17.7L51 15Z"
                      fill="#0891B2"/>
            </svg>
            <div class="logo-mark">SafarSync <span class="logo-ai">AI</span></div>
            <div class="logo-sub">Smart Vehicle Tracking</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Vehicle selector
        st.markdown('<div style="font-size:0.75rem;font-weight:800;color:var(--ss-text-muted);'
                    'text-transform:uppercase;letter-spacing:0.15em;margin-bottom:0.8rem;">'
                    'YOUR VEHICLE</div>', unsafe_allow_html=True)

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
                # Clear vehicle-specific caches to avoid stale data
                for key in ["last_insight", "last_advice", "chat_history", "pdf_bytes", "pdf_ready"]:
                    st.session_state.pop(key, None)
                st.rerun()

            current_v = next((v for v in vehicles if v["id"] == current_id), None)
            if current_v:
                reg = current_v.get("registration_number") or "—"
                st.markdown(f"""
                <div class="sidebar-vehicle-pill fade-in">
                    📋 &nbsp;{esc(reg)}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No vehicles yet.")

        # Quick stats in sidebar
        vid = st.session_state.get("vehicle_id")
        if vid:
            st.divider()
            st.markdown('<div style="font-size:0.75rem;font-weight:800;color:var(--ss-text-muted);'
                        'text-transform:uppercase;letter-spacing:0.15em;margin-bottom:1rem;">'
                        'QUICK STATS</div>', unsafe_allow_html=True)
            try:
                m = analytics.get_summary_metrics(vid, db_version=db.get_db_version())
                st.markdown(f"""
                <div class="fade-in" style="font-size:0.85rem;color:var(--ss-text-soft);line-height:2.2;">
                    <div style="display:flex; justify-content:space-between;"><span>💰 Total:</span> <strong style="color:var(--ss-text)">{fmt_pkr(m['total_spend'])}</strong></div>
                    <div style="display:flex; justify-content:space-between;"><span>⛽ Efficiency:</span> <strong style="color:#0891B2">{f"{m['average_fuel_efficiency']:.1f} km/L" if m['average_fuel_efficiency'] else '—'}</strong></div>
                    <div style="display:flex; justify-content:space-between;"><span>📏 Distance:</span> <strong style="color:var(--ss-text)">{m['total_distance']:,} km</strong></div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                pass

        st.divider()
        st.markdown('<div style="font-size:0.7rem;color:var(--ss-text-muted);text-align:center;'
                    'padding-bottom:1rem;font-weight:600;letter-spacing:0.05em;">SafarSync AI · Vehicle Tracker</div>',
                    unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    st.set_page_config(
        page_title="SafarSync AI",
        page_icon="🚘",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject design system CSS from static/style.css
    st.markdown(_load_css(), unsafe_allow_html=True)

    # ── Config error screen ─────────────────────────────────
    if not _modules_loaded:
        st.markdown("""
        <div class="fade-in" style="max-width:600px;margin:6rem auto;text-align:center;">
            <div style="font-size:4rem;margin-bottom:1.5rem;">⚙️</div>
            <h2 style="color:var(--ss-text);font-family:'Manrope',sans-serif;">Configuration Required</h2>
            <p style="color:var(--ss-text-soft);">Some required configuration is missing.</p>
        </div>
        """, unsafe_allow_html=True)
        st.code(_config_error)
        st.info("Add the missing values to your `.env` file or your Streamlit deployment secrets.")
        return

    # ── Startup ─────────────────────────────────────────────
    db.init_db()
    vehicles = _get_vehicles_cached()
    if not vehicles:
        # First-time user: show onboarding instead of main app
        from pages.onboarding import render as onboarding_render
        onboarding_render()
        st.stop()  # Don't render sidebar or navigation

    # ── Sidebar ─────────────────────────────────────────────
    _render_sidebar(vehicles)

    # ── Navigation ───────────────────────────────────────────
    pages = [
        st.Page(dashboard.render,          title="Dashboard",        icon=":material/space_dashboard:",  url_path="dashboard"),
        st.Page(scan_receipt.render,       title="Scan Receipt",     icon=":material/document_scanner:", url_path="scan-receipt"),
        st.Page(add_expense.render,        title="Add Expense",      icon=":material/add_circle:",       url_path="add-expense"),
        st.Page(logbook.render,            title="Logbook",          icon=":material/menu_book:",        url_path="logbook"),
        st.Page(maintenance_page.render,   title="Maintenance",      icon=":material/build_circle:",     url_path="maintenance"),
        st.Page(ask_ai.render,             title="Ask AI",           icon=":material/smart_toy:",        url_path="ask-ai"),
        st.Page(manage_vehicles.render,    title="My Vehicles",      icon=":material/directions_car:",   url_path="my-vehicles"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
