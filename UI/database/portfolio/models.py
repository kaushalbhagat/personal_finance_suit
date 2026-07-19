
from sqlmodel import SQLModel
import enum
from datetime import date
from typing import List, Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint

# 1. Base Class for Models
class Base(SQLModel):
    metadata = SQLModel.metadata.__class__() 

# 2. Enums for Data Integrity
class AccountType(str, enum.Enum):
    IRA = "IRA"
    ROTH = "ROTH"
    POST_TAX = "Post Tax"
    UTMA = "UTMA"
    K401 = "401k"
    RSU = "RSU"
    UNKNOWN = "Unknown"

class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"   # For adding cash
    WITHDRAW = "WITHDRAW" # For taking cash out
    SPLIT = "SPLIT"

# 3. Account Model
class Account(Base, table=True):
    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner: str = Field(max_length=100)
    institute: str = Field(max_length=100)
    account_type: AccountType
    initial_cash: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    current_cash: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    
    # Relationships
    transactions: List["Transaction"] = Relationship(
        back_populates="account",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    positions: List["CurrentPosition"] = Relationship(
        back_populates="account",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

# 4. Transaction Model
class Transaction(Base, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    ticker: str = Field(max_length=10, index=True) 
    transaction_type: TransactionType
    quantity: Decimal = Field(max_digits=18, decimal_places=4) 
    price_per_share: Decimal = Field(max_digits=18, decimal_places=4)
    transaction_date: date = Field(index=True)

    account: Optional[Account] = Relationship(back_populates="transactions")

# 5. Daily Snapshot Model
class DailySnapshot(Base, table=True):
    __tablename__ = "daily_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    snapshot_date: date = Field(index=True)
    
    total_value: Decimal = Field(max_digits=18, decimal_places=2)
    cash_balance: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2) 
    unrealized_pnl: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)

    account: Optional[Account] = Relationship()

class SnapshotHolding(Base, table=True):
    __tablename__ = "snapshot_holdings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_id: int = Field(foreign_key="daily_snapshots.id")
    ticker: str = Field(max_length=10, index=True)
    quantity: Decimal = Field(max_digits=18, decimal_places=4)    

# 6. Current Positions Model
class CurrentPosition(Base, table=True):
    __tablename__ = "current_positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    ticker: str = Field(max_length=10, index=True)
    quantity: Decimal = Field(default=Decimal("0.0000"), max_digits=18, decimal_places=4)
    total_cost_basis: Decimal = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)

    account: Optional[Account] = Relationship(back_populates="positions")

    __table_args__ = (
        UniqueConstraint("account_id", "ticker", name="uq_account_ticker"),
    )