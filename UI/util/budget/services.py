# services.py
from typing import Any, Dict, List, Optional

import streamlit as st
import pandas as pd
import requests

BASE_URL = "http://localhost:8000"

def fetch_category_pipelines():
    """Fetches categories from backend and generates structured hierarchies/lookups."""
    category_hierarchy = {}
    category_map = {}
    combined_cat_rows = []

    try:
        res = requests.get(f"{BASE_URL}/categories")
        if res.status_code == 200:
            raw_categories = res.json()
            for c in raw_categories:
                sub_map = {sub["name"]: sub["id"] for sub in c.get("subcategories", [])}
                
                # Setup core lookup indexes
                category_hierarchy[c["name"]] = {"id": c["id"], "subcategories": sub_map}
                category_map[c["name"]] = c["id"]
                
                # Process flattened data rows for the AgGrid Registry
                subs = c.get("subcategories", [])
                exclude_rep = c.get("exclude_from_reporting", False)
                
                if not subs:
                    combined_cat_rows.append({
                        "Category Name": c["name"], "Sub Category Name": "—", "Type": "Master Category",
                        "ID": c["id"], "Parent ID": None, "Exclude from Reporting": exclude_rep
                    })
                for sub in subs:
                    combined_cat_rows.append({
                        "Category Name": c["name"], "Sub Category Name": sub["name"], "Type": "Sub-Category",
                        "ID": sub["id"], "Parent ID": c["id"], "Exclude from Reporting": exclude_rep
                    })
    except Exception as e:
        st.error(f"Global Pipeline Interrupted - Reference Category Tree Fetch Failed: {e}")

    return category_hierarchy, category_map, pd.DataFrame(combined_cat_rows)


@st.cache_data(ttl=2)
def fetch_workspace_transactions(start_str, end_str, acct_type, bank, cat_id):
    """Fetches and formats transaction logs based on filter expressions."""
    params = {"start_date": start_str, "end_date": end_str}
    if acct_type != "All": params["type"] = acct_type
    if bank != "All": params["bank_name"] = bank
    if cat_id: params["category_id"] = cat_id
    
    try:
        res = requests.get(f"{BASE_URL}/transactions/", params=params)
        if res.status_code == 200:
            flat_rows = []
            for t in res.json():
                cat_obj, sub_obj = t.get("category") or {}, t.get("subcategory") or {}
                flat_rows.append({
                    "id": t.get("id"), "date": t.get("date"), "description": t.get("description"),
                    "type": t.get("type"), "amount": t.get("amount"), "bank_name": t.get("bank_name"),
                    "note": t.get("note") if t.get("note") is not None else "",
                    "category_name": cat_obj.get("name", "Uncategorized"), "subcategory_name": sub_obj.get("name", "None"),
                    "category_id": t.get("category_id"), "subcategory_id": t.get("subcategory_id"),
                })
            return pd.DataFrame(flat_rows)
    except Exception as e:
        st.error(f"Workspace loading failed: {e}")
    return pd.DataFrame()

def get_new_plaid_link_token():
    res = requests.post(f"{BASE_URL}/create_link_token")
    return res.json().get("link_token") if res.status_code == 200 else None

def trigger_bank_sync():
    res = requests.post(f"{BASE_URL}/transactions/sync")
    return res.json() if res.status_code == 200 else {"status": "failed", "count": 0}

def get_institution_balances() -> list:
    """Fetches the grouped institution and account balance tree matrix."""
    try:
        res = requests.get(f"{BASE_URL}/balances")
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        print(f"Network error fetching balances: {e}")
        return []

def trigger_balance_sync() -> dict:
    """Forces the backend to execute a live real-time Plaid API sync loop."""
    try:
        res = requests.post(f"{BASE_URL}/balances/sync")
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": res.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def update_account_metadata(account_id: str, custom_name: str | None, classification_type: str) -> dict:
    """Sends customization payload updates to the API backend."""
    try:
        payload = {
            "custom_name": custom_name,
            "classification_type": classification_type
        }
        res = requests.put(f"{BASE_URL}/balances/accounts/{account_id}", json=payload)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": res.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    

def get_mapping_for_description(description: str):
        res = requests.get(f"{BASE_URL}/mappings/match/{description}")
        return res.json()

def get_bank_names():
    try:
        res = requests.get(f"{BASE_URL}/accounts")
        return ["All", "Unknown"] + res.json()
    except Exception as e:
        return []


def fetch_totals_breakdown(level: str, start_date, end_date, category_id=None, report_type="All", bank_name="All", exclude_from_reporting=None) -> tuple[pd.DataFrame, float]:
    """
    Centralizes execution loops targeting the /transactions/total endpoint.
    Handles automated string conversion constraints and baseline object checking.
    """
    query_params = {
        "start_date": start_date.strftime("%Y-%m-%d") if hasattr(start_date, "strftime") else str(start_date),
        "end_date": end_date.strftime("%Y-%m-%d") if hasattr(end_date, "strftime") else str(end_date),
        "level": level
    }
    if report_type != "All": query_params["type"] = report_type
    if bank_name != "All": query_params["bank_name"] = bank_name
    if category_id is not None: query_params["category_id"] = category_id
    if exclude_from_reporting is not None: query_params["exclude_from_reporting"] = exclude_from_reporting

    try:
        response = requests.get(f"{BASE_URL}/transactions/total", params=query_params)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data.get("breakdown", []))
            grand_total = data.get("grand_total", 0.0)
            return df, grand_total
    except Exception as e:
        st.error(f"Financial Summary Service Offline: {e}")
    
    return pd.DataFrame(), 0.0

def fetch_monthly_report(category: str, report_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Core dynamic engine mapping structural query variables to the backend GET endpoint.
    """
    # Formulate query parameters matching the schema expected by the backend
    params = {"category": category}
    if report_type:
        params["type"] = report_type

    try:
        # to cleanly align with the FastAPI HTTP query parameters layout.
        res = requests.get(f"{BASE_URL}/tools/monthly_report", params=params)
        
        if res.status_code == 200:
            return res.json()
        
        # 🛡️ UI Defensiveness: Inform user via Streamlit alerts without breaking the layout
        st.error(f"⚠️ Report Fetch Failed ({res.status_code}): {res.text}")
        return []
        
    except Exception as e:
        st.error(f"❌ Network/Connection error generating report: {e}")
        return []

# --- 🚀 CLEAN, AUTO-COMPLETING WRAPPER FUNCTIONS ---

def get_monthly_expenses_summary() -> List[Dict[str, Any]]:
    return fetch_monthly_report(category="Expense")

def get_monthly_income_summary() -> List[Dict[str, Any]]:
    return fetch_monthly_report(category="Income")

def get_monthly_business_expenses_summary() -> List[Dict[str, Any]]:
    return fetch_monthly_report(category="Expense", report_type="Business")

def get_monthly_personal_expenses_summary() -> List[Dict[str, Any]]:
    return fetch_monthly_report(category="Expense", report_type="Personal")

def get_monthly_business_income_summary() -> List[Dict[str, Any]]:
    return fetch_monthly_report(category="Income", report_type="Business")

def get_monthly_personal_income_summary() -> List[Dict[str, Any]]:
    return fetch_monthly_report(category="Income", report_type="Personal")

def get_monthly_report_as_df(category: str, report_type: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches raw JSON report data and wraps it safely in a structured Pandas DataFrame.
    """
    data = fetch_monthly_report(category, report_type)
    if not data:
        return pd.DataFrame(columns=["month", "total"])
        
    df = pd.DataFrame(data)
    # Convert 'month' from string type to a standard date object for timeline sorting/plotting
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"]).dt.date
    return df

def connect_new_bank(link_token):
    try:
        res = requests.get(f"http://localhost:8000/bank_connect?token={link_token}")
        if res.status_code == 200:
            return res
    except Exception as e:
        st.error("Could not fetch a valid Link Token from backend service. Verify server connection status.")