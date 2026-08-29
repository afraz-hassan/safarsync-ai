"""
app.py — Main entry point for the SafarSync AI Streamlit application.

Provides a multi-page interface for vehicle expense tracking, receipt scanning,
maintenance scheduling, and AI-powered insights.
"""

from __future__ import annotations

import streamlit as st
import json
import tempfile
from datetime import date
from typing import Any

# ---------------------------------------------------------------------------
# Import project modules with error handling for missing secrets.
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
except RuntimeError as exc:
    _modules_loaded = False
    _config_error = str(exc)


# ---------------------------------------------------------------------------
# Helper functions.
# ---------------------------------------------------------------------------
def fmt_pkr(amount: float | int | None) -> str:
    """Format a number as PKR currency string."""
    if amount is None:
        return "PKR 0"
    return f"PKR {amount:,.0f}"


def require_vehicle() -> int | None:
    """Check if a vehicle is selected; show warning if not."""
    vid = st.session_state.get("vehicle_id")
    if not vid:
        st.warning("Please select a vehicle from the sidebar to continue.")
        return None
    return vid


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------
def page_dashboard():
    """Display vehicle metrics, charts, anomalies, and AI insights."""
    st.header("Dashboard")

    vid = require_vehicle()
    if not vid:
        return

    # --- Metrics ---
    metrics = analytics.get_summary_metrics(vid)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Spend", fmt_pkr(metrics["total_spend"]))
    with col2:
        st.metric("Fuel Spend", fmt_pkr(metrics["fuel_spend"]))
    with col3:
        st.metric("Maintenance", fmt_pkr(metrics["maintenance_spend"]))
    with col4:
        avg_eff = metrics.get("average_fuel_efficiency")
        st.metric("Avg km/L", f"{avg_eff:.1f}" if avg_eff else "—")

    col5, col6, col7, _ = st.columns(4)
    with col5:
        cpk = metrics.get("cost_per_km")
        st.metric("Cost/km", f"PKR {cpk:.2f}" if cpk else "—")
    with col6:
        st.metric("Distance", f"{metrics['total_distance']:,} km")
    with col7:
        st.metric("Insurance", fmt_pkr(metrics["insurance_spend"]))

    st.divider()

    # --- Charts ---
    chart1, chart2 = st.columns(2)

    with chart1:
        st.subheader("Fuel Efficiency Trend")
        eff_data = analytics.calculate_fuel_efficiency(vid)
        valid_eff = [e for e in eff_data if "efficiency_km_per_l" in e]
        if valid_eff:
            import pandas as pd
            import plotly.express as px

            df = pd.DataFrame(valid_eff)
            fig = px.line(df, x="date", y="efficiency_km_per_l", markers=True)
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="km/L",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data to show fuel efficiency trend.")

    with chart2:
        st.subheader("Monthly Spending")
        monthly = analytics.monthly_spending_summary(vid)
        if monthly:
            import pandas as pd
            import plotly.express as px

            df = pd.DataFrame(monthly)
            fig = px.bar(
                df,
                x="month",
                y="total_amount",
                color="record_type",
                barmode="stack",
            )
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Amount (PKR)",
                height=350,
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No spending data available.")

    st.divider()

    # --- Anomalies ---
    st.subheader("Anomaly Alerts")
    anomalies = anomaly.find_anomalies(vid)
    if anomalies:
        for a in anomalies:
            severity = a["severity"]
            if severity == "high":
                st.error(f"⚠️ {a['message']}")
            elif severity == "warning":
                st.warning(f"⚠️ {a['message']}")
            else:
                st.info(f"ℹ️ {a['message']}")
    else:
        st.success("No anomalies detected.")

    st.divider()

    # --- AI Insight ---
    st.subheader("AI Insight")
    if st.button("Generate AI Insight", key="gen_insight"):
        with st.spinner("Analyzing vehicle data..."):
            insight_text = insights.get_vehicle_insight(vid)
            st.session_state["last_insight"] = insight_text

    if "last_insight" in st.session_state:
        st.info(st.session_state["last_insight"])


# ---------------------------------------------------------------------------
# Page: Scan Receipt
# ---------------------------------------------------------------------------
def page_scan_receipt():
    """Upload receipt image, extract text, parse, validate, and save."""
    st.header("Scan Receipt")

    vid = require_vehicle()
    if not vid:
        return

    uploaded = st.file_uploader(
        "Upload receipt image",
        type=["png", "jpg", "jpeg"],
        key="receipt_uploader",
    )

    # Clear previous scan when a new file is uploaded.
    if uploaded is not None:
        if st.session_state.get("_scan_file_name") != uploaded.name:
            st.session_state["_scan_file_name"] = uploaded.name
            st.session_state.pop("_scan_ocr", None)
            st.session_state.pop("_scan_parsed", None)
            st.session_state.pop("_scan_validated", None)

    # --- Step 1: Upload and extract text ---
    if uploaded is not None and "_scan_ocr" not in st.session_state:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name

        with st.spinner("Extracting text from image..."):
            ocr_result = receipt_scanner.extract_text_from_image(tmp_path)

        st.session_state["_scan_ocr"] = ocr_result

        if "error" in ocr_result:
            st.error(f"OCR failed: {ocr_result['error']}")
            return

        with st.spinner("Parsing receipt with AI..."):
            parsed = receipt_scanner.parse_receipt_text(ocr_result["raw_text"])
            st.session_state["_scan_parsed"] = parsed

        if "error" in parsed:
            st.error(f"AI parsing failed: {parsed['error']}")
            return

        validated = validation.validate_receipt(parsed)
        st.session_state["_scan_validated"] = validated

    # --- Step 2: Show editable fields ---
    if "_scan_validated" in st.session_state:
        validated = st.session_state["_scan_validated"]
        data = validated.get("data", {})

        st.success("Receipt parsed successfully! Review and edit below.")

        with st.form("scan_form"):
            st.subheader("Review Extracted Data")

            rec_type = st.selectbox(
                "Record Type",
                ["fuel", "maintenance", "insurance", "unknown"],
                index=["fuel", "maintenance", "insurance", "unknown"].index(
                    data.get("record_type", "fuel")
                ),
            )
            rec_date = st.date_input("Date", value=date.today())
            amount = st.number_input(
                "Amount (PKR)",
                min_value=0.0,
                value=float(data.get("amount_pkr") or 0),
                step=100.0,
            )
            liters = st.number_input(
                "Liters",
                min_value=0.0,
                value=float(data.get("liters") or 0),
                step=0.5,
            )
            odo = st.number_input(
                "Odometer (km)",
                min_value=0,
                value=int(data.get("odometer_km") or 0),
                step=10,
            )
            vendor = st.text_input("Vendor", value=data.get("vendor_name") or "")
            desc = st.text_area("Description", value=data.get("description") or "")

            if st.form_submit_button("Save Expense", use_container_width=True):
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
                            st.session_state.get("_scan_parsed", {})
                        ),
                    )
                    st.success("Expense saved successfully!")
                    st.session_state.pop("_scan_validated", None)
                    st.session_state.pop("_scan_parsed", None)
                    st.session_state.pop("_scan_ocr", None)
                    st.session_state.pop("_scan_file_name", None)
                except Exception as exc:
                    st.error(f"Failed to save: {exc}")

    # --- Show raw OCR text ---
    if "_scan_ocr" in st.session_state:
        with st.expander("Raw OCR Text"):
            st.text(st.session_state["_scan_ocr"].get("raw_text", ""))


# ---------------------------------------------------------------------------
# Page: Add Expense
# ---------------------------------------------------------------------------
def page_add_expense():
    """Manually add fuel, maintenance, or insurance expense."""
    st.header("Add Expense")

    vid = require_vehicle()
    if not vid:
        return

    with st.form("expense_form"):
        rec_type = st.selectbox(
            "Expense Type", ["fuel", "maintenance", "insurance"]
        )
        rec_date = st.date_input("Date", value=date.today())
        amount = st.number_input("Amount (PKR)", min_value=0.0, step=100.0)

        liters = None
        odo = None
        if rec_type == "fuel":
            liters = st.number_input("Liters", min_value=0.0, step=0.5)
            odo = st.number_input("Odometer (km)", min_value=0, step=10)
        elif rec_type == "maintenance":
            odo = st.number_input("Odometer (km)", min_value=0, step=10)

        vendor = st.text_input("Vendor")
        desc = st.text_area("Description")

        if st.form_submit_button("Save Expense", use_container_width=True):
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                db.add_record(
                    vehicle_id=vid,
                    record_type=rec_type,
                    date=rec_date.isoformat(),
                    amount_pkr=amount,
                    liters=liters,
                    odometer_km=odo,
                    vendor_name=vendor or None,
                    description=desc or None,
                    source="manual",
                )
                st.success(f"Saved {rec_type} expense: {fmt_pkr(amount)}")


# ---------------------------------------------------------------------------
# Page: Vehicle Logbook
# ---------------------------------------------------------------------------
def page_logbook():
    """Display searchable, filterable list of all vehicle records."""
    st.header("Vehicle Logbook")

    vid = require_vehicle()
    if not vid:
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search records", key="log_search")
    with col2:
        filter_type = st.selectbox(
            "Filter by type",
            ["All", "fuel", "maintenance", "insurance"],
            key="log_filter",
        )

    records = db.get_records(vid, record_type=None if filter_type == "All" else filter_type)

    if search:
        search_lower = search.lower()
        records = [
            r for r in records
            if search_lower in (r.get("description") or "").lower()
            or search_lower in (r.get("vendor_name") or "").lower()
        ]

    if not records:
        st.info("No records found.")
        return

    for rec in records:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(
                    f"**{rec['record_type'].upper()}** — {rec['date']}"
                )
                details = []
                if rec.get("amount_pkr"):
                    details.append(fmt_pkr(rec["amount_pkr"]))
                if rec.get("odometer_km"):
                    details.append(f"{rec['odometer_km']:,} km")
                if rec.get("liters"):
                    details.append(f"{rec['liters']:.1f} L")
                if rec.get("vendor_name"):
                    details.append(rec["vendor_name"])
                if details:
                    st.caption(" | ".join(details))
                if rec.get("description"):
                    st.caption(rec["description"])
            with col2:
                if st.button("Edit", key=f"edit_{rec['id']}"):
                    st.session_state["editing_id"] = rec["id"]
            with col3:
                if st.button("Delete", key=f"del_{rec['id']}"):
                    db.delete_record(rec["id"])
                    st.rerun()

            # Edit form
            if st.session_state.get("editing_id") == rec["id"]:
                with st.form(f"edit_form_{rec['id']}"):
                    new_amount = st.number_input(
                        "Amount",
                        value=float(rec.get("amount_pkr") or 0),
                        step=100.0,
                    )
                    new_desc = st.text_input(
                        "Description", value=rec.get("description") or ""
                    )
                    new_vendor = st.text_input(
                        "Vendor", value=rec.get("vendor_name") or ""
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save"):
                            db.update_record(
                                rec["id"],
                                amount_pkr=new_amount if new_amount > 0 else None,
                                description=new_desc or None,
                                vendor_name=new_vendor or None,
                            )
                            st.success("Updated!")
                            st.session_state.pop("editing_id", None)
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state.pop("editing_id", None)
                            st.rerun()

            st.divider()


# ---------------------------------------------------------------------------
# Page: Maintenance
# ---------------------------------------------------------------------------
def page_maintenance():
    """Show maintenance status, AI advice, and PDF download."""
    st.header("Maintenance")

    vid = require_vehicle()
    if not vid:
        return

    # --- Status table ---
    st.subheader("Service Status")
    status = maintenance.check_due_maintenance(vid)

    if status:
        import pandas as pd

        df = pd.DataFrame(status)
        df["type"] = df["type"].str.replace("_", " ").str.title()
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No maintenance schedule data.")

    st.divider()

    # --- AI Advice ---
    st.subheader("AI Maintenance Advice")
    if st.button("Get AI Advice", key="ai_advice"):
        with st.spinner("Analyzing maintenance status..."):
            advice = maintenance.get_ai_maintenance_advice(vid)
            st.session_state["last_advice"] = advice

    if "last_advice" in st.session_state:
        st.info(st.session_state["last_advice"])

    st.divider()

    # --- PDF Download ---
    st.subheader("Download Logbook")
    if st.button("Generate PDF", key="gen_pdf"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_path = pdf_report.generate_logbook_pdf(
                    vid, "logbook_report.pdf"
                )
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download PDF",
                        f,
                        file_name="logbook_report.pdf",
                        mime="application/pdf",
                    )
            except Exception as exc:
                st.error(f"Failed to generate PDF: {exc}")


# ---------------------------------------------------------------------------
# Page: Ask SafarSync
# ---------------------------------------------------------------------------
def page_ask():
    """AI chat interface for vehicle-related questions."""
    st.header("Ask SafarSync")

    vid = require_vehicle()
    if not vid:
        return

    question = st.text_input("Ask a question about your vehicle:")

    if st.button("Ask", key="ask_btn") and question:
        # Gather verified facts from Python modules.
        metrics = analytics.get_summary_metrics(vid)
        maint_status = maintenance.check_due_maintenance(vid)
        anomalies_list = anomaly.find_anomalies(vid)

        # Build facts block.
        facts = []
        facts.append(f"Total spending: {fmt_pkr(metrics['total_spend'])}")
        if metrics["fuel_spend"]:
            facts.append(f"Fuel spending: {fmt_pkr(metrics['fuel_spend'])}")
        if metrics["maintenance_spend"]:
            facts.append(f"Maintenance spending: {fmt_pkr(metrics['maintenance_spend'])}")
        if metrics["insurance_spend"]:
            facts.append(f"Insurance spending: {fmt_pkr(metrics['insurance_spend'])}")
        if metrics["total_distance"]:
            facts.append(f"Total distance: {metrics['total_distance']:,} km")
        if metrics["average_fuel_efficiency"]:
            facts.append(f"Average fuel efficiency: {metrics['average_fuel_efficiency']:.1f} km/L")
        if metrics["cost_per_km"]:
            facts.append(f"Cost per km: PKR {metrics['cost_per_km']:.2f}")

        overdue = [s for s in maint_status if s["status"] == "overdue"]
        due_soon = [s for s in maint_status if s["status"] == "due_soon"]
        if overdue:
            names = ", ".join(s["type"].replace("_", " ") for s in overdue)
            facts.append(f"Overdue services: {names}")
        if due_soon:
            names = ", ".join(s["type"].replace("_", " ") for s in due_soon)
            facts.append(f"Services due soon: {names}")
        if not overdue and not due_soon:
            facts.append("All maintenance is up to date.")

        if anomalies_list:
            facts.append("Anomalies detected:")
            for a in anomalies_list[:5]:
                facts.append(f"  - [{a['severity'].upper()}] {a['message']}")
        else:
            facts.append("No anomalies detected.")

        facts_block = "\n".join(facts)

        prompt = (
            "You are SafarSync AI, a helpful vehicle assistant.\n"
            "Below are verified facts about the user's vehicle.\n"
            "Use ONLY these facts. Do NOT invent numbers.\n\n"
            f"{facts_block}\n\n"
            f"User question: {question}\n\n"
            "Answer concisely using only the facts above."
        )

        with st.spinner("Thinking..."):
            try:
                answer = ask_text(prompt, model=_config.QWEN_PLUS_CHARACTER, max_tokens=300)
                st.session_state["last_answer"] = answer
            except PermissionError:
                st.error("Authentication failed. Check API key.")
            except ConnectionError:
                st.error("Cannot reach AI service. Check connection.")
            except TimeoutError:
                st.error("Request timed out. Try again.")
            except RuntimeError as exc:
                st.error(f"AI service error: {exc}")

    if "last_answer" in st.session_state:
        st.divider()
        st.markdown(st.session_state["last_answer"])


# ---------------------------------------------------------------------------
# Page: Manage Vehicles
# ---------------------------------------------------------------------------
def page_manage():
    """Add new vehicles and select active vehicle."""
    st.header("Manage Vehicles")

    # --- Add vehicle ---
    st.subheader("Add Vehicle")
    with st.form("add_vehicle_form"):
        name = st.text_input("Vehicle Name")
        reg = st.text_input("Registration Number")
        if st.form_submit_button("Add Vehicle", use_container_width=True):
            if not name.strip():
                st.error("Vehicle name is required.")
            else:
                new_id = db.add_vehicle(name.strip(), reg.strip())
                st.success(f"Added '{name}'!")
                st.session_state["vehicle_id"] = new_id
                st.rerun()

    st.divider()

    # --- Select vehicle ---
    st.subheader("Select Vehicle")
    vehicles = db.get_vehicles()
    if not vehicles:
        st.info("No vehicles. Add one above.")
        return

    for v in vehicles:
        col1, col2 = st.columns([3, 1])
        with col1:
            label = v["name"]
            if v.get("registration_number"):
                label += f" ({v['registration_number']})"
            st.markdown(f"**{label}**")
        with col2:
            is_active = st.session_state.get("vehicle_id") == v["id"]
            if st.button(
                "Selected" if is_active else "Select",
                key=f"sel_{v['id']}",
                disabled=is_active,
                use_container_width=True,
            ):
                st.session_state["vehicle_id"] = v["id"]
                st.rerun()


# ---------------------------------------------------------------------------
# Main application.
# ---------------------------------------------------------------------------
def main():
    """Initialize app, render sidebar, and run navigation."""
    st.set_page_config(page_title="SafarSync AI", page_icon="", layout="wide")

    # Check if modules loaded successfully.
    if not _modules_loaded:
        st.error("Configuration Error")
        st.write("Required secrets are missing.")
        st.code(_config_error)
        st.write("Add them to `.env` (local) or Streamlit Cloud secrets.")
        return

    # Initialize database.
    db.init_db()

    # Auto-seed demo data if no vehicles exist.
    vehicles = db.get_vehicles()
    if not vehicles:
        demo_data.seed_demo_data()
        vehicles = db.get_vehicles()

    # --- Sidebar: Vehicle selector ---
    with st.sidebar:
        st.title("SafarSync AI")
        st.caption("Vehicle Expense Tracker")
        st.divider()

        st.subheader("Active Vehicle")
        if vehicles:
            options = {v["id"]: v["name"] for v in vehicles}
            current_id = st.session_state.get("vehicle_id")
            if current_id not in options:
                current_id = list(options.keys())[0]
                st.session_state["vehicle_id"] = current_id

            selected = st.selectbox(
                "Select Vehicle",
                options=list(options.keys()),
                format_func=lambda x: options[x],
                index=list(options.keys()).index(current_id),
                key="vehicle_selector",
                label_visibility="collapsed",
            )
            if selected != st.session_state.get("vehicle_id"):
                st.session_state["vehicle_id"] = selected
                st.rerun()

            # Show vehicle info.
            current_vehicle = next(
                (v for v in vehicles if v["id"] == current_id), None
            )
            if current_vehicle:
                st.caption(f"Reg: {current_vehicle.get('registration_number', '—')}")
        else:
            st.warning("No vehicles. Go to Manage Vehicles to add one.")

    # --- Navigation ---
    pages = [
        st.Page(page_dashboard, title="Dashboard", icon="📊"),
        st.Page(page_scan_receipt, title="Scan Receipt", icon="📷"),
        st.Page(page_add_expense, title="Add Expense", icon="➕"),
        st.Page(page_logbook, title="Vehicle Logbook", icon="📖"),
        st.Page(page_maintenance, title="Maintenance", icon="🔧"),
        st.Page(page_ask, title="Ask SafarSync", icon="💬"),
        st.Page(page_manage, title="Manage Vehicles", icon="🚗"),
    ]

    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
