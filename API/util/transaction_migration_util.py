import pandas as pd
# from sqlmodel import Session, select, func
# from sqlmodel.ext.asyncio.session import AsyncSession
# from sqlalchemy.orm import selectinload
import requests
# import csv
# from typing import Dict, Any
import asyncio
# from datetime import date, timedelta

# from budget.API.schema import TransactionCreate
# from database import Category, SubCategory, Mapping, Transaction, get_session, engine

# class APIClient:
#     def __init__(self, base_url: str = "http://localhost:8000"):
#         """
#         Initialize the client with the base URL of your FastAPI server.
#         """
#         self.base_url = base_url.rstrip("/")
#         self.session = requests.Session()
#         self.session.headers.update({"Content-Type": "application/json"})

#     async def create_mapping(self, date: date, description: str, type: str, category_id: int, subcategory_id: int, amount: float, bank_name: str, note: str) -> Dict[str, Any]:
#         """
#         Hits the POST /transactions endpoint.
#         """
#         url = f"{self.base_url}/transactions"
#         payload = {
#             "date": date,
#             "description": description,
#             "type": type,
#             "category_id": category_id,
#             "subcategory_id": subcategory_id,
#             "amount": amount,
#             "bank_name": bank_name,
#             "note": note
#         }
        
#         print(f"Creating Transaction: '{description}'...")
#         response = self.session.post(url, json=payload)
        
#         # This will throw an exception if the API returns a 4xx or 5xx error
#         response.raise_for_status() 
#         return response.json()

async def add_transaction():
    df = pd.read_csv("BusinessChecking.csv")
    df = df.fillna("")
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
    for index, row in df.iterrows():
            description = row['description'] or "Unknown"
            # print(f">>>>>>>> Date : {row['date']}")
            # print(f"Description : {description}")
            # print(f"Amount : {row['amount']}")
            amount = float(row['amount'].replace(",", ""))*-1
            # print(f'>>>>>>> Description : {description} - Amount : {amount}')
            try:
                payload = {
                    "date": row['date'],
                    "description": description,
                    "type": "Business",
                    "amount": amount or 0.0,
                    "bank_name": "Business Checking" 
                }
                print(payload)
                res = requests.post(f"http://localhost:8000/transactions", json=payload)
                if res.status_code == 201:
                    print(">>>>>>>>>>>> Success")
                print(f'>>>>>>>>> failure : {res.text}')
            except Exception as e:
                print(f'>>>>>>>>> failure : {str(e)}')


# async def execute():
#     async with AsyncSession(engine) as session:
            
#         client = APIClient(base_url="http://localhost:8000")

#         df = pd.read_csv("transactions.csv")
#         df = df.fillna("")
#         df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
#         # date,description,type,category,subcategory,amount,bank_name,note

#         for index, row in df.iterrows():
#             date = row['date']
#             description = row['description'] or "Unknown"
#             type = row['type'] or "Personal"
#             cat = row['category']
#             subcat = row['subcategory']            
#             amount = row['amount'] or 0.0
#             bank_name = row['bank_name'] or "Unknown"
#             note = row['note']

#             print(f'Processing Row : {date} - {description} - {amount}')

#             category_id = None
#             subcategory_id = None

#             try:
#                 if cat:
#                     c_statement = select(Category).where(Category.name == cat)
#                     c_result = await session.exec(c_statement) 
#                     c_item = c_result.first()               
#                     if c_item:
#                         category_id = c_item.id

#                 if subcat and category_id:
#                     s_statement = select(SubCategory).where(SubCategory.name == subcat).where(SubCategory.category_id == category_id)
#                     s_result = await session.exec(s_statement)   
#                     s_item = s_result.first()             
#                     if s_item:
#                         subcategory_id = s_item.id

#                 await client.create_mapping(date,description,type,category_id,subcategory_id,amount,bank_name,note)

#                 await session.commit()        
#             except requests.exceptions.HTTPError as e:
#                 print(f"HTTP Error Occurred: {e}")
#                 # If FastAPI throws a validation error, it returns the details in the JSON body
#                 print("Details:", e.response.json())
#                 await session.rollback()
#                 continue
#             except Exception as e:
#                 print(f"An error occurred: {e}")
#                 await session.rollback()
#                 continue
# ==========================================
# Example Usage / Test Script
# ==========================================
if __name__ == "__main__":
    asyncio.run(add_transaction())

