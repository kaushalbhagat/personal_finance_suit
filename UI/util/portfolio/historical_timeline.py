import pandas as pd
from database.portfolio.models import DailySnapshot
from sqlmodel import select

def load_historical_timeline(session):
    stmt = select(DailySnapshot).order_by(DailySnapshot.snapshot_date.asc())
    snapshots = session.scalars(stmt).all()
    
    data = []
    for snap in snapshots:
        data.append({
            "Date": pd.to_datetime(snap.snapshot_date),
            "Account Type": snap.account.account_type.value,
            "Total Value": float(snap.total_value),
            "Cash Balance": float(snap.cash_balance),
        })
    return pd.DataFrame(data)