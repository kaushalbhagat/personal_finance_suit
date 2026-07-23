from decimal import Decimal
import streamlit as st
import pandas as pd
from database.setup import get_db
from database.portfolio.models import Account
from sqlmodel import select
import yfinance as yf
from datetime import date, timedelta

from util.portfolio.current_holdings import load_current_holdings
from util.portfolio.financial_data import load_financial_data


st.set_page_config(page_title="Personal Budget Dashboard", layout="wide")

# Helper to manually clear form state ONLY on successful submissions
def clear_form_state():
    st.session_state["form_symbol"] = ""
    st.session_state["form_quantity"] = 0.0001
    st.session_state["form_price"] = 0.01

with get_db() as session:
    tx_df, acct_df = load_financial_data(session)
    holdings_df = load_current_holdings(session)

    # --- CURRENT HOLDINGS EXPANDERS ---
    st.subheader("📊 Current Equity Holdings (by Account)")
    if not holdings_df.empty:
        holdings_df = holdings_df.sort_values(by=["Owner", "Institute", "Account", "Ticker"], ascending=[True, True, True, True])
        grouped = holdings_df.groupby(["Owner", "Institute", "Account"])
        
        for (owner, institute, account), group_data in grouped:
            total_account_equity = group_data["Mkt Val"].sum()
            total_account_cost = group_data["Cost Basis"].sum()
            account_gain_loss = group_data["Gain/Loss $"].sum()
            asset_count = len(group_data)
            
            header_label = f"👤 {owner}  |  🏦 {account}  |  {institute} |Total Value: ${total_account_equity:,.2f}  ({asset_count} Assets)"
            
            with st.expander(header_label, expanded=False):
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.caption(f"Account Cost Basis: ${total_account_cost:,.2f}")
                
                pnl_pct = (account_gain_loss / total_account_cost * 100) if total_account_cost > 0 else 0.0
                metric_col2.markdown(f"<p style='text-align: right; margin: 0; color: {'#2ecc71' if account_gain_loss >= 0 else '#e74c3c'}; font-weight: bold;'>Unrealized Return: ${account_gain_loss:,.2f} ({pnl_pct:.2f}%)</p>", unsafe_allow_html=True)
                
                display_columns = ["Ticker", "Qty", "Price", "Price Chng $", "Price Chng %", "Mkt Val", "Day Chng $", "Day Chng %", "Cost Basis", "Gain/Loss $", "Gain/Loss %"]
                
                def color_returns(val):
                    if isinstance(val, (int, float)) and val != 0:
                        return 'color: #2ecc71; font-weight: bold;' if val > 0 else 'color: #e74c3c; font-weight: bold;'
                    return ''

                styled_df = group_data[display_columns].style.map(color_returns, subset=["Price Chng $", "Price Chng %", "Day Chng $", "Day Chng %", "Gain/Loss $", "Gain/Loss %"])
                
                st.dataframe(
                    styled_df,
                    column_config={
                        "Ticker": "Asset Ticker",
                        "Qty": st.column_config.NumberColumn("Qty", format="%.4f"),
                        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                        "Price Chng $": st.column_config.NumberColumn("Price Chng $", format="$%.2f"),
                        "Price Chng %": st.column_config.NumberColumn("Price Chng %", format="%.2f%%"),
                        "Mkt Val": st.column_config.NumberColumn("Mkt Val", format="$%.2f"),
                        "Day Chng $": st.column_config.NumberColumn("Day Chng $", format="$%.2f"),
                        "Day Chng %": st.column_config.NumberColumn("Day Chng %", format="%.2f%%"),
                        "Cost Basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f"),
                        "Gain/Loss $": st.column_config.NumberColumn("Gain/Loss $", format="$%.2f"),
                        "Gain/Loss %": st.column_config.NumberColumn("Gain/Loss %", format="%.2f%%"),
                    },
                    use_container_width=True, hide_index=True
                )
    else:
        st.info("You do not currently hold any open equity positions.")