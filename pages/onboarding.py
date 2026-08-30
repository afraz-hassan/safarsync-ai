"""First-time user onboarding page."""

import streamlit as st
import database as db


def render():
    """Render the first-time user onboarding experience."""
    st.markdown(
        '<div class="onboarding-title">Welcome to SafarSync AI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="onboarding-subtitle">'
        "Let\u2019s get you started \u2014 register your vehicle to begin tracking expenses, "
        "fuel efficiency, and maintenance schedules with AI-powered insights."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("onboarding_form"):
        st.markdown(
            '<div style="font-size:0.75rem;font-weight:800;color:var(--ss-text-muted);'
            'text-transform:uppercase;letter-spacing:0.14em;margin-bottom:0.8rem;">'
            "Vehicle Details</div>",
            unsafe_allow_html=True,
        )

        name = st.text_input(
            "Vehicle Name *",
            placeholder="e.g. My Toyota Corolla",
            help="A friendly name for your vehicle (required)",
        )

        col_make, col_model = st.columns(2)
        with col_make:
            make = st.text_input("Make", placeholder="e.g. Toyota")
        with col_model:
            model = st.text_input("Model", placeholder="e.g. Corolla")

        col_year, col_mileage = st.columns(2)
        with col_year:
            year = st.number_input(
                "Year", min_value=1990, max_value=2030, value=2024, step=1
            )
        with col_mileage:
            mileage = st.number_input(
                "Initial Mileage (km)", min_value=0, value=0, step=100
            )

        reg = st.text_input(
            "Registration Number",
            placeholder="e.g. ABC-1234",
        )

        submitted = st.form_submit_button(
            "Add Vehicle & Get Started",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not name or not name.strip():
                st.error("Please enter a vehicle name.")
            else:
                vehicle_id = db.add_vehicle(
                    name=name.strip(),
                    registration_number=reg.strip(),
                    make=make.strip(),
                    model=model.strip(),
                    year=year,
                    initial_mileage=int(mileage),
                )
                st.session_state["vehicle_id"] = vehicle_id
                st.success(
                    f"Vehicle '{name.strip()}' added successfully! Redirecting\u2026"
                )
                st.rerun()

    st.divider()
    st.caption("Or try with sample data:")
    if st.button("\U0001f697 Load Demo Data", use_container_width=True):
        import demo_data

        demo_data.seed_demo_data()
        vehicles = db.get_vehicles()
        if vehicles:
            st.session_state["vehicle_id"] = vehicles[0]["id"]
        st.rerun()
