"""Configurable bank statement format definitions"""
from pydantic import BaseModel
from typing import Optional

class ImportFormat(BaseModel):
    """Defines the column mappings for a bank statement format"""
    name: str  # User-friendly name for the format
    date_column: str
    amount_column: str
    description_column: str
    type_column: Optional[str] = None
    balance_column: Optional[str] = None
    reference_column: Optional[str] = None
    date_format: str = "%Y-%m-%d"  # Default ISO format
    thousands_separator: str = ","
    decimal_separator: str = "."
    encoding: str = "utf-8-sig"
    currency_symbol: str = ""  # e.g., "£", "$", "€"
    notes: Optional[str] = None  # User notes about this format

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Starling GBP",
                "date_column": "Date",
                "amount_column": "Amount (GBP)",
                "description_column": "Counter Party",
                "type_column": "Reference",
                "balance_column": "Balance (GBP)",
                "date_format": "%d/%m/%Y",
                "currency_symbol": "£"
            }
        }