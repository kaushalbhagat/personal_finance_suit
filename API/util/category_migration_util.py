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

    async def get_category(self, name: str):
        url = f"{self.base_url}/categories/name/{name}"   
        print(f'Getting Category : {name}')
        response = self.session.get(url)
        # This will throw an exception if the API returns a 4xx or 5xx error
        response.raise_for_status() 
        return response.json()

    async def create_category(self, name: str, exclude_from_reporting: bool = False) -> Dict[str, Any]:
        """
        Hits the POST /categories endpoint.
        """
        url = f"{self.base_url}/categories"
        payload = {
            "name": name,
            "exclude_from_reporting": exclude_from_reporting
        }
        
        print(f"Creating Category: '{name}'...")
        response = self.session.post(url, json=payload)
        
        # This will throw an exception if the API returns a 4xx or 5xx error
        response.raise_for_status() 
        return response.json()

    async def create_subcategory(self, name: str, category_id: int) -> Dict[str, Any]:
        """
        Hits the POST /subcategories endpoint.
        """
        url = f"{self.base_url}/subcategories"
        payload = {
            "name": name,
            "category_id": category_id
        }
        
        print(f"Creating Subcategory: '{name}' under Category ID {category_id}...")
        response = self.session.post(url, json=payload)
        
        response.raise_for_status()
        return response.json()

async def execute():
    async with AsyncSession(engine) as session:
            
        client = APIClient(base_url="http://localhost:8000")

        df = pd.read_csv("categories.csv")

        for index, row in df.iterrows():
            cat = row['categories']
            subcat = row['subcategories']

            print(f'Processing Row : {cat} - {subcat}')

            try:
                statement = select(Category).where(Category.name == cat)
                result = await session.exec(statement)                
                category = result.first()
                print(category)

                if category is None:
                    result = await client.create_category(
                        name=cat, 
                        exclude_from_reporting=False
                    )
                    if subcat:
                        category_id = result["id"]
                        await client.create_subcategory(name=subcat, category_id=category_id)
                else:
                    if subcat:
                        await client.create_subcategory(name=subcat, category_id=category.id)

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

