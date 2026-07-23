import pandas as pd
from database.portfolio.models import Account, Transaction
from sqlmodel import select
from database.setup import get_db


def load_financial_data(session):
    # Fetch all transactions using scalars
    tx_query = session.scalars(select(Transaction)).all()
    # Fetch all accounts using scalars
    acct_query = session.scalars(select(Account)).all()
    
    tx_list = []
    for tx in tx_query:
        # Convert Transaction columns to a dict
        tx_dict = {col: getattr(tx, col) for col in tx.__table__.columns.keys()}
        
        # Access the related account via SQLModel relationship
        if tx.account:
            acct_type_str = (
                tx.account.account_type.value 
                if hasattr(tx.account.account_type, 'value') 
                else str(tx.account.account_type)
            )
            tx_dict["account_name"] = f"{tx.account.owner} - {acct_type_str}"
        else:
            tx_dict["account_name"] = "Unknown Account"
            
        tx_list.append(tx_dict)
    
    acct_list = [{col: getattr(acct, col) for col in acct.__table__.columns.keys()} for acct in acct_query]
    
    return (
        pd.DataFrame(tx_list) if tx_list else pd.DataFrame(),
        pd.DataFrame(acct_list) if acct_list else pd.DataFrame()
    )

if __name__ == "__main__":
    with get_db() as session:
        tx_df, acct_df = load_financial_data(session)
        print(tx_df.head(10))
