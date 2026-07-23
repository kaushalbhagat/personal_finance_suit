from datetime import date
import pandas as pd
import streamlit as st
from sqlmodel import select, Session
from database.portfolio.models import Account, Transaction
from util.portfolio.rsu_pnl import calculate_fifo_tax_pnl_with_liquidation, get_current_price

from database.setup import get_db


with get_db() as session:
    st.title("📊 Ticker Tax & PnL Analyzer (With Projected Liquidation)")
    
    # # 1. Select Account & Ticker
    account = session.scalars(select(Account).where(
        Account.owner == "Kaushal",
        Account.account_type == "POST_TAX"
    )).first()

    if account:
        selected_acct_id = account.id
        ticker_input = "GOOG"
        current_price = get_current_price(ticker_input)
        if current_price:
            st.success(f"Fetched Live Market Price for **{ticker_input}**: **${current_price:,.2f}**")

            # 2. Query Transactions
            tx_query = select(Transaction).where(
                Transaction.account_id == selected_acct_id,
                Transaction.ticker == ticker_input
            )
            transactions = session.scalars(tx_query).all()

            if transactions:
                # 3. Process FIFO Calculations + Liquidation
                df_sales, summary = calculate_fifo_tax_pnl_with_liquidation(
                    transactions=transactions, 
                    current_price=current_price
                )

                # 4. Display Metrics
                st.markdown("---")
                st.subheader(f"Tax & PnL Summary (Including Today's Sale @ ${current_price:,.2f})")
                col1, col2, col3, col4 = st.columns(4)
                
                col1.metric("Total Projected PnL", f"${summary['total_pnl']:,.2f}")
                col2.metric("Short-Term PnL / Tax (35%)", f"${summary['st_pnl']:,.2f}", delta=f"-${summary['st_tax']:,.2f} Tax", delta_color="inverse")
                col3.metric("Long-Term PnL / Tax (10%)", f"${summary['lt_pnl']:,.2f}", delta=f"-${summary['lt_tax']:,.2f} Tax", delta_color="inverse")
                col4.metric("Total Tax Liability", f"${summary['total_tax']:,.2f}")

                st.markdown("---")

                # 5. Show Combined Breakdown Table
                st.subheader("All Sales & Simulated Liquidation Lots")
                if not df_sales.empty:
                    st.dataframe(
                        df_sales.style.format({
                            "Quantity": "{:,.2f}",
                            "Buy Price": "${:,.2f}",
                            "Sell Price": "${:,.2f}",
                            "Cost Basis": "${:,.2f}",
                            "Proceeds": "${:,.2f}",
                            "PnL ($)": "${:,.2f}",
                            "Est. Tax ($)": "${:,.2f}"
                        }),
                        use_container_width=True
                    )
                else:
                    st.info("No active holdings or transactions found.")
            else:
                st.warning(f"No transactions found for ticker **{ticker_input}** in selected account.")
        else:
             st.error(
                f"Could not retrieve a current market price for **{ticker_input}**. Please verify the symbol."
            )
    else:
        st.warning("No accounts found in database.")
