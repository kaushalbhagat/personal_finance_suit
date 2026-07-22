from typing import List, Literal
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, desc, func, select
from sqlalchemy.orm import selectinload
from schema import DetailedTransactionResponse, TransactionCreate, TransactionFilter, TransactionReportResponse, TransactionResponse
from model import Category, SubCategory, Transaction
from database import get_session
from services.mapping import get_mapping_for_description_helper


router = APIRouter(tags=["Transactions"])

@router.get("/transactions", response_model=List[DetailedTransactionResponse], tags=["Transactions"])
async def get_transactions(data: TransactionFilter = Depends(), session: Session = Depends(get_session)):
    statement = select(Transaction)
    if data.start_date:
        statement = statement.where(Transaction.date >= data.start_date)
    if data.end_date:
        statement = statement.where(Transaction.date <= data.end_date)    
    if data.type:
        statement = statement.where(func.lower(Transaction.type) == data.type.lower())        
    if data.category_id:
        statement = statement.where(Transaction.category_id == data.category_id)   
    if data.subcategory_id:
        statement = statement.where(Transaction.subcategory_id == data.subcategory_id) 
    if data.bank_name:
        statement = statement.where(Transaction.bank_name == data.bank_name)    
    if data.description:
        statement = statement.where(Transaction.description.like(f"%{data.description}%"))           

    statement = statement.options(
        selectinload(Transaction.category), 
        selectinload(Transaction.subcategory)
    )

    statement = statement.order_by(desc(Transaction.date))

    result = await session.exec(statement)
    return result

@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, tags=["Transactions"])
async def create_mapping(data: TransactionCreate, session: Session = Depends(get_session)):
    new_transaction = Transaction.model_validate(data)
    if not data.category_id:
        mapping = await get_mapping_for_description_helper(data.description, session=session)
        if mapping.is_matched:
            new_transaction.category_id = mapping.category.id
            new_transaction.subcategory_id = mapping.subcategory.id
    if data.note:
        new_transaction.note = data.note 
    session.add(new_transaction)
    await session.commit()
    await session.refresh(new_transaction)
    return new_transaction

@router.put("/transactions/{transaction_id}", response_model=TransactionResponse, tags=["Transactions"])
async def update_transaction(transaction_id: int, data: TransactionCreate, session: Session = Depends(get_session)):
    db_transaction = await session.get(Transaction, transaction_id)
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Extract data matching the TransactionCreate schema
    transaction_data = data.model_dump(exclude_unset=True)
    for key, value in transaction_data.items():
        setattr(db_transaction, key, value)
        
    session.add(db_transaction)
    await session.commit()
    await session.refresh(db_transaction)
    return db_transaction

@router.get("/transactions/total", response_model=TransactionReportResponse, tags=["Transactions"])
async def get_transactions_total(
    # Add a parameter to toggle between grouping by category or subcategory
    level: Literal["category", "subcategory"] = Query("category", description="Group by category or subcategory"),
    data: TransactionFilter = Depends(), 
    session: AsyncSession = Depends(get_session)
):
    if level == "category":
        statement = select(
            Category.name.label("category_name"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount")
        ).select_from(
            Transaction
        ).outerjoin(
            Category, Transaction.category_id == Category.id
        ).group_by(
            Category.name
        ).order_by(
            desc("total_amount")
        )
    else:
        if data.separate_by_type:
            statement = select(
                Transaction.type.label("type"),
                Category.name.label("category_name"),
                SubCategory.name.label("subcategory_name"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total_amount")
            ).select_from(
                Transaction
            ).outerjoin(
                Category, Transaction.category_id == Category.id
            ).outerjoin(
                SubCategory, Transaction.subcategory_id == SubCategory.id
            ).group_by(
                Transaction.type,
                Category.name, 
                SubCategory.name
            ).order_by(
                Category.name
            )        
        else:
            statement = select(
                Category.name.label("category_name"),
                SubCategory.name.label("subcategory_name"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total_amount")
            ).select_from(
                Transaction
            ).outerjoin(
                Category, Transaction.category_id == Category.id
            ).outerjoin(
                SubCategory, Transaction.subcategory_id == SubCategory.id
            ).group_by(
                Category.name, 
                SubCategory.name
            ).order_by(
                desc("total_amount")
            ) 

    # 3. Apply your TransactionFilter criteria
    if data.start_date:
        statement = statement.where(Transaction.date >= data.start_date)
    if data.end_date:
        statement = statement.where(Transaction.date <= data.end_date)
    if data.type:
        statement = statement.where(func.lower(Transaction.type) == data.type.lower()) 
    if data.bank_name:
        statement = statement.where(Transaction.bank_name == data.bank_name)
    if data.category_id:
        statement = statement.where(Transaction.category_id == data.category_id)   
    if data.subcategory_id:
        statement = statement.where(Transaction.subcategory_id == data.subcategory_id)

    statement = statement.where(Category.exclude_from_reporting == data.exclude_from_reporting)

    # 1. Fetch all rows into memory
    result = await session.exec(statement)
    rows = result.all()
    
    # 2. Calculate the grand total using a quick Python loop
    # Since SQLAlchemy Row items act like objects, we can look up .total_amount directly
    total_sum = sum(row.total_amount for row in rows)
    
    # 3. Return a dictionary that matches your new Pydantic schema layout
    return {
        "grand_total": total_sum,
        "breakdown": rows
    }

@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: int, session: Session = Depends(get_session)):
    """
    Permanently deletes a transaction by ID.
    Returns HTTP 204 No Content on success.
    """
    db_transaction = await session.get(Transaction, transaction_id)
    
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found."
        )
    
    await session.delete(db_transaction)
    await session.commit()
    
    # HTTP 204 responses must not return a body
    return None