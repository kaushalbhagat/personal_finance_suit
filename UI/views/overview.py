import streamlit as st
from database.setup import get_db
import util.budget.services as services
from datetime import date
import util.ux_components as ux_components
from util.portfolio.current_holdings import load_portfolio_values


INCOME_CATEGORY_ID = 16


st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

today = date.today()
month_start_date = today.replace(day=1)
year_start_date = date(today.year, 1, 1)

col_1, col_2 = st.columns([1, 1])
with col_1:
    with st.container(border=True):
        df_category, cat_total = services.fetch_totals_breakdown(
            level="category", start_date=month_start_date, end_date=today, report_type="All", bank_name="All"
        )
        title_col, btn_col = st.columns([15,2], gap="small")
        with title_col:
            st.markdown(f"#### Grand Total Spending: `${cat_total:,.2f}`")
        with btn_col:
            if st.button(":material/keyboard_double_arrow_right:", key="spending_nav_chevron"):
                st.switch_page("views/budget/expense_dashboard.py")
        ux_components.render_allocation_pie(df_category.head(10), "total_amount", "category_name")
with col_2:
    with st.container(border=True):
        df_sub, raw_grand_total = services.fetch_totals_breakdown(
            level="subcategory", category_id=INCOME_CATEGORY_ID, exclude_from_reporting=True, start_date=today.replace(day=1), end_date=today, bank_name="All", report_type="All"
        )
        if not df_sub.empty and "total_amount" in df_sub.columns:
            df_sub["total_amount"] = df_sub["total_amount"] * -1
        income_grand_total = raw_grand_total * -1
        title_col, btn_col = st.columns([15,2], gap="small")
        with title_col:
            st.markdown(f"#### Total Income Earned: `${income_grand_total:,.2f}`")
        with btn_col:
            if st.button(":material/keyboard_double_arrow_right:", key="income_nav_chevron"):
                st.switch_page("views/budget/income_dashboard.py")
        ux_components.render_allocation_pie(df_sub.tail(10), "total_amount", "subcategory_name")

with st.container(border=True):
    ux_components.render_income_expense_timeline_chart("Combined", year_start_date, today)

with st.container(border=True):
    with get_db() as session:
        total_val, cash_bal, day_chng_dollar, day_chng_pct, unrealized_pnl, unrealized_pnl_pct = load_portfolio_values(session)
        title_col, btn_col = st.columns([16,1], gap="small")
        with title_col:
            st.subheader("Investment Portfolio Snapshot")
        with btn_col:
            if st.button(":material/keyboard_double_arrow_right:", key="portfolio_nav_chevron"):
                st.switch_page("views/portfolio/snapshot.py")        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Portfolio Value", f"${total_val:,.2f}")
        col2.metric("Available Cash Balance", f"${cash_bal:,.2f}")
        col3.metric(label="Today's Change", value=f"${day_chng_dollar:+,.2f}", delta=f"{day_chng_pct:+.2f}%" if day_chng_dollar != 0 else None)
        col4.metric(label="Total Unrealized PnL", value=f"${unrealized_pnl:,.2f}", delta=f"{unrealized_pnl_pct:+.2f}%" if unrealized_pnl_pct != 0 else None)
