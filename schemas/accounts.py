from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from models.accounts import AccountType


class AccountBase(BaseModel):
    name: str
    type: AccountType
    balance: Decimal
    is_external: bool = False
    interest_rate: Decimal | None = None
    interest_compounding: str | None = None
    minimum_payment: Decimal | None = None
    # Overdraft
    overdraft_limit: Decimal | None = None
    overdraft_interest_rate: Decimal | None = None


class AccountCreate(BaseModel):
    name: str
    balance: Decimal
    account_type: AccountType


class PotOut(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    is_active: bool
    account_id: int


class PotCreate(BaseModel):
    name: str
    target_amount: Decimal
    initial_amount: Decimal
    is_active: bool = True
    account_id: int


class AccountOut(AccountCreate):
    id: int
    balance: Decimal
    pots: list[PotOut]

    model_config = ConfigDict(from_attributes=True)
