import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from datetime import datetime
import util.budget.services as services


@st.dialog("⚙️ Edit Account Configuration")
def edit_account_configuration_dialog(account_id: str, current_name: str, current_classification: str):
    st.write(f"Modify configurations for properties under **{current_name}**.")
    new_alias = st.text_input("Custom Name / Alias", value=current_name)
    
    scopes = ["Personal", "Business"]
    try:
        default_idx = scopes.index(current_classification)
    except ValueError:
        default_idx = 0
    new_classification = st.selectbox("Classification Scope", scopes, index=default_idx)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes", use_container_width=True, type="primary"):
            payload = {
                "custom_name": new_alias.strip() if new_alias.strip() else None,
                "classification_type": new_classification
            }
            try:
                res = requests.put(f"{services.BASE_URL}/accounts/{account_id}", json=payload)
                if res.status_code in [200, 204]:
                    st.success("Account configurations updated!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Server rejected updates: {res.text}")
            except Exception as e:
                st.error(f"Failed to communicate with API server: {e}")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


head_left, head_mid, head_right = st.columns([3.6, 1.2, 1.2], vertical_alignment="center")
with head_left:
    st.markdown("### 🏦 Real-Time Account Liquidity & Utilization")
with head_mid:
    if st.button("🔄 Sync Balances", key="global_balance_sync_trigger", type="primary", use_container_width=True):
        with st.spinner("Contacting institution servers..."):
            try:
                services.trigger_balance_sync()
                st.toast("Account balances refreshed successfully!", icon="✅")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Balance synchronization failed: {e}")
with head_right:
    link_token = services.get_new_plaid_link_token()
    if link_token:
        st.link_button("➕ Connect Bank", url=f"http://localhost:8000/bank_connect?token={link_token}", use_container_width=True, type="secondary")
    else:
        st.button("➕ Connect Bank", key="shelf_connect_bank_disabled", use_container_width=True, disabled=True)

try:
    res = requests.get(f"{services.BASE_URL}/new_balance")
    balances = res.json() if res.status_code == 200 else {"checking": [], "credit card": []}

    checking_accts = balances.get("checking", [])
    cc_accts = balances.get("credit card", [])

    st.markdown("#### 🟢 Cash Assets & Checking Accounts")
    if checking_accts:
        for i in range(0, len(checking_accts), 3):
            chunk = checking_accts[i : i + 3]
            cols = st.columns(3)
            for idx, acct in enumerate(chunk):
                with cols[idx]:
                    with st.container(border=True):
                        st.caption(acct["institution_name"])
                        mask_suffix = f" (...{acct['mask']})" if acct.get("mask") else ""
                        st.markdown(f"**{acct['account_name']}{mask_suffix}**")
                        bal = acct["current_balance"] if acct["current_balance"] is not None else 0.0
                        st.subheader(f"${bal:,.2f}")
                        st.caption(f"💼 Context: **{acct.get('classification_type', 'Personal')}**")
                        if st.button("Edit", key=f"edit_chk_{acct['id']}", type="tertiary"):
                            edit_account_configuration_dialog(acct["id"], acct["account_name"], acct.get('classification_type', 'Personal'))
    else:
        st.info("No active checking account lines discovered.")

    st.write("")

    st.markdown("#### 🔴 Credit Card Liabilities")
    if cc_accts:
        for i in range(0, len(cc_accts), 6):
            chunk = cc_accts[i : i + 6]
            cols = st.columns(6)
            for idx, acct in enumerate(chunk):
                with cols[idx]:
                    with st.container(border=True):
                        st.caption(acct["institution_name"])
                        mask_suffix = f" (..{acct['mask']})" if acct.get("mask") else ""
                        st.markdown(f"<small><b>{acct['account_name']}{mask_suffix}</b></small>", unsafe_allow_html=True)
                        bal = acct["current_balance"] if acct["current_balance"] is not None else 0.0
                        st.markdown(f"#### ${bal:,.2f}")
                        st.markdown(f"<p style='margin:0; padding:0;'><caption style='font-size:0.75rem;'>🏷️ Mode: {acct.get('classification_type', 'Personal')}</caption></p>", unsafe_allow_html=True)
                        if st.button("Edit", key=f"edit_cc_{acct['id']}", type="tertiary", use_container_width=True):
                            edit_account_configuration_dialog(acct["id"], acct["account_name"], acct.get('classification_type', 'Personal'))
    else:
        st.info("No active credit card statement lines discovered.")

except Exception:
    st.error("Real-time account liquidity streaming engine offline.")