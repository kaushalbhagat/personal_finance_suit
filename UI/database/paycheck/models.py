from datetime import date
from decimal import Decimal
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel

class PaycheckBase(SQLModel):
    metadata = SQLModel.metadata.__class__() ;

class Paycheck(PaycheckBase, table=True):
    __tablename__ = "paychecks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    pay_date: date = Field(index=True)
    net_pay: Decimal = Field(max_digits=10, decimal_places=2)
    
    # Cascade delete ensures line items are removed if a paycheck is deleted
    items: List["PaycheckLineItem"] = Relationship(
        back_populates="paychecks", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class PaycheckLineItem(PaycheckBase, table=True):
    __tablename__ = "paycheck_line_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    paycheck_id: Optional[int] = Field(
        default=None, 
        foreign_key="paychecks.id"
    )
    category: str = Field(index=True)  # 'Income', 'Taxes', 'Pre-Tax Benefits', etc.
    name: str                          # 'Regular Pay', 'Medical', etc.
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    
    paycheck: Paycheck = Relationship(back_populates="items")