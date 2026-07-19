from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from model import PlaidAccounts
from database import get_session


router = APIRouter(tags=["Accounts"])

@router.get("/accounts", response_model=List[str])
async def get_account_names(session: Session = Depends(get_session)):
    statement = select(PlaidAccounts.custom_name)
    accounts = await session.exec(statement)
    return accounts