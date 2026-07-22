from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from datetime import date
from decimal import Decimal

from database.paycheck.models import Paycheck, PaycheckLineItem

def get_all_paychecks(session: Session) -> list[Paycheck]:
    statement = (
        select(Paycheck)
        .order_by(Paycheck.pay_date.desc())
    )
    return session.scalars(statement).all()


def get_paycheck_details(session: Session, paycheck_id: int) -> Paycheck | None:
    statement = (
        select(Paycheck)
        .where(Paycheck.id == paycheck_id)
        .options(selectinload(Paycheck.items))  # Eager load line items
    )
    return session.exec(statement).first()