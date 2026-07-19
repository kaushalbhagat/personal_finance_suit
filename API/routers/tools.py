from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlmodel import Session, select
from schema import MonthlyReportResponse
from database import get_session
from schema import MonthlyReport

router = APIRouter(tags=["Tools"])

VIEW_LOOKUP = {
            ("Expense", None): "v_monthly_expenses_summary",
            ("Expense", "Business"): "v_monthly_business_expenses_summary",
            ("Expense", "Personal"): "v_monthly_personal_expenses_summary",
            
            ("Income", None): "v_monthly_income_summary",
            ("Income", "Business"): "v_monthly_business_income_summary",
            ("Income", "Personal"): "v_monthly_personal_income_summary",
        }

@router.get("/tools/monthly_report", response_model=List[MonthlyReportResponse])
async def get_monthly_expense_summary(data: MonthlyReport = Depends(), session: Session = Depends(get_session)):
    view_name = VIEW_LOOKUP.get((data.category, data.type))

    if not view_name:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported configuration combo: category='{data.category}', type='{data.type}'"
        )
    
    # This string interpolation is 100% safe from injection because 'view_name' 
    # is strictly sourced from our internal whitelisted dictionary.
    query = text(f"SELECT * FROM {view_name} ORDER BY month ASC;")
    result = await session.execute(query)
    
    # Convert Database Rows to Pydantic Response Outputs
    # .mappings() changes row tuples into dictionaries, making Pydantic translation effortless
    return [MonthlyReportResponse(**row) for row in result.mappings()]



