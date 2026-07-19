from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship, Session
from datetime import date, datetime, timezone

class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=150, nullable=False)
    exclude_from_reporting: bool = Field(default=False)
    subcategories: List["SubCategory"] = Relationship(back_populates="category")

class SubCategory(SQLModel, table=True):
    __tablename__ = "subcategories"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=150, nullable=False)
    category_id: int = Field(foreign_key="categories.id", ondelete="CASCADE")
    category: Category = Relationship(back_populates="subcategories")  

class Mapping(SQLModel, table=True):
    __tablename__ = "mappings"
    id: Optional[int] = Field(default=None, primary_key=True)
    keyword: str = Field(index=True, unique=True, max_length=150, nullable=False)
    category_id: int = Field(foreign_key="categories.id", ondelete="CASCADE") 
    subcategory_id: int = Field(foreign_key="subcategories.id", ondelete="CASCADE") 
    category: Category = Relationship()
    subcategory: SubCategory = Relationship()


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    description: str = Field(max_length=250)
    type: str = Field(max_length=50)
    category_id: Optional[int] = Field(default=None,foreign_key="categories.id") 
    subcategory_id: Optional[int] = Field(default=None,foreign_key="subcategories.id")    
    amount: float
    bank_name: Optional[str] = Field(default=None, max_length=50)
    note: Optional[str] = Field(default=None, max_length=250)
    category: Category = Relationship()
    subcategory: SubCategory = Relationship()

class PlaidItems(SQLModel, table=True):
    __tablename__ = "plaid_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    institution_id: Optional[str] = Field(max_length=100)
    institution_name: Optional[str] = Field(max_length=250)
    item_id: str = Field(unique=True, index=True, max_length=100)
    access_token: str = Field(max_length=250)
    status: str = Field(default='active', max_length=50)
    last_sync: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cursor: Optional[str] = Field(max_length=250, default=None)

class PlaidAccounts(SQLModel, table=True):
    __tablename__ = "plaid_accounts"
    # Plaid provides a unique string string identifier per account (e.g., 'cr_98A12x...')
    id: str = Field(primary_key=True) 
    
    # 🔗 Foreign Key linking this account directly to your existing table
    item_id: str = Field(foreign_key="plaid_items.item_id") 
    
    name: str                  # e.g., "Premier Checking"
    mask: Optional[str] = None # e.g., "1234" (The last 4 digits)
    type: str                  # e.g., "depository", "credit", "investment"
    subtype: str               # e.g., "checking", "savings", "credit card"
    
    # 💰 Balance tracking
    current_balance: float
    available_balance: Optional[float] = None
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    custom_name: Optional[str] = Field(default=None, nullable=True)
    classification_type: str = Field(default="Personal", nullable=False) # "Personal" or "Business"        