"""Manage Vehicles page — add vehicles and switch the active one."""

from __future__ import annotations

import streamlit as st

import database as db

from ui_helpers import esc, page_hero, section, empty_state


def render() -> None:
    page_hero("My Vehicles", "Add a vehicle and manage which one is active", "🚗")

    # ── Add Vehicle Form ────────────────────────────────────
    section("ADD A VEHICLE")
    st.markdown("<div class='fade-in' style='max-width:600px;'>", unsafe_allow_html=True)
    with st.form("add_vehicle_form"):
        name = st.text_input("Vehicle Name", placeholder="e.g. Primary Commuter")
        reg = st.text_input("Registration Plate", placeholder="e.g. ISB-9876")
        if st.form_submit_button("➕ Add Vehicle", use_container_width=True):
            if not name.strip():
                st.error("Vehicle name is required.")
            else:
                new_id = db.add_vehicle(name.strip(), reg.strip())
                st.success(f"'{name}' added successfully.")
                st.session_state["vehicle_id"] = new_id
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Vehicle List ────────────────────────────────────────
    vehicles = db.get_vehicles()
    if not vehicles:
        empty_state("🚗", "No Vehicles Yet", "Add your first vehicle above.")
        return

    section(f"YOUR VEHICLES  ({len(vehicles)})")
    current_id = st.session_state.get("vehicle_id")

    for v in vehicles:
        is_active = current_id == v["id"]

        # Vehicle card — visual presentation only
        bg = "#EEF4FF" if is_active else "#ffffff"
        border = "#93C5FD" if is_active else "#E4E9F1"

        st.markdown(f"""
        <div class="fade-in" style="background:{bg}; border:1px solid {border}; border-radius:12px;
                    padding:1.5rem 2rem; margin-bottom:1rem; display:flex; align-items:center; gap:1.5rem;
                    transition:all 0.2s;">
            <div style="font-size:2.5rem; flex-shrink:0;">{"🚘" if is_active else "🚗"}</div>
            <div style="flex:1;">
                <div style="color:var(--ss-text); font-family:'Manrope',sans-serif; font-weight:700; font-size:1.2rem; margin-bottom:0.2rem;">{esc(v['name'])}</div>
                <div style="color:var(--ss-text-soft); font-size:0.85rem; letter-spacing:0.05em;">Plate: <span style="color:var(--ss-text)">{esc(v.get('registration_number', '')) or '—'}</span></div>
            </div>
            {"<span style='background:#2563EB;color:#ffffff;padding:6px 16px;border-radius:4px;font-size:0.8rem;font-weight:900;letter-spacing:0.1em;'>ACTIVE</span>" if is_active else ""}
        </div>
        """, unsafe_allow_html=True)

        if not is_active:
            col_sel, _ = st.columns([1, 5])
            with col_sel:
                st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
                if st.button(f"Select", key=f"sel_{v['id']}", use_container_width=True):
                    st.session_state["vehicle_id"] = v["id"]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
