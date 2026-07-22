# views/expense_dashboard.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import util.budget.services as services
import util.ux_components as ux_components


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

st.set_page_config(layout="wide", page_title="Expense Dashboard")

# 1. TOP GLOBAL FILTER BAR
start_date, end_date, selected_scope, selected_bank = ux_components.render_global_filters(key_prefix="expense_dashboard", show_account_picker=True)
selected_type = ux_components.SCOPE_MATRIX[selected_scope].get('report_type')

query_params = {"start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d")}
if selected_type != "All": query_params["type"] = selected_type
if selected_bank != "All": query_params["bank_name"] = selected_bank

# 2. MACRO CATEGORY SECTION (Pie Chart Next to Spending Grid Data Table)
# st.subheader("📊 Macro Category Breakdown")
df_category, cat_total = services.fetch_totals_breakdown(
    level="category", start_date=start_date, end_date=end_date, report_type=selected_type, bank_name=selected_bank
)

col_macro_left, col_macro_right = st.columns([1, 1])

with col_macro_left:
    st.markdown(f"#### Grand Total Spending: `${cat_total:,.2f}`")
    ux_components.render_allocation_pie(df_category.head(10), "total_amount", "category_name")

selected_category_name = "All"
with col_macro_right:
    st.markdown("#### 🗂️ Categories Selection Registry")
    if not df_category.empty:
        grid_df = df_category[["category_name", "total_amount"]].copy()
        selected_row = ux_components.render_interactive_ledger(
            grid_df,
            key=f"category_aggrid_{st.session_state.cat_reset_token}",
            custom_headers={"category_name": "Category Name", "total_amount": "Total Amount"}
        )
        # FIX: Explicit check against None
        if selected_row is not None:
            # st.write(selected_row.index.tolist())
            selected_category_name = selected_row["category_name"]
        
        if selected_category_name != "All":
            if st.button("🧹 Clear Category Filter (Show All Transactions)", use_container_width=True, key="clear_cat_filter_btn"):
                st.session_state.cat_reset_token += 1
                st.session_state.sub_reset_token += 1
                st.rerun()

st.markdown("---")

# 3. DYNAMIC SUB-CATEGORY DRILL DOWN
selected_category_id = None
selected_subcategory_name = "All"

if not df_category.empty and category_map and selected_category_name != "All":
    # st.subheader(f"🔍 Sub-Category Drill Down: {selected_category_name}")
    selected_category_id = category_map.get(selected_category_name)
    
    df_sub, sub_total = services.fetch_totals_breakdown(
        level="subcategory", category_id=selected_category_id, start_date=start_date, end_date=end_date, report_type=selected_type, bank_name=selected_bank
    )

    col_sub_left, col_sub_right = st.columns([1, 1])

    with col_sub_left:
        st.markdown(f"#### Sub-Tier Total for {selected_category_name}: `${sub_total:,.2f}`")
        ux_components.render_allocation_pie(df_sub, "total_amount", "subcategory_name")

    with col_sub_right:
        st.markdown("#### 🔍 Sub-Categories Filter Selection")
        if not df_sub.empty:
            sub_grid_df = df_sub[["subcategory_name", "total_amount"]].copy()
            selected_sub_row = ux_components.render_interactive_ledger(
                sub_grid_df,
                key=f"subcategory_aggrid_{selected_category_name}_{st.session_state.sub_reset_token}",
                custom_headers={"subcategory_name": "Sub-Category Name", "total_amount": "Total Amount"}
            )
            # FIX: Explicit check against None
            if selected_sub_row is not None:
                selected_subcategory_name = selected_sub_row["subcategory_name"]

            if selected_subcategory_name != "All":
                if st.button(f"↩️ Reset to Full {selected_category_name} View", use_container_width=True, key="reset_sub_view_btn"):
                    st.session_state.sub_reset_token += 1
                    st.rerun()
    st.markdown("---")

# 4. BOTTOM LEDGER WORKSPACE
workspace_title = f" Live Transaction Workspace — View: {selected_category_name}"
if selected_subcategory_name != "All": 
    workspace_title += f" ➔ Sub-Category: {selected_subcategory_name}"

ws_head_left, ws_head_right = st.columns([4.2, 1.8], vertical_alignment="center")
with ws_head_left:
    st.subheader(workspace_title)
with ws_head_right:
    if st.button("🚀 Run Live Sync Pipeline", key="workspace_global_sync_trigger", use_container_width=True):
        with st.spinner("Streaming encrypted bank data rows..."):
            try:
                sync_result = services.trigger_bank_sync()
                if sync_result.get("status") == "synced":
                    st.success(f"Success! Imported {sync_result.get('total_imported')} fresh transaction line items.")
                    st.cache_data.clear() 
                    st.rerun()
                else:
                    st.error("Sync routine rejected. Ensure bank link authorization token remains active.")
            except Exception as e:
                st.error(f"Sync failed to run completely: {e}")

df_master = services.fetch_workspace_transactions(query_params["start_date"], query_params["end_date"], selected_type, selected_bank, selected_category_id)
if not df_master.empty and selected_subcategory_name != "All":
    df_master = df_master[df_master["subcategory_name"] == selected_subcategory_name]

main_col, side_col = st.columns([3, 1])
with main_col:
    src_col, tgl_col = st.columns([2, 1])
    with src_col:
        search = st.text_input("🔍 Search within filtered list...", key="tx_search_inp")
    with tgl_col:
        st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
        show_unassigned_only = st.toggle("⚠️ Show Unassigned Only (TODO)", value=False, key="tx_todo_toggle")
        
    display_df = df_master.copy()
    if show_unassigned_only and not display_df.empty:
        display_df = display_df[
            display_df["category_name"].isna() | 
            (display_df["category_name"] == "") | 
            (display_df["category_name"].str.lower() == "uncategorized") |
            (display_df["category_name"] == "None")
        ]

    if not display_df.empty and search:
        display_df = display_df[display_df["description"].str.contains(search, case=False, na=False)]
    
    selected_rows_workspace = []
    if not display_df.empty:
        column_order = ["date", "description", "category_name", "subcategory_name", "amount", "bank_name", "type", "id", "note", "category_id", "subcategory_id"]
        display_df = display_df[column_order]               
        
        clicked_workspace_row = ux_components.render_interactive_ledger(
            display_df,
            key=f"workspace_aggrid_{selected_category_name}_{selected_subcategory_name}_{st.session_state.tx_reset_token}",
            fit_columns=False
        )
        # FIX: Explicit check against None avoids ambiguity errors on Series evaluation
        if clicked_workspace_row is not None:
            selected_rows_workspace = [clicked_workspace_row]
    else:
        st.info("No matching data entries verified matching target queries criteria.")

with side_col:
    st.subheader("Assignment Dock")
    if selected_rows_workspace and not display_df.empty:
        clicked_row = selected_rows_workspace[0]
        target_id = clicked_row["id"]
        row_data = df_master[df_master["id"] == target_id].iloc[0]
        st.markdown(f"**Modifying Transaction ID: `{target_id}`**")
        
        new_desc = st.text_input("Description", value=row_data["description"], key=f"tx_edit_desc_{target_id}")
        new_amount = st.number_input("Amount ($)", value=float(row_data["amount"]), step=0.01, key=f"tx_edit_amt_{target_id}")
        
        if "active_dock_id" not in st.session_state or st.session_state["active_dock_id"] != target_id:
            st.session_state["active_dock_id"] = target_id
            st.session_state["dock_category"] = row_data["category_name"] if pd.notna(row_data["category_name"]) else None
            st.session_state["dock_subcategory"] = row_data["subcategory_name"] if pd.notna(row_data["subcategory_name"]) else None

        cat_options = list(category_hierarchy.keys())

        lbl_col, btn_col = st.columns([2.5, 1.5])
        with lbl_col:
            st.markdown("<p style='font-size: 14px; font-weight: 500; margin-bottom: 0px;'>Assign Category</p>", unsafe_allow_html=True)
        with btn_col:
            if st.button("🪄 Auto-Match", key=f"tx_suggest_{target_id}", use_container_width=True):
                match_res = services.get_mapping_for_description(new_desc)
                if match_res and match_res.get("is_matched"):
                    s_cat = match_res.get("category", {}).get("name")
                    s_sub = match_res.get("subcategory", {}).get("name")
                    st.session_state["dock_category"] = s_cat
                    st.session_state["dock_subcategory"] = s_sub
                    st.toast(f"Rule Matched: {s_cat} ➔ {s_sub or 'None'}", icon="✨")
                    st.rerun()
                else:
                    st.toast("No rule match found for this description.", icon="ℹ️")

        if st.session_state["dock_category"] not in cat_options:
            st.session_state["dock_category"] = None

        parent_cat = st.selectbox("Assign Category", options=cat_options, placeholder="Select a category...", key="dock_category", label_visibility="collapsed")
        
        if parent_cat:
            sub_hierarchy = category_hierarchy.get(parent_cat, {}).get("subcategories", {})
            sub_options = list(sub_hierarchy.keys())
        else:
            sub_hierarchy = {}
            sub_options = []
            
        if st.session_state["dock_subcategory"] not in sub_options:
            st.session_state["dock_subcategory"] = None
        
        sub_cat = st.selectbox("Assign Sub-Category", options=sub_options, placeholder="Select a sub-category...", key="dock_subcategory", disabled=not parent_cat)
        new_note = st.text_input("Note", value=row_data["note"], key=f"tx_edit_note_{target_id}")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1: save_clicked = st.button("🚀 Save", use_container_width=True, key=f"tx_save_b_{target_id}")
        with btn_col2: cancel_clicked = st.button("❌ Close", use_container_width=True, key=f"tx_cncl_b_{target_id}")
            
        st.divider()

        # --- NEW: Delete Action Section with Confirmation ---
        if st.checkbox("⚠️ Enable Delete Option", key=f"confirm_del_chk_{target_id}"):
            if st.button("🗑️ Permanently Delete Transaction", type="primary", use_container_width=True, key=f"tx_del_b_{target_id}"):
                try:
                    delete_response = services.delete_transaction(target_id)
                    if delete_response.get("status") == "success":
                        st.toast("Transaction successfully deleted!", icon="🗑️")
                        st.cache_data.clear()
                        st.session_state.tx_reset_token += 1
                        if "active_dock_id" in st.session_state:
                            del st.session_state["active_dock_id"]
                        st.rerun()
                    else:
                        st.error(f"Deletion failed: {delete_response.get("message")}")
                except Exception as e:
                    st.error(f"HTTP Delete Call Failed: {e}")            
      
        if save_clicked:
            if not parent_cat:
                st.error("Please pick a valid Category before applying changes.")
            else:
                payload = {
                    "id": int(target_id), "date": str(row_data["date"]), "description": new_desc, "type": row_data["type"],
                    "category_id": category_hierarchy.get(parent_cat, {}).get("id"), "subcategory_id": sub_hierarchy.get(sub_cat) if sub_cat else None,
                    "amount": new_amount, "bank_name": row_data["bank_name"], "note": new_note
                }
                try:
                    update_res = requests.put(f"{services.BASE_URL}/transactions/{target_id}", json=payload)
                    if update_res.status_code in [200, 204]:
                        st.success("Database entry synced successfully!")
                        st.cache_data.clear() 
                        st.session_state.tx_reset_token += 1
                        if "active_dock_id" in st.session_state:
                            del st.session_state["active_dock_id"]
                        st.rerun()
                    else: 
                        st.error(f"Rejection: {update_res.text}")
                except Exception as e: 
                    st.error(f"HTTP Update Call Failed: {e}")
                    
        if cancel_clicked:
            st.session_state.tx_reset_token += 1
            st.rerun()
    else:
        st.info("💡 Click directly on any row in the spreadsheet grid to instantly modify descriptions or fix categorization details.")