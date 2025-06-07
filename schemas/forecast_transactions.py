from pydantic import BaseModel
from datetime import date

class ForecastTransaction(BaseModel):
    date: date
    name: str
    amount: float
    source_account_id: int | None = None
    destination_account_id: int | None = None

class ForecastPoint(BaseModel):
    account_id: int
    account_name: str
    date: date
    balance: float
    is_external: bool
    amount_in: float
    amount_out: float