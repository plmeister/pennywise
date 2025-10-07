"""Implementation of specific bank statement importers"""
from pathlib import Path
from datetime import datetime
from typing import Any
from decimal import Decimal
import pandas as pd

from .base import CSVImporter, StatementImporter
from schemas.imports import BankStatement

class StarlingSGDImporter(CSVImporter):
    """Importer for Starling Bank SGD CSV format"""
    date_column = "Date"
    amount_column = "Amount (SGD)"
    description_column = "Counter Party"
    type_column = "Reference"
    balance_column = "Balance (SGD)"
    date_formats = ["%d/%m/%Y"]
    currency_symbols = ["S$", "$"]
    
class StarlingGBPImporter(CSVImporter):
    """Importer for Starling Bank GBP CSV format"""
    date_column = "Date"
    amount_column = "Amount (GBP)" 
    description_column = "Counter Party"
    type_column = "Reference"
    balance_column = "Balance (GBP)"
    date_formats = ["%d/%m/%Y"]
    currency_symbols = ["£"]

class RevolutCSVImporter(CSVImporter):
    """Importer for Revolut CSV format"""
    date_column = "Completed Date"
    amount_column = "Amount"
    description_column = "Description"
    type_column = "Type"
    balance_column = "Balance"
    date_formats = ["%Y-%m-%d %H:%M:%S"]
    thousands_separator = ","
    decimal_separator = "."
    
    def _clean_description(self, desc: str) -> str:
        # Revolut sometimes includes payment references in parentheses
        desc = super()._clean_description(desc)
        if " (" in desc and desc.endswith(")"):
            desc = desc[:desc.rindex(" (")]
        return desc
        
class MonzoCSVImporter(CSVImporter):
    """Importer for Monzo CSV format"""
    date_column = "Date"
    amount_column = "Amount"
    description_column = "Description"
    type_column = "Category"
    date_formats = ["%d/%m/%Y"]
    currency_symbols = ["£"]
    
class ExcelImporter(StatementImporter):
    """Base class for Excel statement importers"""
    sheet_name: str | int = 0  # First sheet by default
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file is an Excel file"""
        return file_path.suffix.lower() in ['.xlsx', '.xls']
        
    def import_file(self, file_path: Path) -> BankStatement:
        # Read Excel file into pandas DataFrame
        df = pd.read_excel(
            file_path,
            sheet_name=self.sheet_name,
            engine='openpyxl'
        )
        # Convert to CSV and use CSV importer
        temp_csv = file_path.with_suffix('.csv')
        df.to_csv(temp_csv, index=False)
        try:
            return CSVImporter().import_file(temp_csv)
        finally:
            temp_csv.unlink()  # Clean up temporary file

def get_importers() -> list[StatementImporter]:
    """Get list of all available importers"""
    return [
        StarlingSGDImporter(),
        StarlingGBPImporter(),
        RevolutCSVImporter(),
        MonzoCSVImporter(),
        ExcelImporter()  # Generic Excel importer
    ]