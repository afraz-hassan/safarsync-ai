"""Logbook page — complete transaction history with inline edit and delete."""

from __future__ import annotations

import streamlit as st

import database as db

from ui_helpers import esc, fmt_pkr, require_vehicle, badge, page_hero, empty_state


def render() -> None:
    page_hero("Logbook", "A complete record of every transaction for this vehicle", "📖")

    vid = require_vehicle()
    if not vid:
        return

    # Controls
    sc, fc = st.columns([3, 1])
    with sc:
        search = st.text_input("🔍  Search Records", key="log_search",
                               label_visibility="collapsed",
                               placeholder="🔍  Search by vendor or description...")
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
        empty_state("📭", "No Records Yet",
                    "Add records manually or scan a receipt to get started.")
        return

    st.markdown(f"""
    <div style="color:var(--ss-text-muted);font-size:0.85rem;margin-bottom:1.5rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
        Showing <strong style="color:#2563EB">{len(records)}</strong> record{"s" if len(records)!=1 else ""}
    </div>
    """, unsafe_allow_html=True)

    for rec in records:
        rtype = rec.get("record_type", "unknown")
        is_editing = st.session_state.get("editing_id") == rec["id"]

        # Build detail chips
        chips = []
        if rec.get("amount_pkr"):
            chips.append(f'<span style="color:var(--ss-text);font-weight:700;font-size:1.05rem;">{fmt_pkr(rec["amount_pkr"])}</span>')
        if rec.get("odometer_km"):
            chips.append(f'<span style="color:var(--ss-text-soft)">{rec["odometer_km"]:,} km</span>')
        if rec.get("liters"):
            chips.append(f'<span style="color:var(--ss-text-soft)">{rec["liters"]:.1f} L</span>')
        if rec.get("vendor_name"):
            chips.append(f'<span style="color:var(--ss-text-soft)">{esc(rec["vendor_name"])}</span>')
        chips_html = ' <span style="color:var(--ss-border-strong);margin:0 8px">|</span> '.join(chips)

        with st.container():
            st.markdown(f"""
            <div class="ss-card ss-card-accent-top fade-in" style="margin-bottom:0.5rem; padding: 1.2rem 1.8rem;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.8rem;">
                    <div style="display:flex;align-items:center;gap:1rem;">
                        {badge(rtype)}
                        <span style="color:var(--ss-text-muted);font-size:0.85rem;font-weight:600;letter-spacing:0.05em;">DATE: {esc(rec.get('date','—'))}</span>
                    </div>
                </div>
                <div style="font-size:0.95rem; margin-bottom:0.5rem;">{chips_html}</div>
                {"<div style='color:var(--ss-text-muted);font-size:0.85rem;font-style:italic;'>" + esc(rec['description']) + "</div>" if rec.get('description') else ""}
            </div>
            """, unsafe_allow_html=True)

            btn_c1, btn_c2, spacer = st.columns([1, 1, 6])
            with btn_c1:
                st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
                if st.button("✏️ Edit", key=f"edit_{rec['id']}", use_container_width=True):
                    st.session_state["editing_id"] = rec["id"]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with btn_c2:
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_{rec['id']}", use_container_width=True):
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
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
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
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop("editing_id", None)
                            st.rerun()
