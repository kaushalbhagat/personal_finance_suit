from decimal import Decimal
import streamlit as st
import pandas as pd
from database.setup import get_db
from database.portfolio.models import Account
from sqlmodel import select
import yfinance as yf
from datetime import date, timedelta

from util.portfolio.financial_data import load_financial_data
from util.portfolio.transactions import execute_equity_transaction, InsufficientFundsError
from util.portfolio.split import execute_stock_split
from util.portfolio.cash import deposit_cash, withdraw_cash

st.set_page_config(page_title="Personal Budget Dashboard", layout="wide")

# Helper callback function run BEFORE widgets render on submit
def process_form_submission(account_options):
    symbol_input = st.session_state.get("form_symbol", "").upper().strip()
    date_input = st.session_state.get("form_date")
    selected_acct_label = st.session_state.get("form_account")
    quantity_input = st.session_state.get("form_quantity", 0.0001)
    price_input = st.session_state.get("form_price", 0.01)
    action_input = st.session_state.get("form_action")

    if not symbol_input:
        st.session_state["form_error"] = "Please provide an asset ticker symbol."
        return

    target_account_id = account_options[selected_acct_label]
    
    with get_db() as session:
        try:
            if action_input == "Split":
                execute_stock_split(session, symbol_input, quantity_input, date_input)
                st.session_state["form_success"] = "Split applied successfully across all accounts"
            elif action_input in {"Buy", "Sell"}:
                execute_equity_transaction(date_input, symbol_input, quantity_input, price_input, action_input, target_account_id, session)
                st.session_state["form_success"] = "Successfully entered Trade"
            elif action_input == "Deposit":
                deposit_cash(date_input, quantity_input, target_account_id, session)
            elif action_input == "Withdraw":
                withdraw_cash(date_input, quantity_input, target_account_id, session)

            # CLEAR STATE SAFELY (Executed BEFORE widgets render on the rerun)
            st.session_state["form_symbol"] = ""
            st.session_state["form_quantity"] = 0.0001
            st.session_state["form_price"] = 0.01

        except InsufficientFundsError as e:
            st.session_state["form_error"] = str(e)


with get_db() as session:
    tx_df, acct_df = load_financial_data(session)

    # --- TRANSACTION LOGGER & RECENT LEDGER ---
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("Log New Transaction")
        
        # Display feedback toasts/alerts from previous submission callback
        if "form_success" in st.session_state:
            st.success(st.session_state.pop("form_success"))
        if "form_error" in st.session_state:
            st.error(st.session_state.pop("form_error"))

        account_options = {}
        for acc in acct_df.itertuples():
            label = f"{acc.owner} - {acc.account_type} (${float(acc.current_cash):,.2f})"
            account_options[label] = acc.id
            
        if not account_options:
            st.warning("Please configure accounts in your database first.")
        else:
            with st.form("transaction_form"):
                date_input = st.date_input("Date", key="form_date")
                selected_acct_label = st.selectbox("Account", list(account_options.keys()), key="form_account")
                symbol_input = st.text_input("Symbol", key="form_symbol")
                
                quantity_input = st.number_input("Quantity", min_value=0.0001, step=1.0, format="%.4f", key="form_quantity")
                price_input = st.number_input("Price", min_value=0.01, step=0.01, format="%.2f", key="form_price")
                action_input = st.selectbox("Action", ["Buy", "Sell", "Deposit", "Withdraw", "Split"], key="form_action")
                
                estimated_total = quantity_input * price_input
                st.caption(f"Estimated Total: **${estimated_total:,.2f}**")
                
                # Pass the processing logic as callback to form submission
                st.form_submit_button(
                    "Submit Transaction", 
                    on_click=process_form_submission, 
                    args=(account_options,)
                )

    with right_col:
        st.subheader("Recent Ledger Entries")
        if not tx_df.empty:
            tx_df['total_value'] = tx_df['quantity'] * tx_df['price_per_share']
            display_df = tx_df[['transaction_date', 'account_name', 'ticker', 'transaction_type', 'quantity', 'price_per_share', 'total_value']].sort_values(by='transaction_date', ascending=False)
            
            # --- TICKER SEARCH FILTER ---
            search_ticker = st.text_input("🔍 Search Transaction for a Ticker...", key="tx_ticker_search").strip().upper()
            if search_ticker:
                display_df = display_df[display_df["ticker"].str.contains(search_ticker, case=False, na=False)]
            # ----------------------------

            if 'transaction_type' in display_df.columns:
                display_df['transaction_type'] = display_df['transaction_type'].apply(lambda x: x.value if hasattr(x, 'value') else str(x))
                
            if not display_df.empty:
                st.dataframe(
                    display_df,
                    column_config={
                        "transaction_date": "Date",
                        "account_name": "Account",
                        "ticker": "Asset Ticker",
                        "transaction_type": "Action",
                        "quantity": st.column_config.NumberColumn("Shares", format="%.4f"),
                        "price_per_share": st.column_config.NumberColumn("Price/Share", format="$%.2f"),
                        "total_value": st.column_config.NumberColumn("Total Value", format="$%.2f"),
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.info(f"No transactions found matching ticker **'{search_ticker}'**.")
        else:
            st.info("No recent trades found in the ledger.")