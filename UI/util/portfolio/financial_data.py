import pandas as pd
from database.portfolio.models import Account, Transaction
from sqlmodel import select

def load_financial_data(session):
    tx_query = session.scalars(select(Transaction)).all()
    acct_query = session.scalars(select(Account)).all()
    
    tx_list = [{col: getattr(tx, col) for col in tx.__table__.columns.keys()} for tx in tx_query]
    acct_list = [{col: getattr(acct, col) for col in acct.__table__.columns.keys()} for acct in acct_query]
    
    return pd.DataFrame(tx_list) if tx_list else pd.DataFrame(), pd.DataFrame(acct_list) if acct_list else pd.DataFrame()