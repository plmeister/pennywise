from typing import Optional
from pydantic import BaseModel, condecimal
from datetime import date
from models.accounts import AccountType

class AccountBase(BaseModel):
    name: str
    type: AccountType
    balance: float
    is_external: bool = False
    interest_rate: Optional[float] = None
    interest_compounding: Optional[str] = None
    minimum_payment: Optional[float] = None
    # Overdraft
    overdraft_limit: Optional[float] = None
    overdraft_interest_rate: Optional[float] = None

class AccountCreate(BaseModel):
    name: str
    balance: float

class PotOut(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    is_active: bool
    account_id: int

class PotCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    is_active: bool = True
    account_id: int

class AccountOut(AccountCreate):
    id: int
    balance: float = 0.0
    pots: list[PotOut]
    class Config:
        from_attributes = True
