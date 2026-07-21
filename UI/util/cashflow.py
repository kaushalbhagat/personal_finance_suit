from collections import defaultdict

import httpx
from datetime import date
from sqlmodel import Session
from util.paycheck.aggregate import create_consolidated_paycheck
from util.budget.services import fetch_totals_breakdown

def gather_consolidated_data(
    db_session: Session, 
    # fastapi_client: httpx.Client, 
    # fastapi_base_url: str, 
    start_date: date, 
    end_date: date
) -> dict:

    cashflow = {
        "Income": {
            "Salary/Bonus/RSU": 0.0,
            "Business": 0.0
        },
        "401K": 0.0,
        "Taxes": 0.0,
        "Deductions": 0.0,
        "Savings": {
            "RSU": 0.0,
            "Other": 0.0
        },
        "Expenses": {
            "Personal": 0.0,
            "Business": 0.0
        }
    }

    paycheck = create_consolidated_paycheck(db_session, start_date, end_date)
    grouped_items = defaultdict(list)
    gross_pay = 0
    savings_rsu = 0
    deductions_401k = 0
    total_deductions = 0
    total_tax = 0

    for item in paycheck.items:
        grouped_items[item.category].append(item)
        if item.category.lower() == 'income':
            gross_pay += item.amount
        elif item.category.lower() == 'rsu':
            savings_rsu += item.amount   
        elif item.category.lower() == 'taxes':
            total_tax += item.amount    
        elif "401K".lower() in item.name.lower():
             deductions_401k += item.amount      
        else:
            total_deductions += item.amount

    cashflow["Income"]["Salary/Bonus/RSU"] = gross_pay
    cashflow["401K"] = deductions_401k
    cashflow["Savings"]["RSU"] = savings_rsu
    cashflow["Deductions"] = total_deductions
    cashflow["Taxes"] = total_tax

    df_category, cat_total = fetch_totals_breakdown(
        level="subcategory", start_date=start_date, end_date=end_date, category_id=16, report_type="business", exclude_from_reporting=True
    )
    cashflow["Income"]["Business"] = cat_total*-1

    df_category, cat_total_p = fetch_totals_breakdown(
        level="subcategory", start_date=start_date, end_date=end_date, category_id=15, report_type="personal"
    )
    df_category, cat_total_b = fetch_totals_breakdown(
        level="subcategory", start_date=start_date, end_date=end_date, category_id=15, report_type="business"
    )    
    cashflow["Savings"]["Other"] = cat_total_p + cat_total_b

    df_category, cat_total = fetch_totals_breakdown(
        level="category", start_date=start_date, end_date=end_date, report_type="business"
    )
    cashflow["Expenses"]["Business"] = cat_total - cat_total_b 

    df_category, cat_total = fetch_totals_breakdown(
        level="category", start_date=start_date, end_date=end_date, report_type="personal"
    )
    cashflow["Expenses"]["Personal"] = cat_total - cat_total_p    

    return cashflow