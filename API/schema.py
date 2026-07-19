from pydantic import BaseModel, Field, model_validator
from datetime import date, timedelta
from typing import Dict, List, Optional


# --- Request Schema --- #

class CategoryFilter(BaseModel):
    name: str | None = Field(default=None, description="Category Name.")

class CategoryCreate(BaseModel):
    name: str
    exclude_from_reporting: bool = False

class SubCategoryFilter(BaseModel):
    name: str | None = Field(default=None, description="SubCategory Name.")
    
class SubCategoryCreate(BaseModel):
    name: str
    category_id: int

class MappingFilter(BaseModel):
    keyword: str | None = Field(default=None, description="Mapping Name.")
    
class MappingsCreate(BaseModel):
    keyword: str
    category_id: int
    subcategory_id: int

class TransactionCreate(BaseModel):
    date: date
    description: str
    type: str
    amount: float
    bank_name: str | None = Field(default=None, description="Bank Name.")
    category_id: int | None = Field(default=None, description="Category ID")
    subcategory_id: int | None = Field(default=None, description="Subcategory ID.")
    note: str | None = Field(default=None, description="Note for this transaction")    

class TransactionFilter(BaseModel):
    description: str | None = Field(default=None, description="Filter by description.")
    start_date: date | None = Field(default=None, description="Start date for filtering.")
    end_date: date | None = Field(default=None, description="End date for filtering.")
    type: str | None = Field(default=None, description="Filter by item type.")
    category_id: int | None = Field(default=None, description="Filter by category.")
    subcategory_id: int | None = Field(default=None, description="Filter by subcategory.")
    bank_name: str | None = Field(default=None, description="Filter by bank_name.")
    separate_by_type: bool | None = Field(default=False, description="Do separate calculation by Type")
    exclude_from_reporting: bool = Field(default=False)
    # This replaces the logic inside your route function
    @model_validator(mode="after")
    def set_dynamic_dates(self):
        if self.end_date is None:
            self.end_date = date.today()
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=60)
        return self    

class AccountCustomizationUpdate(BaseModel):
    custom_name: Optional[str] = None
    classification_type: str = "Personal"

class MonthlyReport(BaseModel):
    category: str # income or expense
    type: Optional[str] = None # All, Personal or Business

# --- Response Schema --- #
class SubCategoryResponse(BaseModel):
    id: int
    name: str
    category_id: int

    class Config:
        from_attributes = True

class DetailedSubCategoryResponse(SubCategoryResponse):
    category: CategoryResponse

class CategoryResponse(BaseModel):
    id: int
    name: str
    exclude_from_reporting: bool

    class Config:
        from_attributes = True

class CategoryWithSubCategories(CategoryResponse):
    subcategories: List[SubCategoryResponse] = []

class MappingsResponse(BaseModel):
    id: int
    keyword: str
    category_id: int
    subcategory_id: int

    class Config:
        from_attributes = True

class DetailedMappingResponse(MappingsResponse):
    category: CategoryResponse
    subcategory: SubCategoryResponse

class KeywordMatchResponse(BaseModel):  
    is_matched: bool
    keyword: Optional[str] = None
    category: Optional[CategoryResponse] = None
    subcategory: Optional[SubCategoryResponse] = None  

class TransactionResponse(BaseModel):
    id: int  # Generated automatically at runtime for the API/Frontend
    date: date
    description: str
    category_id: Optional[int] = None 
    subcategory_id: Optional[int] = None
    amount: float
    type: str
    bank_name: str
    note: Optional[str] = ""

class DetailedTransactionResponse(TransactionResponse):
    category: Optional[CategoryResponse] = None
    subcategory: Optional[SubCategoryResponse] = None 

class TransactionTotalResponse(BaseModel):
    type: Optional[str] = None
    category_name: Optional[str] = "Uncategorized"
    subcategory_name: Optional[str] = None  # Will be empty if grouping only by category
    total_amount: float  
    #category: Optional[CategoryResponse] = None
    #subcategory: Optional[SubCategoryResponse] = None 

class TransactionReportResponse(BaseModel):
    grand_total: float
    breakdown: List[TransactionTotalResponse]    

class MonthlyReportResponse(BaseModel):
    month: date
    total: float
