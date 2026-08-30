"""Ask SafarSync AI page — conversational Q&A about vehicle costs and history."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

import database as db
import analytics
import maintenance
import anomaly
import config as _config
from ai_client import ask_text

from database import get_db_version

from ui_helpers import esc, fmt_pkr, require_vehicle, page_hero, section

_SYSTEM_PROMPT = (
    "You are SafarSync AI, a friendly and knowledgeable vehicle expense advisor. "
    "You help users understand their car spending, fuel efficiency, and maintenance needs.\n\n"
    "STRICT RULES:\n"
    "- Answer ONLY from the VERIFIED FACTS provided in the user message.\n"
    "- NEVER invent numbers, costs, dates, or statistics.\n"
    "- If the data doesn't contain enough information to answer, say so honestly.\n"
    "- Keep answers concise: 2-4 sentences maximum.\n"
    "- Use specific numbers from the data (PKR amounts, km values, dates).\n"
    "- When giving advice, be practical and actionable.\n"
    "- You are context-bounded to this user's vehicle data only."
)


def render() -> None:
    page_hero("Ask SafarSync", "Ask questions about your vehicle's costs and history", "\U0001F4AC")

    vid = require_vehicle()
    if not vid:
        return

    # Chat history display
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if st.session_state["chat_history"]:
        for entry in st.session_state["chat_history"]:
            # User bubble
            st.markdown(f"""
            <div style="display:flex;justify-content:flex-end;margin-bottom:1rem;">
                <div style="background:#2563EB;
                            border-radius:12px 0 12px 12px;padding:1rem 1.5rem;max-width:70%;
                            color:#ffffff;font-size:0.95rem;">
                    {esc(entry['question'])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            # AI bubble
            st.markdown(f"""
            <div class="chat-bubble fade-in" style="max-width:80%;margin-bottom:1.5rem;">
                <div style="font-size:0.75rem;color:#0891B2;font-weight:800;
                            text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem;">
                    SafarSync AI
                </div>
                {esc(entry['answer'])}
            </div>
            """, unsafe_allow_html=True)

        col_clr, _ = st.columns([1, 5])
        with col_clr:
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("Clear Chat", key="clear_chat"):
                st.session_state["chat_history"] = []
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Check for prefilled question from suggestion buttons
    prefill = st.session_state.pop("_ask_prefill", None)

    # Input
    question = st.text_input("",
        placeholder="e.g. How much did I spend on fuel last month?",
        key="ask_input", label_visibility="collapsed",
        value=prefill if prefill else None)

    if st.button("Ask  \u27A4", key="ask_btn") and question.strip():
        # Build enriched context scoped to the last 6 months
        six_months_ago = (date.today() - timedelta(days=180)).isoformat()
        recent_records = db.get_records(vid, start_date=six_months_ago)

        metrics = analytics.get_summary_metrics(vid, db_version=get_db_version())
        maint_status = maintenance.check_due_maintenance(vid, db_version=get_db_version())
        anomalies_list = anomaly.find_anomalies(vid, db_version=get_db_version())

        facts = [f"Total spending: {fmt_pkr(metrics['total_spend'])}"]
        if metrics["fuel_spend"] is not None:
            facts.append(f"Fuel spending: {fmt_pkr(metrics['fuel_spend'])}")
        if metrics["maintenance_spend"] is not None:
            facts.append(f"Maintenance spending: {fmt_pkr(metrics['maintenance_spend'])}")
        if metrics["insurance_spend"] is not None:
            facts.append(f"Insurance spending: {fmt_pkr(metrics['insurance_spend'])}")
        if metrics["total_distance"] is not None:
            facts.append(f"Total distance tracked: {metrics['total_distance']:,} km")
        if metrics["average_fuel_efficiency"] is not None:
            facts.append(f"Average fuel efficiency: {metrics['average_fuel_efficiency']:.1f} km/L")
        if metrics["cost_per_km"] is not None:
            facts.append(f"Cost per km: PKR {metrics['cost_per_km']:.2f}")

        overdue = [s for s in maint_status if s["status"] == "overdue"]
        due_soon = [s for s in maint_status if s["status"] == "due_soon"]
        if overdue:
            facts.append(f"Overdue services: {', '.join(s['type'].replace('_', ' ') for s in overdue)}")
        if due_soon:
            facts.append(f"Services due soon: {', '.join(s['type'].replace('_', ' ') for s in due_soon)}")
        if not overdue and not due_soon:
            facts.append("All maintenance is up to date.")
        if anomalies_list:
            for a in anomalies_list[:5]:
                facts.append(f"Anomaly [{a['severity'].upper()}]: {a['message']}")
        else:
            facts.append("No spending anomalies detected.")

        # Last 10 records as specific data points
        if recent_records:
            facts.append("\nRecent records (last 6 months):")
            for rec in recent_records[:10]:
                r_date = rec.get("date", "N/A")
                r_type = rec.get("record_type", "unknown")
                r_amount = rec.get("amount_pkr")
                r_desc = rec.get("description") or "—"
                amount_str = f"PKR {r_amount:,.0f}" if r_amount is not None else "N/A"
                facts.append(f"  - {r_date} | {r_type} | {amount_str} | {r_desc}")

        # Monthly spending breakdown
        monthly = analytics.monthly_spending_summary(vid, db_version=get_db_version())
        if monthly:
            facts.append("\nMonthly spending breakdown:")
            for row in monthly[:12]:
                facts.append(
                    f"  - {row['month']} | {row['record_type']} | "
                    f"PKR {row['total_amount']:,.0f} ({row['count']} records)"
                )

        facts_block = "\n".join(facts)
        user_msg = f"VERIFIED FACTS:\n{facts_block}\n\nUSER QUESTION: {question.strip()}"

        with st.spinner("Thinking..."):
            try:
                answer = ask_text(
                    user_msg,
                    model=_config.QWEN_PLUS_CHARACTER,
                    max_tokens=200,
                    system_message=_SYSTEM_PROMPT,
                )
                st.session_state["chat_history"].append({
                    "question": question.strip(),
                    "answer": answer,
                })
                st.rerun()
            except PermissionError:
                st.error("Authentication failed. Check your API key.")
            except ConnectionError:
                st.error("Cannot reach the AI service. Check your connection.")
            except TimeoutError:
                st.error("Request timed out. Please try again.")
            except RuntimeError as exc:
                st.error(f"Something went wrong: {exc}")
    elif not st.session_state["chat_history"]:
        # Suggested questions as clickable buttons
        section("TRY ASKING")
        suggestions = [
            "What's my average monthly fuel cost?",
            "Which maintenance is overdue?",
            "How can I improve my fuel efficiency?",
            "Give me a summary of my car expenses.",
        ]
        cols = st.columns(2)
        for i, q in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    st.session_state["_ask_prefill"] = q
                    st.rerun()
