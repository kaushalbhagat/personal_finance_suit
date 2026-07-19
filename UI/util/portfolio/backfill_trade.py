import csv
from datetime import datetime
from decimal import Decimal
from database import get_db
from database.models import Account, AccountType
from sqlalchemy import select

from util.portfolio.transactions import execute_equity_transaction

def get_account_id(owner: str, type: str, session):
    acct_type_enum = AccountType(type)
    stmt = select(Account).where(
        Account.owner == owner, 
        Account.account_type == acct_type_enum
    )
    account = session.scalars(stmt).first()
    if not account:
        account = Account(owner=owner, account_type=acct_type_enum)
        session.add(account)
        session.flush() 
    return account.id

def seed_historical_ledger(csv_file_path: str):
    print(f"🚀 Initializing ingestion of: {csv_file_path}")
    
    with get_db() as session:
        with open(csv_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_idx, row in enumerate(reader, start=1):
                owner = row.get('owner') or "Kaushal"
                raw_acct_type = row.get('account_type') or "Unknown"
                print(f">>> processing row {row_idx}: {owner} ({raw_acct_type})")
                account_id = get_account_id(owner, raw_acct_type, session)
                tx_date = datetime.strptime(row['date'].strip(), "%m/%d/%Y").date()
                ticker = row['ticker'].strip().upper()
                tx_type = row['type'].strip()
                quantity = Decimal(row['quantity'].strip())
                price_per_share = Decimal(row['price'].strip())

                execute_equity_transaction(tx_date, ticker, quantity, price_per_share, tx_type, account_id, session)
        
        # The 'get_db' context manager commits everything cleanly right here
        # This writes both the new transactions AND the updated account cash balances simultaneously!
        print("✅ Seeding and cash reconciliation completed. All records saved successfully.")

if __name__ == "__main__":
    # Point this to your actual exported Google Sheet file path
    seed_historical_ledger("Transactions_kids.csv")