import pandas as pd
import yfinance as yf
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from database.portfolio.models import Account, CurrentPosition, Transaction, TransactionType

class InsufficientFundsError(Exception):
    """Exception raised when a user tries to buy equity for more money than they have."""
    def __init__(self, message):
        super().__init__(message)

def execute_equity_transaction(date_input: date, symbol_input: str, quantity_input: Decimal, price_input: Decimal, action_input: str, selected_acct_id: int, session):
            
    if symbol_input:
        # target_account_id = account_options[selected_acct_label]
        tx_type_enum = ""
        if action_input == "Buy":
            tx_type_enum = TransactionType.BUY
        else:
            tx_type_enum = TransactionType.SELL
        
        qty_dec = Decimal(str(quantity_input))
        price_dec = Decimal(str(price_input))
        total_dec = qty_dec * price_dec
        
        account_row = session.get(Account, selected_acct_id)
        current_cash_dec = Decimal(str(account_row.current_cash or "0.00"))
        
        tx_executable = True
        if tx_type_enum == TransactionType.BUY:
            if current_cash_dec < total_dec:
                raise InsufficientFundsError(f"Insufficient funds! Available: ${float(current_cash_dec):,.2f}")
                tx_executable = False
            else:
                account_row.current_cash = current_cash_dec - total_dec
        else:
            account_row.current_cash = current_cash_dec + total_dec
            
        if tx_executable:
            # Synchronized Update: Mutate CurrentPosition table
            pos_stmt = select(CurrentPosition).where(
                CurrentPosition.account_id == account_row.id,
                CurrentPosition.ticker == symbol_input
            )
            position_row = session.scalars(pos_stmt).first()
            
            if tx_type_enum == TransactionType.BUY:
                if not position_row:
                    position_row = CurrentPosition(
                        account_id=account_row.id,
                        ticker=symbol_input,
                        quantity=qty_dec,
                        total_cost_basis=total_dec
                    )
                    session.add(position_row)
                else:
                    position_row.quantity += qty_dec
                    position_row.total_cost_basis += total_dec
            elif tx_type_enum == TransactionType.SELL:
                if position_row:
                    position_row.quantity -= qty_dec
                    position_row.total_cost_basis -= total_dec
                    if position_row.quantity <= 0:
                        session.delete(position_row)
            
            new_tx = Transaction(
                transaction_date=date_input,
                ticker=symbol_input,
                transaction_type=tx_type_enum,
                quantity=qty_dec,
                price_per_share=price_dec,
                account_id=account_row.id
            )
            session.add(new_tx)
            session.add(account_row)
            session.commit()