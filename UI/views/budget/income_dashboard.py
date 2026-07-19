# views/income_dashboard.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import util.budget.services as services
import util.ux_components as ux_components

INCOME_CATEGORY_ID = 16
INCOME_CATEGORY_NAME = "Income"

# ==========================================
# 2. STATE RECOVERY TOKENS
# ==========================================
if "cat_reset_token" not in st.session_state: st.session_state.cat_reset_token = 0
if "sub_reset_token" not in st.session_state: st.session_state.sub_reset_token = 0
if "tx_reset_token" not in st.session_state: st.session_state.tx_reset_token = 0

if "cat_tok" not in st.session_state: st.session_state.cat_tok = 0
if "map_tok" not in st.session_state: st.session_state.map_tok = 0
if "master_form_tok" not in st.session_state: st.session_state.master_form_tok = 0
if "sub_form_tok" not in st.session_state: st.session_state.sub_form_tok = 0
if "map_form_tok" not in st.session_state: st.session_state.map_form_tok = 0

if "master_form_open" not in st.session_state: st.session_state.master_form_open = False
if "sub_form_open" not in st.session_state: st.session_state.sub_form_open = False
if "map_form_open" not in st.session_state: st.session_state.map_form_open = False

category_hierarchy, category_map, df_categories_combined = services.fetch_category_pipelines()

st.set_page_config(layout="wide", page_title="Income Dashboard")

if "inc_sub_reset_token" not in st.session_state: st.session_state.inc_sub_reset_token = 0
if "inc_tx_reset_token" not in st.session_state: st.session_state.inc_tx_reset_token = 0

unassigned_only = st.session_state.get("inc_unassigned_toggle", False)

# 1. TOP GLOBAL FILTER BAR
start_date, end_date, selected_scope, selected_bank = ux_components.render_global_filters(key_prefix="expense_dashboard", show_account_picker=True)
selected_type = ux_components.SCOPE_MATRIX[selected_scope].get('report_type')
    
query_params = {"start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d")}
if selected_bank != "All": query_params["bank_name"] = selected_bank
if selected_type != "All": query_params["type"] = selected_type

# 2. MACRO CATEGORY SECTION (Pie Chart Next to Spending Grid Data Table)
# st.subheader("📊 Income Stream Distribution & Velocity")
df_sub, raw_grand_total = services.fetch_totals_breakdown(
    level="subcategory", category_id=INCOME_CATEGORY_ID, exclude_from_reporting=True, start_date=start_date, end_date=end_date, bank_name=selected_bank, report_type=selected_type
)

# Invert negative system transaction fields to positive representations
if not df_sub.empty and "total_amount" in df_sub.columns:
    df_sub["total_amount"] = df_sub["total_amount"] * -1
income_grand_total = raw_grand_total * -1

col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown(f"#### Total Income Earned: `${income_grand_total:,.2f}`")
    ux_components.render_allocation_pie(df_sub.tail(10), "total_amount", "subcategory_name")

selected_sub_stream = "All"
with col_right:
    st.markdown("#### 🔍 Sub-Category Breakdown")
    if not df_sub.empty:
        sub_grid_df = df_sub[["subcategory_name", "total_amount"]].copy()
        selected_sub_row = ux_components.render_interactive_ledger(
            sub_grid_df,
            key=f"income_sub_aggrid_{st.session_state.inc_sub_reset_token}",
            custom_headers={"subcategory_name": "Stream Name", "total_amount": "Total Revenue"}
        )
        if selected_sub_row is not None:
            selected_sub_stream = selected_sub_row["subcategory_name"]
        
        if selected_sub_stream != "All":
            st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("🧹 Clear Stream Filter (Show All Income)", use_container_width=True, key="clear_inc_sub_filter_btn"):
                st.session_state.inc_sub_reset_token += 1
                st.rerun()

st.markdown("---")

# 3. INCOME HISTORICAL TRANSACTION LEDGER
workspace_title = "📝 Income Transaction Ledger"
if selected_sub_stream != "All": 
    workspace_title += f" ➔ Stream Filter: {selected_sub_stream}"
st.subheader(workspace_title)

df_master = services.fetch_workspace_transactions(query_params["start_date"], query_params["end_date"], "All", selected_bank, INCOME_CATEGORY_ID)
if not df_master.empty and "amount" in df_master.columns:
    df_master["amount"] = df_master["amount"] * -1

if not df_master.empty:
    if selected_type != "All":
        df_master = df_master[df_master["type"].str.lower() == selected_type.lower()]
    if unassigned_only:
        df_master = df_master[df_master["subcategory_name"].isna() | (df_master["subcategory_name"] == "") | (df_master["subcategory_name"].str.lower() == "unassigned")]
    if selected_sub_stream != "All":
        df_master = df_master[df_master["subcategory_name"] == selected_sub_stream]

main_col, side_col = st.columns([3, 1])
with main_col:
    search_col, toggle_col = st.columns([2, 1])
    with search_col:
        search = st.text_input("🔍 Filter items...", key="inc_tx_search_inp")
    with toggle_col:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        unassigned_only = st.toggle("Show Unassigned Only", value=False, key="inc_unassigned_toggle")

    display_df = df_master.copy() if not df_master.empty else pd.DataFrame()
    if not display_df.empty and search:
        display_df = display_df[display_df["description"].str.contains(search, case=False, na=False)]
    
    selected_rows_workspace = []
    if not display_df.empty:
        column_order = ["date", "description", "subcategory_name", "amount", "bank_name", "type", "id", "note", "category_id", "subcategory_id", "category_name"]
        display_df = display_df[column_order]

        clicked_ledger_row = ux_components.render_interactive_ledger(
            display_df,
            key=f"income_workspace_aggrid_{st.session_state.inc_tx_reset_token}",
            hidden_cols=["category_name"],
            fit_columns=False
        )
        if clicked_ledger_row is not None:
            selected_rows_workspace = [clicked_ledger_row]
    else:
        st.info("No inbound transactions matching criteria verified.")

# 4. SINGLE-TIER INCOME SUB-CATEGORY ASSIGNMENT DOCK
with side_col:
    st.subheader("Stream Tagging Dock")
    if selected_rows_workspace and not display_df.empty:
        clicked_row = selected_rows_workspace[0]
        target_id = clicked_row["id"]
        row_data = df_master[df_master["id"] == target_id].iloc[0]
        
        st.markdown(f"**Tagging Source Transaction ID: `{target_id}`**")
        new_desc = st.text_input("Description Override", value=row_data["description"], key=f"inc_edit_desc_{target_id}")
        new_amount = st.number_input("Amount Received ($)", value=float(row_data["amount"]), step=0.01, key=f"inc_edit_amt_{target_id}")
        
        sub_hierarchy = category_hierarchy.get(INCOME_CATEGORY_NAME, {}).get("subcategories", {})
        sub_options = list(sub_hierarchy.keys())
        sub_index = sub_options.index(row_data["subcategory_name"]) if row_data["subcategory_name"] in sub_options else None
        
        sub_cat = st.selectbox("Assign Stream Type", options=sub_options, index=sub_index, placeholder="Select income type...", key=f"inc_edit_scat_{target_id}")
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1: save_clicked = st.button("🚀 Save", use_container_width=True, key=f"inc_save_b_{target_id}")
        with btn_col2: cancel_clicked = st.button("❌ Close", use_container_width=True, key=f"inc_cncl_b_{target_id}")
            
        if save_clicked:
            if not sub_cat:
                st.error("Please pick a valid stream classification type before applying changes.")
            else:
                payload = {
                    "id": int(target_id), "date": str(row_data["date"]), "description": new_desc, "type": row_data["type"],
                    "category_id": INCOME_CATEGORY_ID, "subcategory_id": sub_hierarchy.get(sub_cat),
                    "amount": new_amount * -1, "bank_name": row_data["bank_name"], "note": row_data["note"]
                }
                try:
                    update_res = requests.put(f"{services.BASE_URL}/transactions/{target_id}", json=payload)
                    if update_res.status_code in [200, 204]:
                        st.success("Income sub-stream saved!")
                        st.cache_data.clear()
                        st.session_state.inc_tx_reset_token += 1
                        st.rerun()
                    else: 
                        st.error(f"Rejection: {update_res.text}")
                except Exception as e: 
                    st.error(f"HTTP Update Call Failed: {e}")
        
        if cancel_clicked:
            st.session_state.inc_tx_reset_token += 1
            st.rerun()
    else:
        st.info("💡 Highlight any income line item row to modify descriptions or rapidly re-route income types.")