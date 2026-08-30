"""Add Expense page — manually log a fuel-up, service, or other cost."""

from __future__ import annotations

import io
import json
import logging
import tempfile
from datetime import date

import streamlit as st
from PIL import Image, ImageOps

import database as db

from ui_helpers import badge, fmt_pkr, page_hero, require_vehicle

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dynamic-form field configuration
# ---------------------------------------------------------------------------
# Each key maps to the list of extra widgets shown beyond the standard fields
# (date, amount, description).  "other" has no extras.
# ---------------------------------------------------------------------------

MAINTENANCE_SUBTYPES: list[str] = [
    "oil_change", "air_filter", "brake_check", "tire_rotation", "general",
]

FIELD_CONFIG: dict[str, dict] = {
    "fuel": {
        "fields": [
            {"key": "liters",       "label": "Liters",           "type": "number_input", "min": 0.0, "step": 0.5},
            {"key": "odometer",     "label": "Odometer (km)",    "type": "number_input", "min": 0,   "step": 10},
            {"key": "station_name", "label": "Station Name",     "type": "text_input",   "placeholder": "e.g. PSO High-Octane"},
        ],
    },
    "maintenance": {
        "fields": [
            {"key": "sub_type",        "label": "Service Type",     "type": "selectbox",  "options": MAINTENANCE_SUBTYPES},
            {"key": "garage_name",     "label": "Garage Name",      "type": "text_input", "placeholder": "e.g. Al-Noor Garage"},
            {"key": "parts_replaced",  "label": "Parts Replaced",   "type": "text_input", "placeholder": "e.g. oil filter, spark plugs"},
            {"key": "odometer",        "label": "Odometer (km)",    "type": "number_input","min": 0, "step": 10},
        ],
    },
    "insurance": {
        "fields": [
            {"key": "policy_number", "label": "Policy Number", "type": "text_input", "placeholder": "e.g. INS-2026-12345"},
            {"key": "provider",      "label": "Provider",      "type": "text_input", "placeholder": "e.g. Jubilee Insurance"},
        ],
    },
    "toll": {
        "fields": [
            {"key": "route", "label": "Route", "type": "text_input", "placeholder": "e.g. M-2 Lahore–Islamabad"},
        ],
    },
    "other": {"fields": []},
}


# ---------------------------------------------------------------------------
# Camera → OCR helper (uses in-memory image, no temp file required)
# ---------------------------------------------------------------------------
def _parse_camera_image(uploaded_file) -> dict | None:
    """
    Run the two-stage receipt OCR pipeline on a captured camera image.

    Returns the parsed receipt dict on success, or ``None`` on any failure
    (a warning is shown to the user via ``st.warning``).
    """
    try:
        from receipt_scanner import (
            _resize_if_needed,
            _extract_text_qwen_vl,
            extract_text_from_image,
            parse_receipt_text,
        )
        import config as _cfg
    except ImportError as exc:
        st.warning(f"Receipt scanner unavailable: {exc}")
        return None

    try:
        img = Image.open(uploaded_file)
        original_format = img.format
    except Exception as exc:
        st.warning(f"Could not open captured image: {exc}")
        return None

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    img, _ = _resize_if_needed(img)

    # Determine which OCR engine is configured
    engine: str = getattr(_cfg, "OCR_ENGINE", "ocr_space")

    # ── Stage 1: extract raw text ────────────────────────────────────────────
    if engine == "qwen_vl":
        try:
            raw_text, _ = _extract_text_qwen_vl(img, original_format)
        except Exception as exc:
            st.warning(f"Qwen-VL OCR failed: {exc}")
            return None
    else:
        # OCR.space needs a file path — save to a temp file.
        buffer = io.BytesIO()
        img.save(buffer, format=original_format or "PNG")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(buffer.getvalue())
            tmp_path: str = tmp.name
        result = extract_text_from_image(tmp_path)
        if "error" in result:
            st.warning(f"OCR failed: {result['error']}")
            return None
        raw_text: str = result.get("raw_text", "")

    if not raw_text or not raw_text.strip():
        st.warning("No text could be extracted from the captured image.")
        return None

    # ── Stage 2: interpret with Qwen ─────────────────────────────────────────
    parsed: dict = parse_receipt_text(raw_text)
    if "error" in parsed:
        st.warning(f"Receipt parsing failed: {parsed['error']}")
        return None

    return parsed


# ---------------------------------------------------------------------------
# Session-state helpers for camera pre-fill
# ---------------------------------------------------------------------------
def _store_prefill(parsed: dict) -> None:
    """Push parsed receipt values into session state so the form reads them."""
    mapping = {
        "prefill_amount":      parsed.get("amount_pkr"),
        "prefill_date":        parsed.get("date"),
        "prefill_description": parsed.get("description"),
        "prefill_vendor":      parsed.get("vendor_name"),
        "prefill_liters":      parsed.get("liters"),
        "prefill_odometer":    parsed.get("odometer_km"),
        "prefill_type":        parsed.get("record_type"),
    }
    for key, val in mapping.items():
        if val is not None:
            st.session_state[key] = val


def _consume_prefill(key: str, default=None):
    """Read and remove a pre-fill value from session state."""
    val = st.session_state.pop(key, default)
    return val if val is not None else default


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render() -> None:
    page_hero("Add Expense", "Manually log a fuel-up, service, or other cost", "➕")

    vid = require_vehicle()
    if not vid:
        return

    st.markdown("<div class='fade-in' style='max-width:700px;'>", unsafe_allow_html=True)

    # ── Camera receipt capture (optional, above the form) ────────────────────
    with st.expander("📷 Scan Receipt with Camera", expanded=False):
        st.caption(
            "Capture a receipt photo to auto-fill the form below. "
            "You can still edit every field before saving."
        )
        camera_image = st.camera_input("Capture receipt", key="receipt_camera")

        if camera_image is not None:
            # Only re-parse if this is a *new* capture (not the same bytes
            # we already processed on a previous rerun).
            prev_id = st.session_state.get("_last_camera_id")
            curr_id = id(camera_image)
            if curr_id != prev_id:
                st.session_state["_last_camera_id"] = curr_id
                with st.spinner("Parsing receipt…"):
                    parsed = _parse_camera_image(camera_image)
                if parsed is not None:
                    _store_prefill(parsed)
                    st.session_state["_camera_parsed"] = parsed
                    st.rerun()

        # Show the last parsed result (persists across reruns).
        if st.session_state.get("_camera_parsed"):
            p = st.session_state["_camera_parsed"]
            conf = p.get("confidence", "unknown")
            st.success(
                f"✅ Parsed as **{p.get('record_type', '?').upper()}** — "
                f"{fmt_pkr(p.get('amount_pkr') or 0)}  "
                f"(confidence: {conf})"
            )
            with st.expander("View extracted data"):
                st.json(
                    {k: v for k, v in p.items()
                     if k not in ("raw_response", "warnings")}
                )
            if st.button("Clear scan", key="clear_camera_scan"):
                st.session_state.pop("_camera_parsed", None)
                st.session_state.pop("_last_camera_id", None)
                # Clear all prefill keys
                for k in list(st.session_state.keys()):
                    if k.startswith("prefill_"):
                        st.session_state.pop(k, None)
                st.rerun()

    # ── Expense-class selector (outside form so Streamlit reruns on change) ──
    current_class: str = st.session_state.get("expense_class", "fuel")

    # Pre-select class from camera scan if available.
    prefill_type = st.session_state.get("prefill_type")
    if prefill_type and prefill_type in FIELD_CONFIG:
        current_class = prefill_type

    current_class = st.selectbox(
        "Expense Class",
        list(FIELD_CONFIG.keys()),
        index=list(FIELD_CONFIG.keys()).index(current_class)
        if current_class in FIELD_CONFIG else 0,
        key="expense_class",
    )

    # ── Dynamic form ─────────────────────────────────────────────────────────
    with st.form("expense_form"):
        # Standard fields — always shown regardless of type
        date_col, amt_col = st.columns(2)
        with date_col:
            # Pre-fill date from camera scan (parse "YYYY-MM-DD" string).
            default_date = date.today()
            prefill_date_str = _consume_prefill("prefill_date")
            if prefill_date_str:
                try:
                    default_date = date.fromisoformat(str(prefill_date_str))
                except (ValueError, TypeError):
                    pass
            rec_date = st.date_input("Date", value=default_date, key="exp_date")

        with amt_col:
            prefill_amount = _consume_prefill("prefill_amount", 0.0) or 0.0
            amount = st.number_input(
                "Amount (PKR)", min_value=0.0, step=100.0,
                value=float(prefill_amount),
                placeholder="0.00", key="exp_amount",
            )

        # Type-specific extra fields
        extra_fields: list[dict] = FIELD_CONFIG.get(current_class, {}).get("fields", [])
        extra_vals: dict = {}

        for field in extra_fields:
            fkey: str = field["key"]
            ftype: str = field["type"]
            wkey: str = f"exp_{fkey}"

            if ftype == "number_input":
                pf_key = f"prefill_{fkey}"
                pf_val = _consume_prefill(pf_key) or field.get("min", 0.0)
                extra_vals[fkey] = st.number_input(
                    field["label"],
                    min_value=field.get("min", 0.0),
                    step=field.get("step", 1.0),
                    value=float(pf_val) if pf_val else field.get("min", 0.0),
                    key=wkey,
                )
            elif ftype == "selectbox":
                extra_vals[fkey] = st.selectbox(
                    field["label"],
                    field.get("options", []),
                    key=wkey,
                )
            elif ftype == "text_input":
                pf_key = f"prefill_{fkey}"
                pf_val = _consume_prefill(pf_key, "")
                extra_vals[fkey] = st.text_input(
                    field["label"],
                    value=str(pf_val) if pf_val else "",
                    placeholder=field.get("placeholder", ""),
                    key=wkey,
                )

        # Description — standard field
        prefill_desc = _consume_prefill("prefill_description", "") or ""
        desc: str = st.text_area(
            "Remarks",
            value=str(prefill_desc),
            placeholder="Additional notes...",
            height=80, key="exp_desc",
        )

        # ── Submit ───────────────────────────────────────────────────────────
        if st.form_submit_button("💾 Save Expense", use_container_width=True,
                                  type="primary"):
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                # Determine the DB record_type.
                # For maintenance, use the chosen sub-type so that
                # maintenance.check_due_maintenance() can match it.
                if current_class == "maintenance":
                    rec_type: str = extra_vals.get("sub_type", "maintenance")
                else:
                    rec_type = current_class

                # Common kwargs shared by every record type.
                add_kwargs: dict = dict(
                    vehicle_id=vid,
                    record_type=rec_type,
                    date=rec_date.isoformat(),
                    amount_pkr=amount,
                    description=desc or None,
                    source="manual",
                )

                # Type-specific database columns.
                if current_class == "fuel":
                    add_kwargs["liters"] = extra_vals.get("liters") or None
                    add_kwargs["odometer_km"] = extra_vals.get("odometer") or None
                    add_kwargs["vendor_name"] = extra_vals.get("station_name") or None
                elif current_class == "maintenance":
                    add_kwargs["odometer_km"] = extra_vals.get("odometer") or None
                    add_kwargs["vendor_name"] = extra_vals.get("garage_name") or None

                # Persist extra fields as JSON in the metadata column.
                meta_fields: dict = {
                    k: v for k, v in extra_vals.items()
                    if k not in ("sub_type",) and v
                }
                if meta_fields:
                    try:
                        metadata_str = json.dumps(meta_fields)
                    except (TypeError, ValueError):
                        metadata_str = None
                    if metadata_str:
                        add_kwargs["metadata"] = metadata_str

                db.add_record(**add_kwargs)

                # Clear camera pre-fill state after successful save.
                for k in list(st.session_state.keys()):
                    if k.startswith("prefill_"):
                        st.session_state.pop(k, None)
                st.session_state.pop("_camera_parsed", None)
                st.session_state.pop("_last_camera_id", None)

                # Build a friendly label for the success banner.
                type_label: str = (
                    rec_type.replace("_", " ").title()
                    if current_class == "maintenance"
                    else current_class.upper()
                )
                st.success(
                    f"✅ Saved: {badge(rec_type)} &nbsp; **{type_label}** — {fmt_pkr(amount)}",
                )

    st.markdown("</div>", unsafe_allow_html=True)
