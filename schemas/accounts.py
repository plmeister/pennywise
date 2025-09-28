from typing import Optional
from pydantic import BaseModel, Decimal
from datetime import date
from models.accounts import AccountType

class AccountBase(BaseModel):
    name: str
    type: AccountType
    balance: Decimal
    is_external: bool = False
    interest_rate: Optional[Decimal] = None
    interest_compounding: Optional[str] = None
    minimum_payment: Optional[Decimal] = None
    # Overdraft
    overdraft_limit: Optional[Decimal] = None
    overdraft_interest_rate: Optional[Decimal] = None

class AccountCreate(BaseModel):
    name: str
    balance: Decimal

class PotOut(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    is_active: bool
    account_id: int

class PotCreate(BaseModel):
    name: str
    target_amount: Decimal = 0.0
    current_amount: Decimal = 0.0
    is_active: bool = True
    account_id: int

class AccountOut(AccountCreate):
    id: int
    balance: Decimal = 0.0
    pots: list[PotOut]
    class Config:
        from_attributes = True
