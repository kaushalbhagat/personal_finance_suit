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

with get_paycheck_db() as session:

    start_date, end_date, selected_scope, selected_bank = ux_components.render_global_filters(key_prefix="paycheck_summary", show_scope_picker=False)
    paycheck = create_consolidated_paycheck(session, [2,3], start_date, end_date)
    render_paycheck_dashboard(paycheck)

