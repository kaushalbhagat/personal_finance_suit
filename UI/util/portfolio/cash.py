import pandas as pd
import yfinance as yf
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from database.portfolio.models import Account, Transaction, TransactionType


def add_cash_tx(date_input: date, quantity_input: Decimal, selected_acct_id: int, session, action: str):

    qty_dec = Decimal(str(quantity_input))
    if action == TransactionType.WITHDRAW:
        qty_dec *= -1

    account_row = session.get(Account, selected_acct_id)
    current_cash_dec = Decimal(str(account_row.current_cash or "0.00"))
    account_row.current_cash = current_cash_dec + qty_dec
    
    new_tx = Transaction(
        transaction_date=date_input,
        ticker="CASH",
        transaction_type=action,
        quantity=qty_dec,
        price_per_share=1,
        account_id=account_row.id
    )
    session.add(new_tx)
    session.add(account_row)
    session.commit()

def deposit_cash(date_input: date, quantity_input: Decimal, selected_acct_id: int, session):
    add_cash_tx(date_input, quantity_input, selected_acct_id, session, TransactionType.DEPOSIT)

def withdraw_cash(date_input: date, quantity_input: Decimal, selected_acct_id: int, session):
    add_cash_tx(date_input, quantity_input, selected_acct_id, session, TransactionType.WITHDRAW)