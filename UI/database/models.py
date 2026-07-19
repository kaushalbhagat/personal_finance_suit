import enum
from datetime import date
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import ForeignKey, MetaData, String, Numeric, Date, Enum, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlmodel.ext.asyncio.session import AsyncSession
from collections.abc import AsyncGenerator


# 1. Base Class for Models
class Base(DeclarativeBase):
    # metadata = MetaData()
    pass

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
class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    institute: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    current_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    
    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    positions: Mapped[List["CurrentPosition"]] = relationship(
        "CurrentPosition", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, owner='{self.owner}', type='{self.account_type.value}')>"

# 4. Transaction Model (The Ledger)
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True) 
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False) 
    price_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Relationship back to the account
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction({self.transaction_type.value} {self.quantity} {self.ticker} @ ${self.price_per_share})>"
    
# 5. Daily Snapshot Model (For lightning-fast timeline rendering)
class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Financial metrics for that specific day
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00")) 
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    # Relationship back to the account
    account: Mapped["Account"] = relationship("Account")
    holdings = relationship("SnapshotHolding", backref="snapshot", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DailySnapshot(Account={self.account_id}, Date={self.snapshot_date}, Value=${self.total_value})>"

class SnapshotHolding(Base):
    __tablename__ = "snapshot_holdings"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("daily_snapshots.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)    

# 6. Optimized Current Positions Lookup Table
class CurrentPosition(Base):
    __tablename__ = "current_positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"))
    total_cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    # Relationship to cleanly map account information (e.g. pos.account.owner)
    account: Mapped["Account"] = relationship("Account", back_populates="positions")

    # Ensure a single account only has one entry per ticker
    __table_args__ = (
        UniqueConstraint("account_id", "ticker", name="uq_account_ticker"),
    )

    def __repr__(self) -> str:
        return f"<CurrentPosition(Account={self.account_id}, Ticker='{self.ticker}', Qty={self.quantity})>"