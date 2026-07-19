import streamlit as st
import pandas as pd
import requests
import time
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import util.budget.services as services

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

st.set_page_config(layout="wide", page_title="Categories Management")

c_form1, c_form2 = st.columns(2)
with c_form1:
    if not st.session_state.master_form_open:
        if st.button("➕ Create New Master Category", use_container_width=True, key="m_open_btn"):
            st.session_state.master_form_open = True
            st.rerun()
    else:
        st.markdown("##### ➕ Create New Master Category")
        new_cat_name = st.text_input("Category Name", key=f"new_cat_inp_{st.session_state.master_form_tok}")
        new_exclude_rep = st.checkbox("Exclude from Reporting", key=f"new_cat_excl_{st.session_state.master_form_tok}")
        
        act_c1, act_c2 = st.columns(2)
        if act_c1.button("Save Master Category", use_container_width=True, key="m_save_action"):
            if new_cat_name:
                res = requests.post(f"{services.BASE_URL}/categories", json={"name": new_cat_name, "exclude_from_reporting": new_exclude_rep})
                if res.status_code in [200, 201]:
                    st.success("Master Category Added!")
                    st.session_state.master_form_open = False
                    st.session_state.master_form_tok += 1
                    time.sleep(1)
                    st.rerun()
                else: st.error(f"Failed: {res.text}")
        if act_c2.button("❌ Close", use_container_width=True, key="m_cncl_action"):
            st.session_state.master_form_open = False
            st.session_state.master_form_tok += 1
            st.rerun()
                
with c_form2:
    if not st.session_state.sub_form_open:
        if st.button("➕ Create & Assign New Sub-Category", use_container_width=True, key="s_open_btn"):
            st.session_state.sub_form_open = True
            st.rerun()
    else:
        st.markdown("##### ➕ Create & Assign New Sub-Category")
        new_sub_name = st.text_input("Sub-Category Name", key=f"new_sub_inp_{st.session_state.sub_form_tok}")
        assign_parent = st.selectbox(
            "Assign to Master Category", 
            options=list(category_hierarchy.keys()), 
            index=None,
            placeholder="Select a category...",
            key=f"sub_parent_sel_{st.session_state.sub_form_tok}"
        )
        
        act_s1, act_s2 = st.columns(2)
        if act_s1.button("Save Sub-Category", use_container_width=True, key="s_save_action"):
            if new_sub_name and assign_parent:
                p_id = category_hierarchy[assign_parent]["id"]
                res = requests.post(f"{services.BASE_URL}/subcategories", json={"name": new_sub_name, "category_id": p_id})
                if res.status_code in [200, 201]:
                    st.success("Sub-Category Linked!")
                    st.session_state.sub_form_open = False
                    st.session_state.sub_form_tok += 1
                    time.sleep(1)
                    st.rerun()
                else: st.error(f"Failed: {res.text}")
        if act_s2.button("❌ Close", use_container_width=True, key="s_cncl_action"):
            st.session_state.sub_form_open = False
            st.session_state.sub_form_tok += 1
            st.rerun()

col_m_left, col_m_right = st.columns([2, 1])
with col_m_left:
    st.subheader("Category Registry")
    
    # 🔍 NEW: Dual search fields for Category and Sub-Category filter scopes
    search_c_col, search_s_col = st.columns(2)
    with search_c_col:
        search_cat_term = st.text_input("🔍 Search Category Name", placeholder="e.g. Food", key="search_cat_mgmt")
    with search_s_col:
        search_sub_term = st.text_input("🔍 Search Sub-Category Name", placeholder="e.g. Restaurants", key="search_sub_mgmt")
    
    # Apply text matching filters to the injected registry dataframe
    df_display_cat = df_categories_combined.copy()
    if search_cat_term:
        df_display_cat = df_display_cat[df_display_cat["Category Name"].str.contains(search_cat_term, case=False, na=False)]
    if search_sub_term:
        df_display_cat = df_display_cat[df_display_cat["Sub Category Name"].str.contains(search_sub_term, case=False, na=False)]

    if not df_display_cat.empty:
        gb_cat = GridOptionsBuilder.from_dataframe(df_display_cat)
        gb_cat.configure_selection(selection_mode="single", use_checkbox=False)
        for f_hide in ["Type", "ID", "Parent ID", "Exclude from Reporting"]: gb_cat.configure_column(f_hide, hide=True)
        
        cat_grid_res = AgGrid(
            df_display_cat, gridOptions=gb_cat.build(), update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme="streamlit", fit_columns_on_grid_load=True, key=f"m_cat_g_{st.session_state.cat_tok}"
        )
        selected_cat_rows = cat_grid_res.get("selected_rows", [])
    else:
        st.info("No Configuration Categories match your search filters inside the master tracking relational table.")
        selected_cat_rows = []

with col_m_right:
    st.subheader("🎛️ Unified Control Panel")
    if selected_cat_rows is not None and len(selected_cat_rows) > 0:
        crow = selected_cat_rows.iloc[0] if isinstance(selected_cat_rows, pd.DataFrame) else selected_cat_rows[0]
        
        has_sub = crow["Sub Category Name"] != "—"
        master_id = int(crow["Parent ID"]) if has_sub else int(crow["ID"])
        sub_id = int(crow["ID"]) if has_sub else None
        current_exclude_val = bool(crow["Exclude from Reporting"])

        st.markdown(f"##### 📁 Edit Master Category (ID: `{master_id}`)")
        edit_cat_name = st.text_input("Master Category Name", value=crow["Category Name"], key=f"edit_m_cat_{master_id}")
        edit_exclude_rep = st.checkbox("Exclude from Reporting", value=current_exclude_val, key=f"edit_m_excl_{master_id}")
        
        if st.button("💾 Update Master Category", key=f"btn_m_{master_id}", use_container_width=True):
            res = requests.put(f"{services.BASE_URL}/categories/{master_id}", json={"name": edit_cat_name, "exclude_from_reporting": edit_exclude_rep})
            if res.status_code in [200, 204]:
                st.success("Updated Master Category properties!")
                st.session_state.cat_tok += 1  
                time.sleep(1)
                st.rerun()
            else: st.error(f"Failed: {res.text}")
                
        if has_sub:
            st.markdown("---")
            st.markdown(f"##### 🏷️ Edit Sub-Category (ID: `{sub_id}`)")
            edit_sub_name = st.text_input("Sub-Category Name", value=crow["Sub Category Name"], key=f"edit_s_cat_{sub_id}")
            
            parent_options = list(category_hierarchy.keys())
            curr_parent_idx = parent_options.index(crow["Category Name"]) if crow["Category Name"] in parent_options else 0
            edit_sub_parent = st.selectbox("Re-assign Parent Category", options=parent_options, index=curr_parent_idx, key=f"sel_s_parent_{sub_id}")
            
            if st.button("💾 Save Sub-Category Changes", key=f"btn_s_{sub_id}", use_container_width=True):
                res = requests.put(f"{services.BASE_URL}/subcategories/{sub_id}", json={"name": edit_sub_name, "category_id": category_hierarchy[edit_sub_parent]["id"]})
                if res.status_code in [200, 204]:
                    st.success("Updated Sub-Category properties!")
                    st.session_state.cat_tok += 1
                    time.sleep(1)
                    st.rerun()
                else: st.error(f"Failed: {res.text}")

        st.markdown("---")
        if st.button("❌ Close", key="clr_cat", use_container_width=True):
            st.session_state.cat_tok += 1
            st.rerun()
    else:
        st.info("💡 Highlight any row on the left grid ledger to access unified structure editing options instantly.")
