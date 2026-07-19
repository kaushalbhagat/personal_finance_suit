# views/management.py
import streamlit as st
import pandas as pd
import requests
import time
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import util.budget.services as services
import streamlit.components.v1 as components

st.subheader("🏦 Institutions & Live Data Connections")
st.write("Link financial profiles natively using Plaid encryption relays.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🔗 Step 1: Connect Account")
    
    link_token = services.get_new_plaid_link_token()
    
    if link_token:
        st.link_button(
            "➕ Launch Secure Bank Link Portal", 
            url=f"http://localhost:8000/bank_connect?token={link_token}",
            use_container_width=True,
            type="primary"
        )
        st.caption("This triggers a temporary connection profile in a secure workspace tab to safeguard origin verification headers.")
    else:
        st.error("Could not fetch a valid Link Token from backend service. Verify server connection status.")

with col2:
    st.markdown("#### 🔄 Step 2: Fetch Active Ledger Entries")
    st.write("Pull fresh transaction line-items down since your last recorded connection update.")
    
    if st.button("🚀 Run Live Sync Pipeline", use_container_width=True):
        with st.spinner("Streaming encrypted bank data rows..."):
            sync_result = services.trigger_bank_sync()
            if sync_result.get("status") == "synced":
                st.success(f"Success! Imported {sync_result.get('total_imported')} fresh transaction line items.")
                st.cache_data.clear() 
            else:
                st.error("Sync routine rejected. Ensure bank link authorization token remains active.")