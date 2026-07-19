from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from schema import DetailedMappingResponse, KeywordMatchResponse, MappingsCreate, MappingsResponse, MappingFilter
from model import SubCategory, Mapping
from database import get_session
from services.mapping import get_mapping_for_description_helper

router = APIRouter(tags=["Mappings"])

@router.get("/mappings", response_model=List[DetailedMappingResponse], tags=["Mappings"])
async def get_mappings(data: MappingFilter = Depends(), session: Session = Depends(get_session)):
    statement = select(Mapping)
    if(data.keyword):
        statement = statement.where(Mapping.keyword.like(f"%{data.keyword}%"))

    statement = statement.options(selectinload(Mapping.category), selectinload(Mapping.subcategory))
    result = await session.exec(statement)
    return result

@router.post("/mappings", response_model=MappingsResponse, status_code=status.HTTP_201_CREATED, tags=["Mappings"])
async def create_mapping(data: MappingsCreate, session: Session = Depends(get_session)):
    subcategory = await session.get(SubCategory, data.subcategory_id)
    if not subcategory:
        raise HTTPException(status_code=404, detail="Category/SubCategory Not Found")
    
    new_mapping = Mapping.model_validate(data)
    session.add(new_mapping)
    await session.commit()
    await session.refresh(new_mapping)
    return new_mapping

@router.put("/mappings/{id}", response_model=MappingsResponse, tags=["Mappings"])
async def update_mapping(id: int, data: MappingsCreate, session: Session = Depends(get_session)):
    subcategory = await session.get(SubCategory, data.subcategory_id)
    if not subcategory:
        raise HTTPException(status_code=404, detail="Category/SubCategory Not Found")
    
    db_mapping = await session.get(Mapping, id)
    db_mapping.keyword = data.keyword
    db_mapping.category_id = data.category_id
    db_mapping.subcategory_id = data.subcategory_id
    session.add(db_mapping)
    await session.commit()
    await session.refresh(db_mapping)
    return db_mapping

@router.get("/mappings/match/{description}", response_model=KeywordMatchResponse, tags=["Mappings"])
async def get_mapping_for_description(description: str, session: Session = Depends(get_session)):
    return await get_mapping_for_description_helper(description=description, session=session)