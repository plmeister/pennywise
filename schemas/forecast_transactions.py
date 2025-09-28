from pydantic import BaseModel
from datetime import date
from decimal import Decimal

class ForecastTransaction(BaseModel):
    date: date
    name: str
    amount: Decimal
    source_account_id: int | None = None
    destination_account_id: int | None = None

class ForecastPoint(BaseModel):
    account_id: int
    account_name: str
    date: date
    balance: Decimal
    is_external: bool
    amount_in: Decimal
    amount_out: Decimal