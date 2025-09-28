from pydantic import BaseModel
from datetime import date
from typing import Optional, Literal
from decimal import Decimal

class ScheduledTransactionBase(BaseModel):
    description: str
    amount: Decimal
    from_account_id: Optional[int]
    to_account_id: Optional[int]
    from_pot_id: Optional[int]
    to_pot_id: Optional[int]
    recurrence: Literal["once", "daily", "weekly", "monthly", "custom"]
    custom_rule: Optional[str] = None
    start_date: date
    end_date: Optional[date]
    shift_for_holidays: bool = True
    is_active: bool = True

class ScheduledTransactionCreate(ScheduledTransactionBase):
    pass

class ScheduledTransactionRead(ScheduledTransactionBase):
    id: int

    class Config:
        orm_mode = True
