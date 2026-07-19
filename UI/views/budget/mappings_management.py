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

if not st.session_state.map_form_open:
    if st.button("➕ Build New Keyword Mapping Rule", use_container_width=True, key="map_rule_open_btn"):
        st.session_state.map_form_open = True
        st.rerun()
else:
    st.markdown("##### ➕ Build New Keyword Mapping Rule")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1: new_keyword = st.text_input("If Description Contains Keyword (e.g. 'AMZN')", key=f"map_kw_new_{st.session_state.map_form_tok}")
    with m_col2: map_cat_choice = st.selectbox(
        "Auto-Assign Category", 
        options=list(category_hierarchy.keys()), 
        index=None, 
        placeholder="Select a category...", 
        key=f"map_cat_new_{st.session_state.map_form_tok}"
    )
    with m_col3:
        sub_options_map = list(category_hierarchy.get(map_cat_choice, {}).get("subcategories", {}).keys())
        map_sub_choice = st.selectbox(
            "Auto-Assign Sub-Category", 
            options=sub_options_map, 
            index=None, 
            placeholder="Select a sub-category...", 
            key=f"map_sub_new_{st.session_state.map_form_tok}"
        )
        
    act_m1, act_m2 = st.columns(2)
    if act_m1.button("🚀 Save Auto-Mapping Rule", use_container_width=True, key="map_save_action_btn"):
        if new_keyword:
            payload = {
                "keyword": new_keyword, 
                "category_id": category_hierarchy[map_cat_choice]["id"], 
                "subcategory_id": category_hierarchy[map_cat_choice]["subcategories"].get(map_sub_choice)
            }
            res = requests.post(f"{services.BASE_URL}/mappings", json=payload)
            if res.status_code in [200, 201]:
                st.success("Rule mapped and saved successfully!")
                st.session_state.map_form_open = False
                st.session_state.map_form_tok += 1
                time.sleep(1)
                st.rerun()
            else: st.error(f"Save Failed: {res.text}")
    if act_m2.button("❌ Close", use_container_width=True, key="map_cncl_action_btn"):
        st.session_state.map_form_open = False
        st.session_state.map_form_tok += 1
        st.rerun()

m_left, m_right = st.columns([2, 1])
with m_left:
    st.subheader("Active Keyword Mappings")
    # 🔍 NEW: Single text filter input field mapped directly to backend MappingFilter requirements
    search_mapping_term = st.text_input("🔍 Search Keyword Rule Pattern", placeholder="e.g. NETFLIX", key="search_kw_mgmt")

    df_mappings = pd.DataFrame()
    try:
        # Append query params to trigger the server-side lookup engine filtering execution loop
        api_params = {}
        if search_mapping_term:
            api_params["keyword"] = search_mapping_term

        map_res = requests.get(f"{services.BASE_URL}/mappings", params=api_params)
        if map_res.status_code == 200:
            map_rows = []
            for m in map_res.json():
                cat_obj, sub_obj = m.get("category") or {}, m.get("subcategory") or {}
                map_rows.append({
                    "Mapping ID": m.get("id"), "Keyword Rule Pattern": m.get("keyword"),
                    "Target Category": cat_obj.get("name", "None"), "Target Sub-Category": sub_obj.get("name", "None"),
                    "Cat ID": m.get("category_id"), "Sub ID": m.get("subcategory_id")
                })
            df_mappings = pd.DataFrame(map_rows)
    except Exception as e: st.error(f"Failed to fetch automated mapping criteria schemas: {e}")

    if not df_mappings.empty:
        gb_map = GridOptionsBuilder.from_dataframe(df_mappings)
        gb_map.configure_selection(selection_mode="single", use_checkbox=False)
        gb_map.configure_column("Cat ID", hide=True)
        gb_map.configure_column("Sub ID", hide=True)
        
        map_grid_res = AgGrid(
            df_mappings, gridOptions=gb_map.build(), update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme="streamlit", fit_columns_on_grid_load=True, key=f"m_map_g_{st.session_state.map_tok}"
        )
        selected_map_rows = map_grid_res.get("selected_rows", [])
    else:
        st.info("No transaction extraction keyword rule patterns match your current filter query.")
        selected_map_rows = []

with m_right:
    st.subheader("⚙️ Mapping Dock")
    if selected_map_rows is not None and len(selected_map_rows) > 0:
        mrow = selected_map_rows.iloc[0] if isinstance(selected_map_rows, pd.DataFrame) else selected_map_rows[0]
        mid = mrow['Mapping ID']
        st.markdown(f"**Modifying Rule ID: `{mid}`**")
        
        edit_keyword = st.text_input("Modify Keyword Rule", value=mrow["Keyword Rule Pattern"], key=f"edit_kw_{mid}")
        cat_list = list(category_hierarchy.keys())
        c_idx = cat_list.index(mrow["Target Category"]) if mrow["Target Category"] in cat_list else 0
        edit_m_cat = st.selectbox("Change Target Category", options=cat_list, index=c_idx, key=f"edit_kw_cat_{mid}")
        
        sub_list = list(category_hierarchy.get(edit_m_cat, {}).get("subcategories", {}).keys())
        s_idx = sub_list.index(mrow["Target Sub-Category"]) if mrow["Target Sub-Category"] in sub_list else 0
        edit_m_sub = st.selectbox("Change Target Sub-Category", options=sub_list, index=s_idx, key=f"edit_kw_sub_{mid}")
        
        mb1, mb2 = st.columns(2)
        if mb1.button("💾 Apply Rule Changes", use_container_width=True, key=f"apply_map_edit_btn_{mid}"):
            payload = {
                "keyword": edit_keyword, "category_id": category_hierarchy[edit_m_cat]["id"],
                "subcategory_id": category_hierarchy[edit_m_cat]["subcategories"].get(edit_m_sub)
            }
            res = requests.put(f"{services.BASE_URL}/mappings/{mid}", json=payload)
            print(f'Return Code : {res.status_code}')
            if res.status_code in [200, 204]:
                st.success("Rule properties changed successfully!")
                st.session_state.map_tok += 1
                time.sleep(1)
                st.rerun()
                
        if mb2.button("❌ Close", use_container_width=True, key=f"clear_map_focus_btn_{mid}"):
            st.session_state.map_tok += 1
            st.rerun()
    else:
        st.info("💡 Select an auto-mapping keyword rule to instantly update layout targets.")