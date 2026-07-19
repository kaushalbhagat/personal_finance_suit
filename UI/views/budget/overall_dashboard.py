# views/overall_dashboard.py
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
import util.budget.services as services
import util.ux_components as ux_components

INCOME_CATEGORY_ID = 16

# 1. Render filters once at the top of the page (unique key prefix prevents state collisions)
start_date, end_date, scope, bank = ux_components.render_global_filters(key_prefix="overall_dashboard")
# Space spacing spacer
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
# 2. Use those values for the chart
ux_components.render_income_expense_timeline_chart(scope, start_date, end_date)

st.markdown("<br><hr style='border-top: 1px dashed #bbb;'><br>", unsafe_allow_html=True)

cfg = ux_components.SCOPE_MATRIX[scope]
# Fetch Side-by-Side Allocation Metrics via central component helper
df_income, df_expense = services.fetch_totals_breakdown(
    level="subcategory", category_id=INCOME_CATEGORY_ID, exclude_from_reporting=True, start_date=start_date, end_date=end_date, report_type=cfg["report_type"]
)
df_expense_macro, _ = services.fetch_totals_breakdown(
    level="category", start_date=start_date, end_date=end_date, report_type=cfg["report_type"]
)

if not df_income.empty and "total_amount" in df_income.columns:
    df_income["total_amount"] = df_income["total_amount"] * -1

if not df_expense_macro.empty and "category_name" in df_expense_macro.columns:
    df_expense_macro = df_expense_macro[df_expense_macro["category_name"].str.lower() != "income"]

# Render Side-by-Side Allocation Charts via central module functions
col_left, col_right = st.columns([1, 1])
with col_left:
    st.markdown(f"#### 🟢 {cfg['pie_label']} Revenue Allocation")
    ux_components.render_allocation_pie(df_income.tail(10), "total_amount", "subcategory_name", hole=0.4, color_sequence=px.colors.sequential.Greens_r)
with col_right:
    st.markdown(f"#### 🔴 {cfg['pie_label']} Spending Breakdown")
    ux_components.render_allocation_pie(df_expense_macro.head(10), "total_amount", "category_name", hole=0.4, color_sequence=px.colors.sequential.Oranges_r)