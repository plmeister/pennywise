"""Data structures for bank statement imports"""
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime
from typing import Optional

class ImportedTransaction(BaseModel):
    """Represents a transaction imported from a bank statement"""
    date: datetime
    amount: Decimal
    description: str
    type: Optional[str] = None  # Transaction type from bank (e.g., "POS", "DD", "FPI")
    reference: Optional[str] = None
    balance: Optional[Decimal] = None  # Running balance if provided
    
    # Fields used for reconciliation
    unique_id: Optional[str] = None  # Bank's unique transaction ID if available
    check_number: Optional[str] = None
    raw_description: Optional[str] = None  # Original description before any cleaning
    
    @validator('amount', pre=True)
    def parse_amount(cls, v):
        """Handle different amount formats"""
        if isinstance(v, str):
            # Remove currency symbols and commas
            v = v.replace('£', '').replace('$', '').replace(',', '')
            return Decimal(v)
        return v

class BankStatement(BaseModel):
    """Represents an imported bank statement"""
    account_number: Optional[str] = None
    sort_code: Optional[str] = None
    start_date: datetime
    end_date: datetime
    start_balance: Optional[Decimal] = None
    end_balance: Optional[Decimal] = None
    transactions: list[ImportedTransaction]
    
    @property
    def total_credits(self) -> Decimal:
        credits = [tx.amount for tx in self.transactions if tx.amount > 0]
        return sum(credits, Decimal('0'))
    
    @property
    def total_debits(self) -> Decimal:
        debits = [tx.amount for tx in self.transactions if tx.amount < 0]
        return sum(debits, Decimal('0'))
    
    @property
    def net_movement(self) -> Decimal:
        return self.total_credits + self.total_debits  # debits are negative