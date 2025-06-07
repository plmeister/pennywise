from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional

class ScenarioTransactionLegCreate(BaseModel):
    account_id: int
    amount: float
    category_id: Optional[int] = None

class ScenarioTransactionCreate(BaseModel):
    date: date
    description: Optional[str] = None
    is_materialised: Optional[bool] = False
    legs: List[ScenarioTransactionLegCreate]

class ForecastScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    transactions: Optional[List[ScenarioTransactionCreate]] = Field(default_factory=list)


class ScenarioTransactionLeg(BaseModel):
    id: int
    account_id: int
    amount: float
    category_id: Optional[int]

    class Config:
        orm_mode = True

class ScenarioTransaction(BaseModel):
    id: int
    date: date
    description: Optional[str]
    is_materialised: bool
    legs: List[ScenarioTransactionLeg]

    class Config:
        orm_mode = True

class ForecastScenario(BaseModel):
    id: int
    name: str
    description: Optional[str]
    start_date: date
    end_date: date
    transactions: List[ScenarioTransaction]

    class Config:
        orm_mode = True
