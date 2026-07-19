# services/mapping_service.py
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from model import Mapping
from schema import KeywordMatchResponse

async def get_mapping_for_description_helper(description: str, session: AsyncSession):
    
    print(f'Looking for a mapping for {description}')

    statement = (
        select(Mapping)
        .where(func.instr(
            func.lower(func.trim(description)), 
            func.lower(func.trim(Mapping.keyword))
            ) > 0
        )
        .options(
            selectinload(Mapping.category), 
            selectinload(Mapping.subcategory)    
        )
    )
    result = await session.exec(statement)
    matched_rule = result.first()

    if not matched_rule:
        print(f'Did not find mapping rule for {description}')
        return KeywordMatchResponse(is_matched=False)
    print(f'Found matching category id {matched_rule.category}')
    return KeywordMatchResponse(
        is_matched=True,
        keyword=matched_rule.keyword,
        category=matched_rule.category,
        subcategory=matched_rule.subcategory
    )