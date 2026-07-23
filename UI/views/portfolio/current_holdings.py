import streamlit as st
from database.setup import get_db
from sqlmodel import select

from util.portfolio.current_holdings import load_current_holdings

with get_db() as session:
    holdings_df = load_current_holdings(session)

    # --- CURRENT HOLDINGS EXPANDERS ---
    st.subheader("📊 Current Equity Holdings (across Account)")
    if not holdings_df.empty:
        equity_only_df = holdings_df[holdings_df["Ticker"] != "CASH"]
        if not equity_only_df.empty:
            # Group by Ticker and aggregate values
            unified_grouped = equity_only_df.groupby("Ticker").agg({
                "Qty": "sum",
                "Cost Basis": "sum",
                "Mkt Val": "sum",
                "Day Chng $": "sum",
                "Gain/Loss $": "sum"
            }).reset_index()
            
            # Calculate weighted average values and performance percentages
            unified_grouped["Price"] = unified_grouped["Mkt Val"] / unified_grouped["Qty"]
            
            # We set change columns to 0.0 or calculate based on aggregated figures
            unified_grouped["Price Chng $"] = 0.0  # Optional: yfinance logic can populate this if needed
            unified_grouped["Price Chng %"] = 0.0
            
            # Compute portfolio change percentages
            prev_mkt_val = unified_grouped["Mkt Val"] - unified_grouped["Day Chng $"]
            unified_grouped["Day Chng %"] = (unified_grouped["Day Chng $"] / prev_mkt_val * 100).fillna(0.0)
            unified_grouped["Gain/Loss %"] = (unified_grouped["Gain/Loss $"] / unified_grouped["Cost Basis"] * 100).fillna(0.0)
            
            # Ensure proper columns exist for formatting
            unified_grouped["Price Chng $"] = unified_grouped["Price Chng $"].astype(float)
            unified_grouped["Price Chng %"] = unified_grouped["Price Chng %"].astype(float)
            
            # Grand totals for the unified header metric
            total_unified_mkt_val = unified_grouped["Mkt Val"].sum()
            total_unified_cost = unified_grouped["Cost Basis"].sum()
            total_unified_gain_loss = unified_grouped["Gain/Loss $"].sum()
            unified_pnl_pct = (total_unified_gain_loss / total_unified_cost * 100) if total_unified_cost > 0 else 0.0
            
            unified_header = f"🌍 UNIFIED PORTFOLIO (ALL ACCOUNTS)  |  Total Value: ${total_unified_mkt_val:,.2f}  ({len(unified_grouped)} Unique Assets)"
            
            with st.expander(unified_header, expanded=True): # Expanded by default to showcase the new unified view
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.caption(f"Combined Cost Basis: ${total_unified_cost:,.2f}")
                metric_col2.markdown(
                    f"<p style='text-align: right; margin: 0; color: {'#2ecc71' if total_unified_gain_loss >= 0 else '#e74c3c'}; font-weight: bold;'>"
                    f"Total Return: ${total_unified_gain_loss:,.2f} ({unified_pnl_pct:.2f}%)</p>", 
                    unsafe_allow_html=True
                )
                
                display_columns = ["Ticker", "Qty", "Price", "Price Chng $", "Price Chng %", "Mkt Val", "Day Chng $", "Day Chng %", "Cost Basis", "Gain/Loss $", "Gain/Loss %"]
                
                def color_returns(val):
                    if isinstance(val, (int, float)) and val != 0:
                        return 'color: #2ecc71; font-weight: bold;' if val > 0 else 'color: #e74c3c; font-weight: bold;'
                    return ''

                styled_unified_df = unified_grouped[display_columns].style.map(
                    color_returns, 
                    subset=["Price Chng $", "Price Chng %", "Day Chng $", "Day Chng %", "Gain/Loss $", "Gain/Loss %"]
                )
                
                st.dataframe(
                    styled_unified_df,
                    column_config={
                        "Ticker": "Asset Ticker",
                        "Qty": st.column_config.NumberColumn("Combined Qty", format="%.4f"),
                        "Price": st.column_config.NumberColumn("Weighted Price", format="$%.2f"),
                        "Price Chng $": st.column_config.NumberColumn("Price Chng $", format="$%.2f"),
                        "Price Chng %": st.column_config.NumberColumn("Price Chng %", format="%.2f%%"),
                        "Mkt Val": st.column_config.NumberColumn("Mkt Val", format="$%.2f"),
                        "Day Chng $": st.column_config.NumberColumn("Day Chng $", format="$%.2f"),
                        "Day Chng %": st.column_config.NumberColumn("Day Chng %", format="%.2f%%"),
                        "Cost Basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f"),
                        "Gain/Loss $": st.column_config.NumberColumn("Gain/Loss $", format="$%.2f"),
                        "Gain/Loss %": st.column_config.NumberColumn("Gain/Loss %", format="%.2f%%"),
                    },
                    use_container_width=True, hide_index=True
                )