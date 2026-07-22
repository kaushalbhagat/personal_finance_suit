import streamlit as st
import pandas as pd
from decimal import Decimal
from sqlmodel import Session
from database.paycheck.models import Paycheck, PaycheckLineItem
from util.paycheck.details import get_all_paychecks
from database.setup import get_paycheck_db

def to_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val))

def sub_metric(label: str, value: str):
    st.markdown(
        f"""
        <div style="padding: 10px; border: 2px solid #363945; border-radius: 6px; text-align: center; box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.4);">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase;">{label}</div>
            <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_paychecks_page(session: Session):
    # 1. Fetch All Paychecks
    all_paychecks = get_all_paychecks(session)

    if not all_paychecks:
        st.info("No paychecks recorded yet. Add your first paystub to see details.")
        return

    # 2. Left / Right Master-Detail Columns
    left_col, right_col = st.columns([1, 4])

    with left_col:
        st.subheader("Paystub History")
        
        # Prepare data for selection table
        history_df = pd.DataFrame([
            {
                "ID": p.id,
                "Date": p.pay_date.strftime("%Y-%m-%d"),
                "Net Pay": f"${float(p.net_pay):,.2f}"
            }
            for p in all_paychecks
        ])

        # Interactive row selection
        selected_paycheck_id = st.selectbox(
            "Select Paystub Date",
            options=[p.id for p in all_paychecks],
            format_func=lambda pid: next(
                f"{p.pay_date.strftime('%b %d, %Y')} — ${p.net_pay:,.2f}" 
                for p in all_paychecks if p.id == pid
            )
        )

    # 3. Selected Paycheck Inspection
    with right_col:
        selected_paycheck = next(p for p in all_paychecks if p.id == selected_paycheck_id)
        
        st.subheader(f"Details for Paystub ({selected_paycheck.pay_date.strftime('%B %d, %Y')})")
        
        # Group line items by Category
        category_map = {}
        for item in selected_paycheck.items:
            category_map.setdefault(item.category, []).append(item)

        gross_pay = sum(to_decimal(i.amount) for i in category_map.get("Income", []))
        total_taxes = sum(to_decimal(i.amount) for i in category_map.get("Taxes", []))
        total_rsu = sum(to_decimal(i.amount) for i in category_map.get("RSU", []))
        total_deductions = sum(
            to_decimal(i.amount) 
            for i in selected_paycheck.items 
            if i.category in ("Pre-Tax Benefits", "Post-Tax Benefits")
        )
        
        # Display Metric Bar
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1: sub_metric("Gross Income", f"${gross_pay:,.2f}")
        with m2: sub_metric("Total Taxes", f"${total_taxes:,.2f}")
        with m3: sub_metric("Total Deductions", f"${total_deductions:,.2f}")
        with m4: sub_metric("RSU", f"${total_rsu:,.2f}")
        with m5: sub_metric("Net Pay", f"${selected_paycheck.net_pay:,.2f}")

        st.divider()

        # Render Grouped Line Items
        for category_name, items in category_map.items():
            with st.expander(f"📌 **{category_name}**", expanded=True):
                item_data = [
                    {"Description": item.name, "Amount": f"${item.amount:,.2f}"} 
                    for item in items
                ]
                st.table(pd.DataFrame(item_data))

with get_paycheck_db() as session:
    render_paychecks_page(session)