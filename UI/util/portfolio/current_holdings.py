import pandas as pd
from database.portfolio.models import Account, CurrentPosition
from sqlmodel import select
import yfinance as yf


def load_portfolio_values(session) -> tuple[float, float, float, float, float, float]:
    holdings_df = load_current_holdings(session)

    total_val = 0.0
    cash_bal = 0.0
    day_chng_dollar = 0.0
    day_chng_pct = 0.0
    unrealized_pnl = 0.0
    unrealized_pnl_pct = 0.0

    if not holdings_df.empty:
        total_val = float(holdings_df["Mkt Val"].sum())
        day_chng_dollar = float(holdings_df["Day Chng $"].sum())
        unrealized_pnl = float(holdings_df["Gain/Loss $"].sum())
        
        denominator = total_val - unrealized_pnl
        if denominator > 0:
            unrealized_pnl_pct = unrealized_pnl * 100 / denominator
        
        prev_total_val = total_val - day_chng_dollar
        if prev_total_val > 0:
            day_chng_pct = (day_chng_dollar / prev_total_val) * 100
        
        cash_rows = holdings_df[holdings_df["Ticker"] == "CASH"]
        if not cash_rows.empty:
            cash_bal = float(cash_rows["Mkt Val"].sum())

    return total_val, cash_bal, day_chng_dollar, day_chng_pct, unrealized_pnl, unrealized_pnl_pct    

def load_current_holdings(session):
    """
    Reads active stock positions directly from the current_position table 
    and combines them with current account cash values.
    """
    # Fetch accounts to get their live current cached cash values
    accounts = session.scalars(select(Account)).all()
    account_cash_map = {a.id: (a.current_cash, a.account_type.value, a.owner, a.institute) for a in accounts}
    
    # Pull active allocations directly from our optimized table
    positions = session.scalars(select(CurrentPosition)).all()
    
    unique_tickers = list(set(pos.ticker for pos in positions))

    # Batch download market data for both today and yesterday
    tickers_current = {}
    tickers_prev_close = {}
    if unique_tickers:
        hist_data = yf.download(unique_tickers, period="5d")
        if not hist_data.empty and "Close" in hist_data:
            for ticker in unique_tickers:
                try:
                    series = hist_data["Close"][ticker].dropna()
                    if len(series) >= 2:
                        tickers_current[ticker] = float(series.iloc[-1])
                        tickers_prev_close[ticker] = float(series.iloc[-2])
                    elif len(series) == 1:
                        tickers_current[ticker] = float(series.iloc[-1])
                        tickers_prev_close[ticker] = float(series.iloc[-1])
                except KeyError:
                    continue
            
    active_holdings = []
    for pos in positions:
        qty = float(pos.quantity)
        cost_basis = float(pos.total_cost_basis)
        avg_buy_price = cost_basis / qty if qty > 0 else 0.0
        ticker = pos.ticker
        
        live_price = tickers_current.get(ticker, avg_buy_price)
        prev_close = tickers_prev_close.get(ticker, live_price)
        
        price_chng_dollar = live_price - prev_close
        price_chng_pct = (price_chng_dollar / prev_close * 100) if prev_close > 0 else 0.0
        
        mkt_val = qty * live_price
        day_chng_dollar = qty * price_chng_dollar 
        day_chng_pct = price_chng_pct             
        
        gain_loss_dollar = mkt_val - cost_basis
        gain_loss_pct = (gain_loss_dollar / cost_basis * 100) if cost_basis > 0 else 0.0
        
        active_holdings.append({
            "Owner": pos.account.owner,
            "Institute": pos.account.institute,
            "Account": pos.account.account_type.value,
            "Ticker": ticker,
            "Qty": qty,
            "Price": live_price,
            "Price Chng $": price_chng_dollar,
            "Price Chng %": price_chng_pct,
            "Mkt Val": mkt_val,
            "Day Chng $": day_chng_dollar,
            "Day Chng %": day_chng_pct,
            "Cost Basis": cost_basis,
            "Gain/Loss $": gain_loss_dollar,
            "Gain/Loss %": gain_loss_pct
        })
    
    # Inject current cash balance line-items
    for acct_id, (current_cash, acct_type_str, owner_str, institute) in account_cash_map.items():
        cash_float = float(current_cash or 0.0)
        if cash_float != 0.0:
            active_holdings.append({
                "Owner": owner_str,
                "Institute": institute,
                "Account": acct_type_str,
                "Ticker": "CASH",
                "Qty": cash_float,
                "Price": 1.0,
                "Price Chng $": 0.0,
                "Price Chng %": 0.0,
                "Mkt Val": cash_float,
                "Day Chng $": 0.0,
                "Day Chng %": 0.0,
                "Cost Basis": cash_float,
                "Gain/Loss $": 0.0,
                "Gain/Loss %": 0.0
            })
            
    return pd.DataFrame(active_holdings)