import streamlit as st

from util import ux_components
from database.setup import get_paycheck_db
from util.cashflow import gather_consolidated_data


import streamlit as st
import pandas as pd
from decimal import Decimal

def to_decimal(val) -> Decimal:
    """Safely convert float, int, str, or Decimal to Decimal."""
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val))

def render_cashflow_ui(cashflow: dict):
    # --- STEP 1: Normalize and Calculate Summaries Safely ---
    salary_rsu_bonus = to_decimal(cashflow["Income"].get("Salary/Bonus/RSU", 0))
    business_inc = to_decimal(cashflow["Income"].get("Business", 0))
    total_income = salary_rsu_bonus + business_inc

    total_taxes = to_decimal(cashflow.get("Taxes", 0))
    total_deductions = to_decimal(cashflow.get("Deductions", 0))
    total_401k = to_decimal(cashflow.get("401K", 0))

    rsu_savings = to_decimal(cashflow["Savings"].get("RSU", 0))
    other_savings = to_decimal(cashflow["Savings"].get("Other", 0))
    total_savings = total_401k + rsu_savings + other_savings

    personal_exp = to_decimal(cashflow["Expenses"].get("Personal", 0))
    business_exp = to_decimal(cashflow["Expenses"].get("Business", 0))
    total_expenses = personal_exp + business_exp

    st.title("📊 Cash Flow Report")
    st.caption("Consolidated Personal & Business Financial Summary")

    # --- STEP 2: Top KPI Metric Cards ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Income", f"${total_income:,.2f}")
    with col2:
        st.metric("Taxes & Deductions", f"${(total_taxes + total_deductions):,.2f}")
    with col3:
        st.metric("Total Savings & 401K", f"${total_savings:,.2f}")
    with col4:
        st.metric("TotalExpenses", f"${total_expenses:,.2f}")

    st.divider()

    # --- STEP 3: Two-Column Detailed Breakdown ---
    col_left, col_right = st.columns(2)

    # LEFT COLUMN: Income & Savings
    with col_left:
        st.subheader("💵 Inflow & Wealth Building")

        with st.expander("📥 **Income Breakdown**", expanded=True):
            st.write(f"**Salary / Bonus / RSU:** ${salary_rsu_bonus:,.2f}")
            st.write(f"**Business Income:** ${business_inc:,.2f}")
            st.markdown(f"**Total Income:** `${total_income:,.2f}`")

        with st.expander("🏦 **Savings & Investments**", expanded=True):
            st.write(f"**401K (Paycheck):** ${total_401k:,.2f}")
            st.write(f"**RSU Savings:** ${rsu_savings:,.2f}")
            st.write(f"**Other Savings (Budget):** ${other_savings:,.2f}")
            st.markdown(f"**Total Savings:** `${total_savings:,.2f}`")

    # RIGHT COLUMN: Taxes, Deductions & Expenses
    with col_right:
        st.subheader("💸 Outflows & Expenses")

        with st.expander("🏛️ **Taxes & Paycheck Deductions**", expanded=True):
            st.write(f"**Taxes:** ${total_taxes:,.2f}")
            st.write(f"**Pre/Post-Tax Benefits:** ${total_deductions:,.2f}")
            st.markdown(f"**Total Tax/Deductions:** `${(total_taxes + total_deductions):,.2f}`")

        with st.expander("💳 **Living & Business Expenses**", expanded=True):
            st.write(f"**Personal Expenses:** ${personal_exp:,.2f}")
            st.write(f"**Business Expenses:** ${business_exp:,.2f}")
            st.markdown(f"**Total Expenses:** `${total_expenses:,.2f}`")

with get_paycheck_db() as session:
    start_date, end_date, selected_scope, selected_bank = ux_components.render_global_filters(key_prefix="paycheck_summary", show_scope_picker=False)
    cashflow = gather_consolidated_data(session, start_date, end_date)
    # st.header(cashflow)
    render_cashflow_ui(cashflow)