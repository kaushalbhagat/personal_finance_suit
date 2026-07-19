from decimal import Decimal
import streamlit as st
import pandas as pd
from database.setup import get_db
from database.models import Account
from sqlmodel import select
import yfinance as yf
from datetime import date, timedelta

from util.portfolio.financial_data import load_financial_data
from util.portfolio.transactions import execute_equity_transaction, InsufficientFundsError
from util.portfolio.split import execute_stock_split
from util.portfolio.cash import deposit_cash, withdraw_cash

st.set_page_config(page_title="Personal Budget Dashboard", layout="wide")

# Helper to manually clear form state ONLY on successful submissions
def clear_form_state():
    st.session_state["form_symbol"] = ""
    st.session_state["form_quantity"] = 0.0001
    st.session_state["form_price"] = 0.01

with get_db() as session:
    tx_df, acct_df = load_financial_data(session)

    # --- TRANSACTION LOGGER & RECENT LEDGER ---
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("Log New Transaction")
        
        account_options = {}
        accounts = session.scalars(select(Account)).all()
        for acc in accounts:
            label = f"{acc.owner} - {acc.account_type.value} (${float(acc.current_cash):,.2f})"
            account_options[label] = acc.id
            
        if not account_options:
            st.warning("Please configure accounts in your database first.")
        else:
            # We omit clear_on_submit=True to manage state manually
            with st.form("transaction_form"):
                date_input = st.date_input("Date", key="form_date")
                selected_acct_label = st.selectbox("Account", list(account_options.keys()), key="form_account")
                symbol_input = st.text_input("Symbol", key="form_symbol").upper().strip()
                
                quantity_input = st.number_input("Quantity", min_value=0.0001, step=1.0, format="%.4f", key="form_quantity")
                price_input = st.number_input("Price", min_value=0.01, step=0.01, format="%.2f", key="form_price")
                action_input = st.selectbox("Action", ["Buy", "Sell", "Deposit", "Withdraw", "Split"], key="form_action")
                
                estimated_total = quantity_input * price_input
                st.caption(f"Estimated Total: **${estimated_total:,.2f}**")
                
                submitted = st.form_submit_button("Submit Transaction")
                
                if submitted:
                    if not symbol_input:
                        st.error("Please provide an asset ticker symbol.")
                    else:
                        target_account_id = account_options[selected_acct_label]
                        try:
                            if action_input == "Split":
                                execute_stock_split(session, symbol_input, quantity_input, date_input)
                                st.success(f"Split applied successfully across all accounts")
                            elif action_input in {"Buy", "Sell"}:
                                execute_equity_transaction(date_input, symbol_input, quantity_input, price_input, action_input, target_account_id, session)
                                st.success(f"Successfully entered Trade")
                            elif action_input == "Deposit":
                                deposit_cash(date_input, quantity_input, target_account_id, session)
                            elif action_input == "Withdraw":
                                withdraw_cash(date_input, quantity_input, target_account_id, session)
                            
                            # Clean state and reload ONLY if execution succeeded without throwing
                            clear_form_state()
                            st.rerun()
                        except InsufficientFundsError as e:
                            # State is preserved automatically; show the error banner
                            st.error(e)

    with right_col:
        st.subheader("Recent Ledger Entries")
        if not tx_df.empty:
            tx_df['total_value'] = tx_df['quantity'] * tx_df['price_per_share']
            display_df = tx_df[['transaction_date', 'ticker', 'transaction_type', 'quantity', 'price_per_share', 'total_value']].sort_values(by='transaction_date', ascending=False)
            
            if 'transaction_type' in display_df.columns:
                display_df['transaction_type'] = display_df['transaction_type'].apply(lambda x: x.value if hasattr(x, 'value') else str(x))
                
            st.dataframe(
                display_df,
                column_config={
                    "transaction_date": "Date",
                    "ticker": "Asset Ticker",
                    "transaction_type": "Action",
                    "quantity": st.column_config.NumberColumn("Shares", format="%.4f"),
                    "price_per_share": st.column_config.NumberColumn("Price/Share", format="$%.2f"),
                    "total_value": st.column_config.NumberColumn("Total Value", format="$%.2f"),
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No recent trades found in the ledger.")