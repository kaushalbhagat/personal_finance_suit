from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from database.portfolio.models import Account
from util.portfolio.daily_snapshots import refresh_daily_snapshot, incremental_build_daily_snapshots

def build_daily_snapshot_for_all_acounts():
    with get_db() as session:
        refresh_daily_snapshot(session)

def build_daily_snapshot_for_an_account(account_id):
    with get_db() as session:
        stmt = select(Account).where(Account.id == account_id)
        account = session.scalars(stmt).first()
        incremental_build_daily_snapshots(session, date(2024, 1, 1), date.today(), [account])

if __name__ == "__main__":
    build_daily_snapshot_for_an_account(10)