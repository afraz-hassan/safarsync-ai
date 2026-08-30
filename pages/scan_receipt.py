"""Scan Receipt page — upload a receipt image, OCR + AI parse, verify & save."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime

import streamlit as st

import database as db
import receipt_scanner
import validation

from ui_helpers import esc, require_vehicle, page_hero


def render() -> None:
    page_hero("Scan Receipt", "Upload a receipt and let AI fill in the details", "📷")

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
        <div style="flex:1; height:4px; border-radius:2px; background:{'#2563EB' if step>=1 else '#E2E8F0'};"></div>
        <div style="flex:1; height:4px; border-radius:2px; background:{'#2563EB' if step>=2 else '#E2E8F0'};"></div>
        <div style="flex:1; height:4px; border-radius:2px; background:{'#2563EB' if step>=3 else '#E2E8F0'};"></div>
    </div>
    <div style="display:flex;gap:1rem;margin-bottom:2rem;font-size:0.8rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em;">
        <span style="color:{'#2563EB' if step>=1 else '#94A3B8'};flex:1;">① Upload</span>
        <span style="color:{'#2563EB' if step>=2 else '#94A3B8'};flex:1;text-align:center;">② Extraction</span>
        <span style="color:{'#2563EB' if step>=3 else '#94A3B8'};flex:1;text-align:right;">③ Review</span>
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
            conf_colors = {"high": "#059669", "medium": "#B45309", "low": "#DC2626"}
            st.markdown(f"""
            <div style="text-align:center;margin-top:1rem;">
                <span style="border:1px solid {conf_colors.get(conf,'#94A3B8')};
                             color:{conf_colors.get(conf,'#64748B')};padding:6px 16px;border-radius:4px;
                             font-size:0.8rem;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;">
                    AI Confidence: {conf}
                </span>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Raw OCR Data"):
                st.code(st.session_state["_scan_ocr"].get("raw_text", ""), language=None)

        with c_form:
            st.markdown("""
            <div class="fade-in" style="color:#0891B2;font-size:0.95rem;font-weight:700;margin-bottom:1.5rem; letter-spacing:0.05em; text-transform:uppercase;">
                ✓ Extraction complete — please verify the details
            </div>
            """, unsafe_allow_html=True)

            validated = st.session_state["_scan_validated"]
            data = validated.get("data", {})

            # Pre-populate date from AI extraction
            extracted_date = date.today()
            if data.get("date"):
                try:
                    extracted_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass

            with st.form("scan_form"):
                type_opts = ["fuel", "maintenance", "insurance", "unknown"]
                rec_type = st.selectbox("Record Type", type_opts,
                    index=type_opts.index(data.get("record_type", "fuel")))
                # Show AI-extracted category badge
                ai_category = data.get("category")
                if ai_category:
                    st.markdown(
                        f'<span style="background:#E0F2FE;color:#0369A1;padding:3px 10px;'
                        f'border-radius:20px;font-size:0.75rem;font-weight:700;'
                        f'text-transform:uppercase;letter-spacing:0.05em;">'
                        f'\U0001F3F7\uFE0F {esc(ai_category)}</span>',
                        unsafe_allow_html=True,
                    )
                rec_date = st.date_input("Date", value=extracted_date)
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
                desc = st.text_area("Description", value=data.get("description") or "", height=80)

                # Display extracted line items if available
                line_items = data.get("line_items", [])
                if line_items:
                    with st.expander("\U0001F4CB Extracted Line Items", expanded=False):
                        for i, item in enumerate(line_items, 1):
                            li_desc = item.get("description", "\u2014")
                            qty = item.get("quantity", "\u2014")
                            price = item.get("unit_price", "\u2014")
                            total = item.get("total", "\u2014")
                            st.markdown(f"**{i}.** {li_desc} \u2014 Qty: {qty}, Unit: {price}, Total: {total}")

                if st.form_submit_button("\U0001F4BE Save Record", use_container_width=True):
                    try:
                        # Serialize parsed OCR data safely before persisting.
                        try:
                            raw_ocr_json = json.dumps(
                                st.session_state.get("_scan_parsed", {}))
                        except (TypeError, ValueError):
                            raw_ocr_json = None

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
                            raw_ocr_json=raw_ocr_json,
                        )
                        st.success("Record saved successfully!")
                        for k in ("_scan_validated", "_scan_parsed", "_scan_ocr", "_scan_file_name"):
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Save failed: {exc}")
