import pandas as pd
from sqlmodel import Session, select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
import requests
from typing import Dict, Any
import asyncio
from database import Category, SubCategory, Mapping, Transaction, get_session, engine

class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the client with the base URL of your FastAPI server.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    async def create_mapping(self, keyword: str, category_id: int, subcategory_id: int) -> Dict[str, Any]:
        """
        Hits the POST /mappings endpoint.
        """
        url = f"{self.base_url}/mappings"
        payload = {
            "keyword": keyword,
            "category_id": category_id,
            "subcategory_id": subcategory_id
        }
        
        print(f"Creating Mappings: '{keyword}'...")
        response = self.session.post(url, json=payload)
        
        # This will throw an exception if the API returns a 4xx or 5xx error
        response.raise_for_status() 
        return response.json()



async def execute():
    async with AsyncSession(engine) as session:
            
        client = APIClient(base_url="http://localhost:8000")

        df = pd.read_csv("mappings.csv")

        for index, row in df.iterrows():
            keyword = row['keyword']
            cat = row['category']
            subcat = row['subcategory']

            print(f'Processing Row : {keyword} - {cat} - {subcat}')

            try:
                c_statement = select(Category).where(Category.name == cat)
                c_result = await session.exec(c_statement)                
                category_id = c_result.first().id

                s_statement = select(SubCategory).where(SubCategory.name == subcat).where(SubCategory.category_id == category_id)
                s_result = await session.exec(s_statement)                
                subcategory_id = s_result.first().id

                await client.create_mapping(keyword, category_id, subcategory_id)

                await session.commit()        
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error Occurred: {e}")
                # If FastAPI throws a validation error, it returns the details in the JSON body
                print("Details:", e.response.json())
                await session.rollback()
                continue
            except Exception as e:
                print(f"An error occurred: {e}")
                await session.rollback()
                continue
# ==========================================
# Example Usage / Test Script
# ==========================================
if __name__ == "__main__":
    asyncio.run(execute())

