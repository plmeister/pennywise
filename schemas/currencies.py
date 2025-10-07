from pydantic import BaseModel, ConfigDict
from models.accounts import CurrencyType
from database import Base
from datetime import datetime

class CurrencySchema(Base):
    code: str
    name: str
    symbol: str
    type: CurrencyType
    decimals: int = 2
    is_active: bool = True

class CurrencyBase(BaseModel):
    code: str
    name: str
    symbol: str
    type: CurrencyType
    decimals: int = 2
    is_active: bool = True

class CurrencyCreate(CurrencyBase):
    pass

class Currency(CurrencyBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class TransactionResponse(BaseModel):
    id: int
    description: str | None
    date: datetime
    currency_id: int