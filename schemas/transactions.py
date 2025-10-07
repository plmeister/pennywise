from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal

from enum import Enum

class TransactionType(str, Enum):
    """Type of transaction"""
    EXPENSE = "expense"  # Regular expense
    INCOME = "income"    # Regular income
    TRANSFER = "transfer"  # Inter-account transfer
    
class TransferStatus(str, Enum):
    """Status of a transfer transaction"""
    UNMATCHED = "unmatched"      # No matching transfer found yet
    PENDING = "pending"          # Potential match found but not confirmed
    MATCHED = "matched"          # Confirmed match with another transaction
    NOT_TRANSFER = "not_transfer"  # Confirmed not a transfer

class TransactionBase(BaseModel):
    description: str
    date: date
    amount: Decimal
    account_id: int
    currency_id: int
    transaction_type: TransactionType = Field(default=TransactionType.EXPENSE)
    transfer_status: TransferStatus = Field(default=TransferStatus.UNMATCHED)
    linked_transaction_id: int | None = Field(default=None)  # ID of matching transfer transaction
    raw_description: str | None = Field(default=None)  # Original description before cleaning

class TransferIn(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal
    currency_id: int
    description: str = ""
    date: date


class PotTransferIn(BaseModel):
    account_id: int
    pot_id: int
    direction: str = Field(..., pattern="^(to_pot|from_pot)$")
    amount: Decimal
    currency_id: int
    date: date


class ExternalPaymentIn(BaseModel):
    direction: str = Field(..., pattern="^(in|out)$")
    internal_account_id: int
    external_account_id: int
    amount: Decimal
    currency_id: int
    note: str = ""
    date: date

class TransactionResponse(BaseModel):
    id: int
    description: str | None
    date: datetime
    currency_id: int
    
    model_config = ConfigDict(from_attributes=True)

class TransactionCreate(BaseModel):
    source_account_id: int
    destination_account_id: int
    amount: Decimal
    currency_id: int
    description: str | None = None

class Transaction(TransactionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ExternalTransactionCreate(BaseModel):
    internal_account_id: int
    external_account_id: int
    amount: Decimal
    currency_id: int
    direction: str  # "in" (money coming in) or "out" (money going out)
    description: str | None = None
from pydantic import BaseModel, condecimal

class PotTransactionCreate(BaseModel):
    pot_id: int
    amount: Decimal
    direction: str  # "in" (deposit to pot) or "out" (withdraw from pot)
    description: str | None = None
