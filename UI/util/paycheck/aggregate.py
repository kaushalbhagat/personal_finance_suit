from datetime import date
from decimal import Decimal
from typing import List
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from database.paycheck.models import Paycheck, PaycheckLineItem
from database.setup import get_paycheck_db


def create_consolidated_paycheck(session: Session, start_date: date, end_date: date) -> Paycheck:
    """
    Executes aggregated queries over a list of paycheck IDs and constructs
    an unpersisted, consolidated 'Paycheck' object.
    """

    # 1. Aggregate net pay across the paychecks
    sum_net_pay_stmt = (
        select(func.sum(Paycheck.net_pay))
        .where(Paycheck.pay_date >= start_date)
        .where(Paycheck.pay_date <= end_date)         
    )
    total_net_pay = session.scalar(sum_net_pay_stmt) or Decimal("0.00")

    # 2. Aggregate line items and find the latest pay date
    items_stmt = (
        select(
            func.max(Paycheck.pay_date).label("latest_pay_date"),
            PaycheckLineItem.category,
            PaycheckLineItem.name,
            func.sum(PaycheckLineItem.amount).label("total_amount")
        )
        .join(PaycheckLineItem, Paycheck.id == PaycheckLineItem.paycheck_id)
        .where(Paycheck.pay_date >= start_date)
        .where(Paycheck.pay_date <= end_date)         
        .group_by(PaycheckLineItem.category, PaycheckLineItem.name)
    )
    
    results = session.execute(items_stmt).all()

    # Extract maximum pay date and build aggregated line items
    latest_pay_date = date.today()
    consolidated_items: List[PaycheckLineItem] = []

    for row in results:
        max_date, category, name, total_amount = row
        if max_date:
            latest_pay_date = max_date
            
        consolidated_items.append(
            PaycheckLineItem(
                category=category,
                name=name,
                amount=total_amount
            )
        )

    # 3. Construct and return the unpersisted Paycheck object
    return Paycheck(
        id=None,
        pay_date=latest_pay_date,
        net_pay=total_net_pay,
        items=consolidated_items
    )

if __name__ == "__main__":
    today = date.today()
    with get_paycheck_db() as session:
        paycheck = create_consolidated_paycheck(session, today.replace(day=1), today)
        print(paycheck)
