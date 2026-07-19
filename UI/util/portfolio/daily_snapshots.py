
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from database.models import Account, Transaction, DailySnapshot, TransactionType, SnapshotHolding

class SnapshotException(Exception):
    """Exception raised when a daily snapshot can't be created."""
    def __init__(self, message):
        super().__init__(message)

def refresh_daily_snapshot(session):

    latest_snap_stmt = select(DailySnapshot.snapshot_date).order_by(DailySnapshot.snapshot_date.desc()).limit(1)
    latest_snap_date = session.scalars(latest_snap_stmt).first()
    
    today = date.today()
    
    if not latest_snap_date:
        # If completely empty, search for earliest transaction or default to 2020
        earliest_tx_stmt = select(Transaction.transaction_date).order_by(Transaction.transaction_date.asc()).limit(1)
        earliest_tx_date = session.scalars(earliest_tx_stmt).first()
        start_date = earliest_tx_date if earliest_tx_date else date(2020, 1, 1)
    else:
        # Start on the day immediately following your last cached date
        start_date = latest_snap_date + timedelta(days=1)
    
    if start_date > today:
        raise SnapshotException("Snapshots are already fully up to date!")
    else:
        return incremental_build_daily_snapshots(session, start_date, today)
  

def incremental_build_daily_snapshots(session, start_date: date, end_date: date, accounts=None):
    """
    Optimized incremental snapshot builder. Avoids looping through all historical 
    transactions by initializing state once and processing day-by-day.
    """
    # 1. Gather all active tickers across the transaction ledger
    # all_tx_tickers = session.scalars(select(Transaction.ticker)).all()
    all_tx_tickers = session.scalars(
        select(Transaction.ticker)
        .where(Transaction.ticker.isnot(None))
        .where(Transaction.ticker != "CASH")
    ).all()    
    unique_tickers = list(set(all_tx_tickers))
    
    if not unique_tickers:
        return 0

    # Add 7 days of historical padding to handle holiday/weekend fallbacks safely
    buffer_start = start_date - timedelta(days=7)
    
    df_prices = yf.download(
        tickers=unique_tickers,
        start=buffer_start.strftime("%Y-%m-%d"),
        end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        group_by='ticker'
    )
    
    if df_prices.empty:
        return 0

    generated_days = 0
    if accounts is None: 
        accounts = session.scalars(select(Account)).all()
    
    # 2. INITIALIZE RUNNING STATE FOR EACH ACCOUNT ONCE (Before entering the date loop)
    # This dictionary will hold the persistent state across the entire date range loop
    account_states = {}
    day_before_start = start_date - timedelta(days=1)

    for account in accounts:
        # Try to bootstrap state from the previous day's stored snapshot (Approach 1 advantage)
        prev_snap = session.scalars(
            select(DailySnapshot).where(
                DailySnapshot.account_id == account.id,
                DailySnapshot.snapshot_date == day_before_start
            )
        ).first()

        if prev_snap:
            cash_balance = Decimal(str(prev_snap.cash_balance))
            holdings = {h.ticker: Decimal(str(h.quantity)) for h in prev_snap.holdings}
        else:
            # Fallback: Reconstruct starting positions from transactions up to the day before start_date
            init_tx_stmt = (
                select(Transaction)
                .where(Transaction.account_id == account.id)
                .where(Transaction.transaction_date <= day_before_start)
            )
            init_transactions = session.scalars(init_tx_stmt).all()
            
            cash_balance = Decimal(str(account.initial_cash or "0.00"))
            holdings = {}
            for tx in init_transactions:
                if tx.transaction_type in [TransactionType.BUY, TransactionType.SELL]:
                    if tx.ticker not in holdings:
                        holdings[tx.ticker] = Decimal("0.0000")
                    tx_value = tx.quantity * tx.price_per_share
                    if tx.transaction_type == TransactionType.BUY:
                        holdings[tx.ticker] += tx.quantity
                        cash_balance -= tx_value
                    elif tx.transaction_type == TransactionType.SELL:
                        holdings[tx.ticker] -= tx.quantity
                        cash_balance += tx_value
                elif tx.transaction_type == TransactionType.DEPOSIT:
                    cash_balance += (tx.quantity * tx.price_per_share)
                elif tx.transaction_type == TransactionType.WITHDRAW:
                    cash_balance -= (tx.quantity * tx.price_per_share)                    

        account_states[account.id] = {
            "cash_balance": cash_balance,
            "holdings": holdings
        }

    # 3. DATE PROCESSING LOOP
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        for account in accounts:
            state = account_states[account.id]
            
            # CRITICAL CHANGE: Only pull transactions that happened on *THIS SPECIFIC DAY*
            day_tx_stmt = (
                select(Transaction)
                .where(Transaction.account_id == account.id)
                .where(Transaction.transaction_date == current_date)
            )
            day_transactions = session.scalars(day_tx_stmt).all()
            
            # Apply only today's transactions to the accumulated state
            for tx in day_transactions:
                if tx.transaction_type in [TransactionType.BUY, TransactionType.SELL]:
                    if tx.ticker not in state["holdings"]:
                        state["holdings"][tx.ticker] = Decimal("0.0000")
                    tx_value = tx.quantity * tx.price_per_share
                    if tx.transaction_type == TransactionType.BUY:
                        state["holdings"][tx.ticker] += tx.quantity
                        state["cash_balance"] -= tx_value
                    elif tx.transaction_type == TransactionType.SELL:
                        state["holdings"][tx.ticker] -= tx.quantity
                        state["cash_balance"] += tx_value
                elif tx.transaction_type == TransactionType.DEPOSIT:
                    state["cash_balance"] += (tx.quantity * tx.price_per_share)
                elif tx.transaction_type == TransactionType.WITHDRAW:
                    state["cash_balance"] -= (tx.quantity * tx.price_per_share) 
            
            # Calculate market values using our running holdings state
            total_market_value_of_shares = Decimal("0.00")
            
            for ticker, shares in state["holdings"].items():
                if shares > 0:
                    current_market_price = Decimal("0.00")
                    try:
                        if len(unique_tickers) == 1:
                            price_series = df_prices['Close'] if 'Close' in df_prices else df_prices[unique_tickers[0]]['Close']
                        else:
                            price_series = df_prices[ticker]['Close']
                        
                        if date_str in price_series.index:
                            price_val = price_series.loc[date_str]
                            if pd.notna(price_val):
                                current_market_price = Decimal(str(price_val))
                        else:
                            previous_prices = price_series.loc[:date_str]
                            if not previous_prices.empty:
                                valid_prices = previous_prices.dropna()
                                if not valid_prices.empty:
                                    current_market_price = Decimal(str(valid_prices.iloc[-1]))
                    except Exception:
                        current_market_price = Decimal("0.00")
                    
                    total_market_value_of_shares += (shares * current_market_price)
            
            total_account_value = state["cash_balance"] + total_market_value_of_shares
            
            # 4. UPSERT SNAPSHOT AND PERSIST QUANTITIES TO DISK
            snap_stmt = select(DailySnapshot).where(
                DailySnapshot.account_id == account.id,
                DailySnapshot.snapshot_date == current_date
            )
            existing_snapshot = session.scalars(snap_stmt).first()
            
            if existing_snapshot:
                existing_snapshot.total_value = total_account_value
                existing_snapshot.cash_balance = state["cash_balance"]
                # Clear out old child rows before replacing them to prevent double-inserting duplicates
                existing_snapshot.holdings.clear()
                snapshot_obj = existing_snapshot
            else:
                snapshot_obj = DailySnapshot(
                    account_id=account.id,
                    snapshot_date=current_date,
                    total_value=total_account_value,
                    cash_balance=state["cash_balance"],
                    unrealized_pnl=Decimal("0.00")
                )
                session.add(snapshot_obj)
            
            # Append today's frozen holdings directly to the relationship list
            for ticker, qty in state["holdings"].items():
                if qty > 0:
                    holding_record = SnapshotHolding(
                        ticker=ticker,
                        quantity=qty
                    )
                    snapshot_obj.holdings.append(holding_record)
                
        generated_days += 1
        current_date += timedelta(days=1)
        
    session.commit()
    return generated_days