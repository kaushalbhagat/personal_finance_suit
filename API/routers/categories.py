from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from model import Category, SubCategory
from database import get_session
from schema import CategoryWithSubCategories, CategoryCreate, CategoryResponse, SubCategoryFilter, SubCategoryResponse, SubCategoryCreate, DetailedSubCategoryResponse, CategoryFilter

router = APIRouter(tags=["Categories"])

@router.get("/categories", response_model=List[CategoryWithSubCategories], tags=["Categories"])
async def get_categories(data: CategoryFilter = Depends(), session: Session = Depends(get_session)):
    statement = select(Category)
    if data.name:
        statement = statement.where(Category.name.like(f"%{data.name}%")) 
    statement = statement.options(selectinload(Category.subcategories))
    result = await session.exec(statement)
    return result

@router.get("/categories/name/{name}", response_model=CategoryWithSubCategories, tags=["Categories"])
async def get_categories_by_name(name: str, session: Session = Depends(get_session)):
    statement = select(Category).where(Category.name == name).options(selectinload(Category.subcategories))
    result = await session.exec(statement)
    category = result.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with name '{name}' not found"
    )
    return category

@router.get("/categories/id/{id}", response_model=CategoryWithSubCategories, tags=["Categories"])
async def get_categories_by_id(id: int, session: Session = Depends(get_session)):
    statement = select(Category).where(Category.id == id).options(selectinload(Category.subcategories))
    result = await session.exec(statement)
    category = result.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id '{id}' not found"
    )
    return category

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, tags=["Categories"])
async def create_category(data: CategoryCreate, session: Session = Depends(get_session)):
    new_category = Category.model_validate(data)
    session.add(new_category)
    await session.commit()
    await session.refresh(new_category)
    return new_category

@router.put("/categories/{id}", response_model=CategoryResponse, tags=["Categories"])
async def update_category(id: int, data: CategoryCreate, session: Session = Depends(get_session)):
    db_category = await session.get(Category, id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_category.name = data.name
    db_category.exclude_from_reporting = data.exclude_from_reporting
        
    session.add(db_category)
    await session.commit()
    await session.refresh(db_category)
    return db_category

@router.get("/categories/{category_id}/subcategories", response_model=List[DetailedSubCategoryResponse], tags=["Categories"])
async def get_subcategories_for_category(category_id: int, session: Session = Depends(get_session)):
    parent = await session.get(Category, category_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent Category Not Found")

    statement = select(SubCategory).where(SubCategory.category_id == category_id).options(selectinload(SubCategory.category))
    subcategories = await session.exec(statement)
    return subcategories  

@router.get("/subcategories", response_model=List[DetailedSubCategoryResponse], tags=["Categories"])
async def get_subcategories(data: SubCategoryFilter = Depends(), session: Session = Depends(get_session)):
    statement = select(SubCategory)
    if(data.name):
        statement = statement.where(SubCategory.name.like(f"%{data.name}%"))
    statement = statement.options(selectinload(SubCategory.category))
    subcategories = await session.exec(statement)
    return subcategories  

@router.post("/subcategories", response_model=SubCategoryResponse, status_code=status.HTTP_201_CREATED, tags=["Categories"])
async def create_subcategory(data: SubCategoryCreate, session: Session = Depends(get_session)):
    parent = await session.get(Category, data.category_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent Category Not Found")
    
    new_subcategory = SubCategory.model_validate(data)
    session.add(new_subcategory)
    await session.commit()
    await session.refresh(new_subcategory)
    return new_subcategory

@router.put("/subcategories/{id}", response_model=SubCategoryResponse, tags=["Categories"])
async def update_subcategory(id: int, data: SubCategoryCreate, session: Session = Depends(get_session)):
    db_subcategory = await session.get(SubCategory, id)
    if not db_subcategory:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    
    db_subcategory.name = data.name
        
    session.add(db_subcategory)
    await session.commit()
    await session.refresh(db_subcategory)
    return db_subcategory