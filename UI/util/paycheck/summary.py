from sqlmodel import Session, case, extract, func, select
from database.paycheck.models import Paycheck, PaycheckLineItem


def monthly(session: Session, year: int):
    """
    Returns Gross Pay, Total Deductions, and Net Pay consolidated by month.
    """
    statement = (
        select(
            extract('month', Paycheck.pay_date).label("month"),
            func.sum(
                case(
                    (PaycheckLineItem.category == "Income", PaycheckLineItem.amount),
                    else_=0
                )
            ).label("gross_pay"),
            func.sum(
                case(
                    (PaycheckLineItem.category != "Income", PaycheckLineItem.amount),
                    else_=0
                )
            ).label("total_deductions"),
            func.sum(Paycheck.net_pay).label("net_pay"),
            func.count(func.distinct(Paycheck.id)).label("paycheck_count")
        )
        .join(PaycheckLineItem, Paycheck.id == PaycheckLineItem.paycheck_id)
        .where(extract('year', Paycheck.pay_date) == year)
        .group_by(extract('month', Paycheck.pay_date))
        .order_by("month")
    )

    return session.execute(statement).scalars()

from datetime import date
from sqlmodel import Session, select, case
from sqlalchemy import func

def get_paycheck_summary_by_date_range(session: Session, start_date: date, end_date: date):
    """
    Returns single consolidated totals (Gross, Deductions, Net) for all 
    paychecks between start_date and end_date.
    """
    statement = (
        select(
            func.sum(
                case(
                    (PaycheckLineItem.category == "Income", PaycheckLineItem.amount),
                    else_=0
                )
            ).label("gross_pay"),
            func.sum(
                case(
                    (PaycheckLineItem.category != "Income", PaycheckLineItem.amount),
                    else_=0
                )
            ).label("total_deductions"),
            func.sum(Paycheck.net_pay).label("net_pay"),
            func.count(func.distinct(Paycheck.id)).label("paycheck_count")
        )
        .join(PaycheckLineItem, Paycheck.id == PaycheckLineItem.paycheck_id)
        .where(Paycheck.pay_date >= start_date)
        .where(Paycheck.pay_date <= end_date)
    )

    return session.execute(statement).one_or_none()