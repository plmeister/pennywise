from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int
    children: List['CategoryOut'] = []

    class Config:
        orm_mode = True

CategoryOut.update_forward_refs()
class CategoryOut(CategoryBase):
    id: int
    children: List["CategoryOut"] = []

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

# Pydantic v2: rebuild model for forward refs
CategoryOut.model_rebuild()