# config.py
import os
from dotenv import load_dotenv
import plaid
from plaid.api import plaid_api

load_dotenv()

# Initialize Plaid Client
configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox if os.getenv("PLAID_ENV") == "sandbox" else plaid.Environment.Production,
    api_key={
        'clientId': os.getenv("PLAID_CLIENT_ID"),
        'secret': os.getenv("PLAID_SECRET"),
    }
)
api_client = plaid.ApiClient(configuration)
plaid_client = plaid_api.PlaidApi(api_client)