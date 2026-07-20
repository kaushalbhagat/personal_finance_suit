from datetime import date

import streamlit as st
import pandas as pd
from collections import defaultdict

from util import ux_components
from database.setup import get_paycheck_db
from util.paycheck.aggregate import create_consolidated_paycheck

def render_paycheck_dashboard(paycheck):
    st.header(f"Paycheck Overview: {paycheck.pay_date.strftime('%B %d, %Y')}")
    
    # 1. Calculate the high-level totals
    gross_pay = 0
    rsu_pay = 0
    total_deductions = 0
    grouped_items = defaultdict(list)
    
    for item in paycheck.items:
        grouped_items[item.category].append(item)
        if item.category.lower() == 'income':
            gross_pay += item.amount
        elif item.category.lower() == 'rsu':
            rsu_pay += item.amount            
        else:
            total_deductions += item.amount
            
    # 2. Render the Summary Cards
    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Gross Pay", value=f"${gross_pay:,.2f}")
    with col2:
        st.metric(label="RSU", value=f"${rsu_pay:,.2f}")        
    with col3:
        # Show deductions as a negative impact
        st.metric(label="Total Deductions", value=f"${total_deductions:,.2f}")
    with col4:
        # Net pay comes straight from the top-level model
        st.metric(label="Net Take-Home", value=f"${paycheck.net_pay:,.2f}")
        
    st.divider()
    
    # 3. Render the Grouped Line Items (Accordions)
    st.subheader("Detailed Breakdown")
    
    # Define a custom sort order so Income is always first, Taxes next, etc.
    category_order = ["Income", "RSU", "Pre-Tax Benefits", "Taxes", "Post-Tax Deductions"]
    sorted_categories = sorted(
        grouped_items.keys(), 
        key=lambda x: category_order.index(x) if x in category_order else 99
    )
    
    for category in sorted_categories:
        items = grouped_items[category]
        category_total = sum(item.amount for item in items)
        
        # The expander title shows the category and its total
        with st.expander(f"**{category}** — ${category_total:,.2f}"):
            # Convert line items to a DataFrame for clean table rendering
            df = pd.DataFrame([
                {"Name": item.name, "Amount": float(item.amount)} 
                for item in items
            ])
            
            # Format the Amount column as currency
            st.dataframe(
                df, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Amount": st.column_config.NumberColumn(format="$%.2f")
                }
            )

import plotly.graph_objects as go
import streamlit as st
from collections import defaultdict

def render_paycheck_waterfall(paycheck):
    # 1. Aggregate line items by category
    category_totals = defaultdict(float)
    gross_pay = 0.0
    
    for item in paycheck.items:
        amount = float(item.amount)
        if item.category.lower() == 'income':
            gross_pay += amount
        else:
            category_totals[item.category] += amount

    # 2. Build the chart data series
    # Start with Gross Pay
    measures = ["absolute"]
    x_labels = ["Gross Pay"]
    y_values = [gross_pay]
    
    # Add each deduction category as a relative negative value
    for category, total in category_totals.items():
        measures.append("relative")
        x_labels.append(category)
        y_values.append(-total)  # Negative so it steps down
        
    # End with Net Pay as the final total bar
    measures.append("total")
    x_labels.append("Net Take-Home")
    y_values.append(float(paycheck.net_pay))

    # 3. Create the Plotly Waterfall Figure
    fig = go.Figure(go.Waterfall(
        name="Paycheck Flow",
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_values,
        textposition="outside",
        # Format the floating text labels as currency
        text=[f"${abs(val):,.2f}" for val in y_values],
        # Custom color styling: Green for gross/net, Red for deductions
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#27ae60"}},
        connector={"line": {"color": "rgb(150, 150, 150)", "dash": "dot"}}
    ))

    fig.update_layout(
        title="Paycheck Breakdown Flow",
        showlegend=False,
        yaxis_title="Amount ($)",
        yaxis=dict(tickprefix="$"),
        height=450,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    # 4. Display in Streamlit
    st.plotly_chart(fig, use_container_width=True)

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from database.paycheck.models import Paycheck, PaycheckLineItem

def get_paycheck_details(session: Session, paycheck_id: int) -> Paycheck:
    statement = (
        select(Paycheck)
        .where(Paycheck.id == paycheck_id)
        .options(selectinload(Paycheck.items))
    )
    return session.execute(statement).scalars().one()

def execute():
    with get_paycheck_db() as session:
        paycheck = get_paycheck_details(session, 2)
        render_paycheck_dashboard(paycheck)

        render_paycheck_waterfall(paycheck)

# execute()

import calendar
import pandas as pd
import streamlit as st
from util.paycheck.summary import monthly, get_paycheck_summary_by_date_range

def render_monthly_paycheck_summary(session: Session, year: int):
    raw_data = monthly(session, year)
    
    if not raw_data:
        st.warning(f"No paycheck data found for {year}.")
        return

    # Convert results to DataFrame
    df = pd.DataFrame([
        {
            "Month": calendar.month_name[int(row.month)],
            "Paychecks": row.paycheck_count,
            "Gross Pay": float(row.gross_pay),
            "Total Deductions": float(row.total_deductions),
            "Net Take-Home": float(row.net_pay),
        }
        for row in raw_data
    ])

    st.subheader(f"Consolidated Monthly Overview — {year}")
    
    # Display styled interactive table
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Gross Pay": st.column_config.NumberColumn(format="$%.2f"),
            "Total Deductions": st.column_config.NumberColumn(format="$%.2f"),
            "Net Take-Home": st.column_config.NumberColumn(format="$%.2f"),
        }
    )

def render_date_range_summary(session: Session):
    st.subheader("Period Summary")

    # Date Range Controls
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date(2026, 1, 1))
    with col2:
        end_date = st.date_input("End Date", value=date(2026, 12, 31))

    if start_date > end_date:
        st.error("Start Date must be before or equal to End Date.")
        return

    result = get_paycheck_summary_by_date_range(session, start_date, end_date)

    # Handle cases where no paychecks exist in the range
    if not result or result.paycheck_count == 0:
        st.info("No paychecks found in the selected date range.")
        return

    gross = float(result.gross_pay or 0)
    deductions = float(result.total_deductions or 0)
    net = float(result.net_pay or 0)

    st.caption(f"Consolidated total across **{result.paycheck_count}** paycheck(s)")

    # Display clean top-level metric cards
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Gross Pay", f"${gross:,.2f}")
    with m2:
        st.metric("Total Deductions", f"${deductions:,.2f}", delta=f"-${deductions:,.2f}", delta_color="inverse")
    with m3:
        st.metric("Net Take-Home", f"${net:,.2f}")

# with get_paycheck_db() as session:
#     render_date_range_summary(session)

with get_paycheck_db() as session:

    start_date, end_date, selected_scope, selected_bank = ux_components.render_global_filters(key_prefix="paycheck_summary", show_scope_picker=False)
    paycheck = create_consolidated_paycheck(session, [2,3], start_date, end_date)
    render_paycheck_dashboard(paycheck)

