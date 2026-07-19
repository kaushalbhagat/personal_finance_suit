from typing import Any, Dict, List
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
import plaid
from sqlmodel import Session, select
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

from model import PlaidAccounts, PlaidItems, Transaction
from database import get_session
from config import plaid_client  # 💡 Imported from central config
from services.mapping import get_mapping_for_description_helper

from schema import AccountCustomizationUpdate

router = APIRouter(tags=["Plaid"])

# ROUTE 1: Generate a temporary initialization token for the UI
@router.post("/create_link_token", tags=["Plaid"])
def create_link_token():
    try:
        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Personal Budget App",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=str(uuid.uuid4()))
        )
        response = plaid_client.link_token_create(request)
        return {"link_token": response['link_token']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ROUTE 2: Exchange the temporary public_token for a permanent access_token
@router.post("/exchange_public_token")
async def exchange_public_token(payload: dict, session: Session = Depends(get_session)):
    public_token = payload.get("public_token")
    # Read the metadata parameters forwarded from our frontend script
    institution_name = payload.get("institution_name", "Unknown Bank")
    institution_id = payload.get("institution_id", "Unknown ID")
    
    if not public_token:
        raise HTTPException(status_code=400, detail="Missing public_token")
        
    try:
        # Exchange for permanent access token
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = plaid_client.item_public_token_exchange(request)

        print("Response from item_public_token_exchange")
        print(response)
        
        access_token = response['access_token']
        item_id = response['item_id']
        
        data = {
            "institution_id": institution_id,
            "institution_name": institution_name,
            "item_id": item_id,
            "access_token": access_token
        }
        new_plaid_item = PlaidItems.model_validate(data)
        session.add(new_plaid_item)
        await session.commit()
        return {"status": "success", "institution": institution_name}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

# ROUTE 3: Incremental Sync to pull down latest transaction payloads
@router.post("/transactions/sync")
async def sync_transactions(session: Session = Depends(get_session)):
    statement = select(PlaidItems).where(PlaidItems.status.in_(["active", "healthy"]))
    result = await session.exec(statement)
    linked_banks = result.all()
    if not linked_banks:
        return {"status": "no_banks_linked", "total_imported": 0}
    
    statement = select(PlaidAccounts)
    result = await session.exec(statement)
    linked_accounts = result.all()
    linked_accounts_map = {item.id: item for item in linked_accounts}
        
    total_imported_records = 0
    
    # 🔄 Loop through each bank credential independently
    for bank in linked_banks:
        # These attributes can now be safely accessed because they are loaded in memory
        bank_name = bank.institution_name
        token = bank.access_token
        cursor = bank.cursor
        last_synced = bank.last_sync.date()
        
        print(f'>>>>>>>>>>> Bank Name : {bank_name} - Cursor : {cursor}')
        # if bank_name == "Chase Bank": # COMMENT THIS
        try:
            has_more = True
            # cursor=None
            while has_more:
                # Sync transactions for this bank connection
                request = TransactionsSyncRequest(access_token=token, **({"cursor": cursor} if cursor else {}))
                response = plaid_client.transactions_sync(request)

                added_txs = response.get('added', [])
                has_more = response.get('has_more')
                cursor = response.get('next_cursor')
                
                print(f'<<<<<<<<<>>>>>>>>>>> has_more: {has_more} - cursor : {cursor}')
            
            
                # Write new transactions to your transaction ledger table
                for tx in added_txs:
                    print(f'>>>>>>>>>>>>>> {tx['transaction_id']} : {tx['date']}')
                    # if tx['date'] > last_synced:
                    account_id = tx["account_id"]
                    account_info = linked_accounts_map[account_id]
                    data = {
                        "date": tx['date'],
                        "amount": tx['amount'],
                        "description": tx['name'],
                        "type": account_info.classification_type or tx["type"],
                        "bank_name": account_info.custom_name or tx["bank_name"],
                    }
                    mapping = await get_mapping_for_description_helper(data["description"], session=session)
                    if mapping.is_matched:
                        data["category_id"] = mapping.category.id
                        data["subcategory_id"] = mapping.subcategory.id
                    print(data)
                    new_transaction = Transaction.model_validate(data) # UNCOMMENT THIS
                    session.add(new_transaction) # UNCOMMENT THIS
                
                    total_imported_records += 1
            
            # Since 'bank' is already an active model instance, modify it directly!
            bank.last_sync = datetime.now()
            bank.cursor = cursor
            session.add(bank)
            
        except Exception as e:
            print(f"Skipping sync for {bank_name} due to api error: {e}")
            continue
            
    # This batches updates together, speeds up execution, and prevents 
    # objects from expiring mid-iteration.
    await session.commit()
            
    return {"status": "synced", "total_imported": total_imported_records}

@router.delete("/bank_item/{item_id}")
async def remove_item(item_id: str, session: Session = Depends(get_session)):
    # 1. Securely fetch the bank record from your database using the Item ID
    statement = select(PlaidItems).where(PlaidItems.item_id == item_id)
    result = await session.exec(statement)
    db_plaid_item = result.one_or_none()
    
    if not db_plaid_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Bank connection item not found in database."
        )
        
    # 2. Extract the hidden access token safely on the backend side
    secure_access_token = db_plaid_item.access_token

    try:
        # 3. Create the Plaid removal request payload securely
        request = ItemRemoveRequest(access_token=secure_access_token)
        
        # 4. Fire the removal request directly to Plaid's servers
        plaid_client.item_remove(request)
        print(f"Successfully revoked Item {item_id} from Plaid systems.")

    except plaid.ApiException as e:
        print(f"Plaid API error while unlinking item: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plaid rejection error: {e.reason}"
        )

    # 5. Safe to purge from your storage context once Plaid acknowledges revocation
    await session.delete(db_plaid_item)
    await session.commit()
    print(f"Successfully purged Item {item_id} from internal tracking database.")
    
    return {"status": "success", "detail": f"Item {item_id} disconnected completely."}


# Append this clean UI router to your budget_api.py server routing table
@router.get("/bank_connect", response_class=HTMLResponse, tags=["Plaid"])
def bank_connect_page(token: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure Bank Connection Gateway</title>
        <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                background-color: #f9fafb;
                margin: 0;
            }}
            .card {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
                text-align: center;
                max-width: 400px;
            }}
            button {{
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 16px;
                font-weight: 600;
                border-radius: 6px;
                cursor: pointer;
                width: 100%;
                margin-top: 20px;
                transition: background 0.2s;
            }}
            button:hover {{ background-color: #0052a3; }}
            #success-msg {{ display: none; color: #16a34a; font-weight: 600; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🏦 Secure Bank Link</h2>
            <p>Click below to open the encrypted Plaid ledger authentication console.</p>
            <button id="link-button">Connect Account</button>
            <p id="success-msg">🎉 Connection established successfully! You can now close this tab and return to your app dashboard to sync items.</p>
        </div>

        <script type="text/javascript">
        // Initialize Plaid safely inside a clear origin space
        const handler = Plaid.create({{
          token: '{token}',
          onSuccess: function(public_token, metadata) {{
          
            console.log("--- Plaid Metadata JSON ---");
            console.log(JSON.stringify(metadata, null, 2));
            document.getElementById('link-button').style.display = 'none';
            
            // Send the public token directly back to your local token exchange pipeline
            fetch('/exchange_public_token', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ 
                    public_token: public_token, 
                    institution_id: metadata.institution.institution_id,
                    institution_name: metadata.institution.name
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                document.getElementById('success-msg').style.display = 'block';
            }})
            .catch(err => alert('Public token verification failed: ' + err));
          }},
          onExit: function(err, metadata) {{
            if (err != null) {{ console.error(err); }}
          }}
        }});
        
        document.getElementById('link-button').onclick = function() {{
          handler.open();
        }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# API to update balance of all the linked accounts.
@router.post("/balances/sync")
async def sync_all_institution_balances(session = Depends(get_session)):
    # 1. Fetch all your linked institutions out of the database
    statement = select(PlaidItems)
    result = await session.exec(statement)
    all_items = result.all()
    
    total_accounts_processed = 0
    
    # 2. Loop through every single institution access token
    for item in all_items:
        try:
            # Prepare the balance request payload for this specific token
            request = AccountsBalanceGetRequest(access_token=item.access_token)
            
            # Hit Plaid to fetch real-time balances for ALL accounts linked to this item
            response = plaid_client.accounts_balance_get(request)
            
            # 3. Pull out the array of accounts nested inside this institution response
            plaid_accounts_list = response['accounts']
            
            for acct in plaid_accounts_list:
                balances = acct.get('balances', {})
                
                # Check if this account already exist
                statement = select(PlaidAccounts).where(PlaidAccounts.id == acct['account_id'])
                accounts = await session.exec(statement)
                account_data = accounts.first()

                # If account exist, just update balance
                if account_data:
                    # Update account data
                    account_data.current_balance = float(balances.get('current', 0.0))
                    account_data.available_balance = float(balances.get('available')) if balances.get('available') is not None else None
                    account_data.last_updated=datetime.now()
                else: # Create the account 
                    account_data = PlaidAccounts(
                        id=acct['account_id'],
                        item_id=item.item_id, # Link back to parent institution
                        name=acct['name'],
                        mask=acct.get('mask'),
                        type=str(acct['type']),
                        subtype=str(acct['subtype']),
                        current_balance=float(balances.get('current', 0.0)),
                        available_balance=float(balances.get('available')) if balances.get('available') is not None else None,
                        last_updated=datetime.now()
                    )
                session.add(account_data)
                total_accounts_processed += 1
                
            # Update the parent item sync timestamp tracker
            # item.last_sync = datetime.utcnow()
            item.status = "healthy"
            session.add(item)
            
        except plaid.ApiException as e:
            # Handle token revocations or MFA login flags gracefully without halting execution
            print(f"Failed pulling data for Institution {item.institution_name}: {e}")
            item.status = "error"
            session.add(item)
            continue
            
    await session.commit()
    return {"status": "success", "synced_accounts_count": total_accounts_processed}


@router.get("/new_balance", response_model=Dict[str, Any])
async def get_new_balances(session: Session = Depends(get_session)):
    # 1. 🏎️ Select ONLY the used columns and filter at the DATABASE layer
    statement = select(
        PlaidItems.institution_name,
        PlaidAccounts.custom_name,
        PlaidAccounts.name,
        PlaidAccounts.current_balance,
        PlaidAccounts.subtype,
        PlaidAccounts.mask,
        PlaidAccounts.id,
        PlaidAccounts.classification_type
    ).join(
        PlaidAccounts
    ).where(
        PlaidAccounts.subtype.in_(["checking", "credit card"])  # 🎯 DB filters out everything else
    )

    stat_result = await session.exec(statement)
    all_accounts = stat_result.all()

    # 2. 🗃️ Pre-populate output buckets
    response = {"checking": [], "credit card": []}

    # 3. ⏱️ Single-pass loop (O(N) runtime instead of looping twice via list comprehensions)
    for acct in all_accounts:
        account_data = {
            "institution_name": acct.institution_name,
            "account_name": acct.custom_name if acct.custom_name is not None else acct.name,
            "current_balance": acct.current_balance,
            "mask": acct.mask,
            "id": acct.id,
            "classification_type": acct.classification_type
        }
        # Dynamically append to the right bucket based on the DB subtype string
        response[acct.subtype].append(account_data)
    
    return response

# # API to fetch the stored balance for all the accounts
# @router.get("/balances", response_model=List[Dict[str, Any]])
# async def get_stored_balances(session: Session = Depends(get_session)):
#     """
#     Fetches all tracked accounts from the database and groups them 
#     hierarchically by their parent financial institution.
#     """
#     # 1. Fetch all items (institutions) and accounts
#     items_stmt = select(PlaidItems)
#     items_res = await session.exec(items_stmt)
#     all_items = items_res.all()

#     accounts_stmt = select(PlaidAccounts)
#     accounts_res = await session.exec(accounts_stmt)
#     all_accounts = accounts_res.all()

#     # 2. Structure the data hierarchically
#     response_data = []
#     for item in all_items:
#         # Filter child accounts belonging to this specific institution item
#         institution_accounts = [
#             {
#                 "id": acct.id,
#                 "name": acct.name,
#                 "mask": acct.mask,
#                 "type": acct.type,
#                 "subtype": acct.subtype,
#                 "current_balance": acct.current_balance,
#                 "available_balance": acct.available_balance,
#                 "last_updated": acct.last_updated.isoformat() if acct.last_updated else None,
#                 "custom_name": acct.custom_name,
#                 "classification_type": acct.classification_type
#             }
#             for acct in all_accounts if acct.item_id == item.item_id
#         ]
        
#         response_data.append({
#             "institution_id": item.institution_id,
#             "institution_name": item.institution_name,
#             "status": item.status,
#             "accounts": institution_accounts
#         })

#     return response_data

# API to update the custom namr and classification type for an account
@router.put("/balances/accounts/{account_id}")
async def update_account_customization(account_id: str, data: AccountCustomizationUpdate, session: Session = Depends(get_session)):
    acct = await session.get(PlaidAccounts, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Financial account record not found.")
    
    acct.custom_name = data.custom_name if data.custom_name and data.custom_name.strip() else None
    acct.classification_type = data.classification_type
    
    session.add(acct)
    await session.commit()
    return {"status": "success", "message": "Account properties customized updated successfully."}