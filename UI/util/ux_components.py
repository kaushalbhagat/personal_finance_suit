# ux_components.py
import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import util.budget.services as services

# --- 1. UNIFIED DATA FETCH LAYER ---

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
        response = requests.get(f"{services.BASE_URL}/transactions/total", params=query_params)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data.get("breakdown", []))
            grand_total = data.get("grand_total", 0.0)
            return df, grand_total
    except Exception as e:
        st.error(f"Financial Summary Service Offline: {e}")
    
    return pd.DataFrame(), 0.0


# --- 2. UNIFIED VISUALIZATION LAYOUTS ---

def render_allocation_pie(df: pd.DataFrame, values_col: str, names_col: str, title: str = None, hole: float = 0.3, color_sequence=None):
    """
    Standardizes user interface layout distributions for chart generation,
    handling layout containers and responsive container expansions uniformly.
    """
    if df.empty or df[values_col].sum() == 0:
        st.info("No records observed inside active context parameters.")
        return None
        
    fig = px.pie(df, values=values_col, names=names_col, hole=hole, title=title, color_discrete_sequence=color_sequence)
    fig.update_layout(
        legend_orientation="v", 
        legend_x=1.02, 
        legend_y=0.5, 
        legend_yanchor="middle",
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return st.plotly_chart(fig, use_container_width=True)


# --- 3. REUSABLE DATA LEDGER GRID (AgGrid Builder) ---

def render_interactive_ledger(df: pd.DataFrame, key: str, hidden_cols: list = None, custom_headers: dict = None, column_widths: dict = None, fit_columns=True) -> list:
    """
    Builds structured, uniform AgGrid data grids.
    Abstracts repetitive currency layout parsers, column configuration widths, and column hides.
    """
    if df.empty:
        return None

    defaults_to_hide = ["id", "category_id", "subcategory_id"]
    cols_to_hide = list(set(defaults_to_hide + (hidden_cols or [])))

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    
    # Hide tracking properties safely
    for col in cols_to_hide:
        if col in df.columns:
            gb.configure_column(col, hide=True)

    # Standardize field headings and default sizing properties
    headers = {
        "date": "Date", "description": "Description", "bank_name": "Account",
        "type": "Type", "category_name": "Category", "subcategory_name": "Sub-Category"
    }
    if custom_headers:
        headers.update(custom_headers)
        
    widths = {"date": 110, "description": 260, "bank_name": 120, "type": 100, "category_name": 160, "subcategory_name": 160, "amount": 120}
    if column_widths:
        widths.update(column_widths)
    
    for field, header_text in headers.items():
        if field in df.columns:
            width = widths.get(field, 150)
            gb.configure_column(field, headerName=header_text, width=width)

    # Apply uniform currency layout strings across dashboards
    money_fields = ["amount", "total_amount", "Total Amount", "Total Revenue", "amount_received"]
    for money_col in money_fields:
        if money_col in df.columns:
            width = widths.get("amount", 120)
            header_name = headers.get(money_col, money_col)
            gb.configure_column(money_col, headerName=header_name, width=width, valueFormatter="`$ ` + x.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})")

    grid_response = AgGrid(
        df, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="streamlit", fit_columns_on_grid_load=fit_columns, key=key
    )
    
    selected_rows = grid_response.get("selected_rows", [])
    if selected_rows is not None and len(selected_rows) > 0:
        return selected_rows.iloc[0] if isinstance(selected_rows, pd.DataFrame) else selected_rows[0]
    return None


# Reusable timeline graph for income expense
# ui/ux_components.py
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

INCOME_CATEGORY_ID = 16

# Shared metadata matrix
SCOPE_MATRIX = {
    "Combined": {
        "report_type": "All", "pie_label": "Combined", "line_title": "Unified Monthly Cash Flow",
    },
    "Personal": {
        "report_type": "Personal", "pie_label": "Personal", "line_title": "Personal Cash Flow",
    },
    "Business": {
        "report_type": "Business", "pie_label": "Business", "line_title": "Business Cash Flow",
    }
}

from datetime import datetime, date
import dateutil.relativedelta as rd
import streamlit as st

def render_global_filters(
    key_prefix: str, 
    show_account_picker: bool = False
) -> tuple[date, date, str, str | None]:
    """
    Renders the Scope and Date Range pickers, an optional Account picker,
    and a fully reactive preset dropdown for fast date ranges.
    """
    state_key = f"{key_prefix}_current_date_val"
    preset_key = f"{key_prefix}_date_preset_sel"
    
    today = date.today()

    # 1. Initialize session states safely
    if state_key not in st.session_state:
        st.session_state[state_key] = (date(2025, 1, 1), today)

    # 2. Define the Callback for when the Preset Dropdown changes
    def on_preset_change():
        selected = st.session_state[preset_key]
        if selected == "This Month":
            st.session_state[state_key] = (today.replace(day=1), today)
        elif selected == "Last Month":
            first_of_this_month = today.replace(day=1)
            last_month_end = first_of_this_month - rd.relativedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            st.session_state[state_key] = (last_month_start, last_month_end)
        elif selected == "YTD":
            st.session_state[state_key] = (date(today.year, 1, 1), today)
        elif selected == "Last Year":
            st.session_state[state_key] = (date(today.year - 1, 1, 1), date(today.year - 1, 12, 31))

    # 3. Setup column layouts
    if show_account_picker:
        col_preset, col_datepicker, col_scope, col_bank = st.columns([1.2, 1.8, 1.5, 1.5])
    else:
        col_preset, col_datepicker, col_scope = st.columns([1.2, 1.8, 2.0])
        col_bank = None

    # 4. Render Preset Dropdown with its callback attached
    with col_preset:
        presets = ["Custom", "This Month", "Last Month", "YTD", "Last Year"]
        st.selectbox(
            "Quick Range",
            options=presets,
            key=preset_key,
            on_change=on_preset_change, # Triggers calculations immediately on selection
            label_visibility="collapsed"
        )

    # 5. Render Main Date Picker (Reading from state_key, NOT using a conflicting key string)
    with col_datepicker:
        selected_range = st.date_input(
            "Time Range", 
            value=st.session_state[state_key],
            label_visibility="collapsed"
        )
        
        # 6. Check if user manually interacted with the date picker bounds
        if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
            start_date, end_date = selected_range
            # If manual date picker value deviates from our state, revert dropdown to "Custom"
            if (start_date, end_date) != st.session_state[state_key]:
                st.session_state[preset_key] = "Custom"
                st.session_state[state_key] = (start_date, end_date)
        elif isinstance(selected_range, (tuple, list)) and len(selected_range) == 1:
            start_date = selected_range[0]
            end_date = today
        else:
            start_date, end_date = st.session_state[state_key]

    # 7. Render Scope Dropdown
    with col_scope:
        selected_scope = st.selectbox(
            "Scope", 
            options=list(SCOPE_MATRIX.keys()), 
            key=f"{key_prefix}_scope_filter_dropdown", 
            label_visibility="collapsed"
        )
        
    # 8. Render Optional Account Dropdown
    selected_bank = None
    if show_account_picker and col_bank is not None:
        with col_bank:
            banks = services.get_bank_names()
            selected_bank = st.selectbox(
                "Account", 
                options=banks, 
                key=f"{key_prefix}_dash_bank_sel",
                label_visibility="collapsed"
            )
            
    return start_date, end_date, selected_scope, selected_bank

def generate_line_chart_df(expense_func, income_func, start_date=None, end_date=None) -> pd.DataFrame:
    """Fetches list logs from API, tags them, and combines them chronologically."""
    # Note: If your underlying API functions support date filtering, 
    # pass start_date and end_date down to expense_func() and income_func() here.
    df_exp = pd.DataFrame(expense_func())
    if not df_exp.empty:
        df_exp["Type"] = "Expense"
    else:
        df_exp = pd.DataFrame(columns=["month", "total", "Type"])
        
    df_inc = pd.DataFrame(income_func())
    if not df_inc.empty:
        df_inc["Type"] = "Income"
    else:
        df_inc = pd.DataFrame(columns=["month", "total", "Type"])
        
    combined_df = pd.concat([df_exp, df_inc], ignore_index=True)
    
    if not combined_df.empty and "month" in combined_df.columns:
        combined_df["month"] = pd.to_datetime(combined_df["month"]).dt.date
        
        # Filter by date range if provided
        if start_date and end_date:
            combined_df = combined_df[
                (combined_df["month"] >= pd.to_datetime(start_date).date()) & 
                (combined_df["month"] <= pd.to_datetime(end_date).date())
            ]
            
        combined_df = combined_df.sort_values("month")
    return combined_df


def render_income_expense_timeline_chart(selected_scope: str, start_date: datetime, end_date: datetime):
    """
    Renders the chart based on parameters passed from the page level.
    This accepts the 'services' module dynamically to avoid circular imports.
    """
    # Map the dynamic service functions based on scope
    service_mapping = {
        "Combined": {
            "expense_fn": services.get_monthly_expenses_summary, 
            "income_fn": services.get_monthly_income_summary
        },
        "Personal": {
            "expense_fn": services.get_monthly_personal_expenses_summary, 
            "income_fn": services.get_monthly_personal_income_summary
        },
        "Business": {
            "expense_fn": services.get_monthly_business_expenses_summary, 
            "income_fn": services.get_monthly_business_income_summary
        }
    }
    
    cfg = SCOPE_MATRIX[selected_scope]
    fns = service_mapping[selected_scope]

    st.markdown(f"#### 🟢 🔴 {cfg['line_title']}")
    
    # Generate DF using the passed-in dates
    df_line = generate_line_chart_df(fns["expense_fn"], fns["income_fn"], start_date, end_date)

    if not df_line.empty:
        fig = px.line(
            df_line, 
            x="month", 
            y="total", 
            color="Type", 
            markers=True, 
            color_discrete_map={"Income": "#2ECC71", "Expense": "#E74C3C"}, 
            labels={"month": "Timeline", "total": "Amount ($)", "Type": "Cash Flow"}
        )
        fig.update_layout(hovermode="x unified", legend_orientation="h", legend_y=1.1)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No timeline transaction patterns discovered under the {cfg['pie_label']} layer.")

# Reusable portfolio performance chart 

from util.portfolio.current_holdings import load_current_holdings
from util.portfolio.historical_timeline import load_historical_timeline
from util.portfolio.daily_snapshots import refresh_daily_snapshot, SnapshotException
def build_portfolio_performance_chart(session):
    timeline_df = load_historical_timeline(session)

    # --- HEADER & REFRESH SNAPSHOT ENGINE ---
    head_col, btn_col = st.columns([5, 1])
    with head_col:
        st.subheader("📈 Portfolio Performance Over Time")

    with btn_col:
        st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Snapshots", use_container_width=True):
            with st.spinner("Processing incremental historical snapshots..."):
                try:
                    days_built = refresh_daily_snapshot(session)
                    if days_built > 0:
                        st.toast(f"Successfully caught up {days_built} days of snapshots!", icon="🚀")
                        st.rerun()
                    else:
                        st.info("No active metrics or missing data tracks to synthesize.")
                except SnapshotException as e:
                    st.toast(e)

    # --- TIMELINE CHART RENDERING ---
    if not timeline_df.empty:
        chart_view = st.radio("Select View", ["Total Aggregate Portfolio", "Breakdown by Account Type"], horizontal=True)
        if chart_view == "Total Aggregate Portfolio":
            aggregate_df = timeline_df.groupby("Date")[["Total Value", "Cash Balance"]].sum()
            st.line_chart(aggregate_df, x_label="Timeline", y_label="Balance ($)", color=["#29b5e8", "#ff4b4b"])
        else:
            pivot_df = timeline_df.pivot_table(index="Date", columns="Account Type", values="Total Value", aggfunc="sum").fillna(0)
            st.line_chart(pivot_df, x_label="Timeline", y_label="Total Account Value ($)")
    else:
        st.info("No snapshot data available yet. Click 'Refresh Snapshots' above to generate points.")