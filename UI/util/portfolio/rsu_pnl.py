from datetime import date
import pandas as pd
import streamlit as st
import yfinance as yf
from sqlmodel import select, Session
from database.portfolio.models import Account, Transaction

LT_TAX_RATE = 0.10  # 10% Long-Term Tax Rate
ST_TAX_RATE = 0.35  # 35% Short-Term Tax Rate

@st.cache_data(ttl=300)  # Cache for 5 minutes to prevent rate-limiting
def get_current_price(ticker_symbol: str) -> float | None:
    """Fetches the latest market price for a ticker using yfinance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        # fast_info['last_price'] provides fast price lookups
        if hasattr(ticker, "fast_info") and "last_price" in ticker.fast_info:
            price = ticker.fast_info["last_price"]
            if price and not pd.isna(price):
                return float(price)

        # Fallback to recent history if fast_info fails
        hist = ticker.history(period="1d")
        if not hist.empty and "Close" in hist:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        st.error(f"Error fetching live price for {ticker_symbol}: {e}")
    return None

def calculate_fifo_tax_pnl_with_liquidation(
    transactions, 
    current_price: float, 
    liquidation_date: date = None,
    lt_rate=LT_TAX_RATE, 
    st_rate=ST_TAX_RATE
):
    """
    Processes BUY and actual SELL transactions in FIFO order, then simulates a 
    full liquidation of remaining holdings at `current_price` as of `liquidation_date`.
    """
    if liquidation_date is None:
        liquidation_date = date.today()

    # Ensure chronological order
    sorted_txs = sorted(transactions, key=lambda x: x.transaction_date)
    
    buy_lots = []
    all_sales = []

    # 1. Process Actual Historical Transactions
    for tx in sorted_txs:
        t_type = tx.transaction_type.value if hasattr(tx.transaction_type, 'value') else str(tx.transaction_type)
        t_type = t_type.upper()

        if t_type == "BUY":
            buy_lots.append({
                "tx_id": tx.id,
                "date": tx.transaction_date,
                "price": float(tx.price_per_share),
                "qty_remaining": float(tx.quantity)
            })
        elif t_type == "SELL":
            sell_qty = float(tx.quantity)
            sell_price = float(tx.price_per_share)
            sell_date = tx.transaction_date

            while sell_qty > 0 and buy_lots:
                lot = buy_lots[0]
                matched_qty = min(sell_qty, lot["qty_remaining"])
                
                holding_days = (sell_date - lot["date"]).days
                is_long_term = holding_days > 365
                term_label = "Long-Term" if is_long_term else "Short-Term"
                applicable_tax_rate = lt_rate if is_long_term else st_rate

                cost_basis = matched_qty * lot["price"]
                proceeds = matched_qty * sell_price
                pnl = proceeds - cost_basis
                tax_est = max(0.0, pnl) * applicable_tax_rate

                all_sales.append({
                    "Sell Date": sell_date,
                    "Buy Date": lot["date"],
                    "Holding (Days)": holding_days,
                    "Term": term_label,
                    "Status": "Realized (Past Sale)",
                    "Quantity": matched_qty,
                    "Buy Price": lot["price"],
                    "Sell Price": sell_price,
                    "Cost Basis": cost_basis,
                    "Proceeds": proceeds,
                    "PnL ($)": pnl,
                    "Tax Rate": f"{int(applicable_tax_rate * 100)}%",
                    "Est. Tax ($)": tax_est
                })

                sell_qty -= matched_qty
                lot["qty_remaining"] -= matched_qty

                if lot["qty_remaining"] == 0:
                    buy_lots.pop(0)

    # 2. Simulate Selling All Remaining Open Holdings at Today's Price
    for lot in buy_lots:
        remaining_qty = lot["qty_remaining"]
        if remaining_qty > 0:
            holding_days = (liquidation_date - lot["date"]).days
            is_long_term = holding_days > 365
            term_label = "Long-Term" if is_long_term else "Short-Term"
            applicable_tax_rate = lt_rate if is_long_term else st_rate

            cost_basis = remaining_qty * lot["price"]
            proceeds = remaining_qty * current_price
            pnl = proceeds - cost_basis
            tax_est = max(0.0, pnl) * applicable_tax_rate

            all_sales.append({
                "Sell Date": liquidation_date,
                "Buy Date": lot["date"],
                "Holding (Days)": holding_days,
                "Term": term_label,
                "Status": "Assumed Sale (Today)",
                "Quantity": remaining_qty,
                "Buy Price": lot["price"],
                "Sell Price": current_price,
                "Cost Basis": cost_basis,
                "Proceeds": proceeds,
                "PnL ($)": pnl,
                "Tax Rate": f"{int(applicable_tax_rate * 100)}%",
                "Est. Tax ($)": tax_est
            })

    df_sales = pd.DataFrame(all_sales)

    # 3. Compute Summary Metrics (Past + Assumed Liquidation)
    if not df_sales.empty:
        st_pnl = df_sales[df_sales["Term"] == "Short-Term"]["PnL ($)"].sum()
        lt_pnl = df_sales[df_sales["Term"] == "Long-Term"]["PnL ($)"].sum()
        
        st_tax = max(0.0, st_pnl) * st_rate
        lt_tax = max(0.0, lt_pnl) * lt_rate
        total_pnl = df_sales["PnL ($)"].sum()
        total_tax = st_tax + lt_tax
    else:
        st_pnl = lt_pnl = total_pnl = st_tax = lt_tax = total_tax = 0.0

    summary = {
        "st_pnl": st_pnl,
        "lt_pnl": lt_pnl,
        "total_pnl": total_pnl,
        "st_tax": st_tax,
        "lt_tax": lt_tax,
        "total_tax": total_tax
    }

    return df_sales, summary


def render_ticker_tax_view(session: Session):
    st.title("📊 Ticker Tax & PnL Analyzer (With Projected Liquidation)")
    
    # 1. Select Account & Ticker
    accounts = session.scalars(select(Account)).all()
    if not accounts:
        st.warning("No accounts found in database.")
        return

    account_map = {f"{acct.owner} - {acct.account_type}": acct.id for acct in accounts}
    selected_acct_label = st.selectbox("Select Account", options=list(account_map.keys()))
    selected_acct_id = account_map[selected_acct_label]

    col_ticker, col_price = st.columns(2)
    with col_ticker:
        ticker_input = st.text_input("Ticker Symbol", value="GOOG").strip().upper()
    with col_price:
        current_price = st.number_input(
            "Assumed Today's Selling Price ($)", 
            min_value=0.01, 
            value=175.00, 
            step=1.00
        )

    if not ticker_input:
        st.info("Please enter a valid ticker symbol.")
        return

    # 2. Query Transactions
    tx_query = select(Transaction).where(
        Transaction.account_id == selected_acct_id,
        Transaction.ticker == ticker_input
    )
    transactions = session.scalars(tx_query).all()

    if not transactions:
        st.warning(f"No transactions found for ticker **{ticker_input}** in selected account.")
        return

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