import streamlit as st

# Define your pages with Material Icons
# Browse icons at: https://fonts.google.com/icons
home_page = st.Page("views/overview.py", title="Home", icon=":material/home:")
cashflow_page = st.Page("views/cashflow.py", title="Cashflow", icon=":material/home:")

dashboard_page = st.Page("views/budget/overall_dashboard.py", title="Overview", icon=":material/dashboard:")
expense_page = st.Page("views/budget/expense_dashboard.py", title="Expense", icon=":material/receipt:")
income_page = st.Page("views/budget/income_dashboard.py", title="Income", icon=":material/money_bag:")
accounts_page = st.Page("views/budget/accounts_overview.py", title="Accounts", icon=":material/account_balance:")
category_management_page = st.Page("views/budget/categories_management.py", title="Categories", icon=":material/category:")
mappings_management_page = st.Page("views/budget/mappings_management.py", title="Mappings", icon=":material/automation:")
institutes_management_page = st.Page("views/budget/institutes_management.py", title="Institutes", icon=":material/add_business:")

portfolio_snapshot_page = st.Page("views/portfolio/snapshot.py", title="Overview", icon=":material/finance:")
current_holdings_page = st.Page("views/portfolio/current_holdings.py", title="Current Holdings", icon=":material/finance:")
portfolio_accounts_page = st.Page("views/portfolio/accounts.py", title="Accounts", icon=":material/account_balance:")
portfolio_transaction_page = st.Page("views/portfolio/transactions.py", title="Transactions", icon=":material/settings:")
rsu_pnl_page = st.Page("views/portfolio/rsu_pnl.py", title="RSU P&L", icon=":material/settings:")

paycheck_overview = st.Page("views/paycheck/summary.py", title="Summary", icon=":material/settings:")
all_paychecks = st.Page("views/paycheck/all.py", title="All", icon=":material/settings:")

# Initialize the navigation
# pg = st.navigation([home_page, dashboard_page, settings_page]
pg = st.navigation({
    "Personal Finance Hub": [home_page, cashflow_page],
    "Budgeting": [dashboard_page, expense_page, income_page, accounts_page, category_management_page, mappings_management_page, institutes_management_page],
    "Portfolio": [portfolio_snapshot_page, current_holdings_page, portfolio_accounts_page, portfolio_transaction_page, rsu_pnl_page],
    "Paycheck": [paycheck_overview, all_paychecks]
})



# Run the selected page
pg.run()