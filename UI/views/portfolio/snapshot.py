from decimal import Decimal
import streamlit as st
import pandas as pd
from database.setup import get_db
from database.portfolio.models import Account
from sqlmodel import select
import yfinance as yf
from datetime import date, timedelta
import util.ux_components as ux_components

from util.portfolio.current_holdings import load_portfolio_values
from util.portfolio.historical_timeline import load_historical_timeline
# from util.portfolio.daily_snapshots import refresh_daily_snapshot, SnapshotException

st.set_page_config(page_title="Personal Budget Dashboard", layout="wide")

# Helper to manually clear form state ONLY on successful submissions
def clear_form_state():
    st.session_state["form_symbol"] = ""
    st.session_state["form_quantity"] = 0.0001
    st.session_state["form_price"] = 0.01

with get_db() as session:
    ux_components.build_portfolio_performance_chart(session)
    # holdings_df = load_current_holdings(session)
    total_val, cash_bal, day_chng_dollar, day_chng_pct, unrealized_pnl, unrealized_pnl_pct = load_portfolio_values(session)

    # # --- METRIC COMPUTATIONS ---
    # total_val = 0.0
    # cash_bal = 0.0
    # day_chng_dollar = 0.0
    # day_chng_pct = 0.0
    # unrealized_pnl = 0.0
    # unrealized_pnl_pct = 0.0

    # if not holdings_df.empty:
    #     total_val = float(holdings_df["Mkt Val"].sum())
    #     day_chng_dollar = float(holdings_df["Day Chng $"].sum())
    #     unrealized_pnl = float(holdings_df["Gain/Loss $"].sum())
        
    #     denominator = total_val - unrealized_pnl
    #     if denominator > 0:
    #         unrealized_pnl_pct = unrealized_pnl * 100 / denominator
        
    #     prev_total_val = total_val - day_chng_dollar
    #     if prev_total_val > 0:
    #         day_chng_pct = (day_chng_dollar / prev_total_val) * 100
        
    #     cash_rows = holdings_df[holdings_df["Ticker"] == "CASH"]
    #     if not cash_rows.empty:
    #         cash_bal = float(cash_rows["Mkt Val"].sum())

    snap_head_col, snap_btn_col = st.columns([4, 1], vertical_alignment="bottom")

    with snap_head_col:
        st.subheader("Investment Portfolio Snapshot")

    with snap_btn_col:
        if st.button("🔄 Refresh Live Prices", use_container_width=True, help="Fetch fresh market data and update the on-screen metrics and tables"):
            st.toast("Fetching latest market prices...", icon="📥")
            st.rerun()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Portfolio Value", f"${total_val:,.2f}")
    col2.metric("Available Cash Balance", f"${cash_bal:,.2f}")
    col3.metric(label="Today's Change", value=f"${day_chng_dollar:+,.2f}", delta=f"{day_chng_pct:+.2f}%" if day_chng_dollar != 0 else None)
    col4.metric(label="Total Unrealized PnL", value=f"${unrealized_pnl:,.2f}", delta=f"{unrealized_pnl_pct:+.2f}%" if unrealized_pnl_pct != 0 else None)
