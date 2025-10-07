"""Base classes for bank statement importers"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from decimal import Decimal
from datetime import datetime
import logging
import pandas as pd

from schemas.imports import ImportedTransaction, BankStatement

logger = logging.getLogger(__name__)

class ImporterError(Exception):
    """Base class for importer errors"""
    pass

class StatementImporter(ABC):
    """Base class for bank statement importers"""
    
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if this importer can handle the given file"""
        pass
    
    @abstractmethod
    def import_file(self, file_path: Path) -> BankStatement:
        """Import transactions from the given file"""
        pass
    
    def _parse_date(self, date_str: str, formats: list[str]) -> datetime:
        """Try to parse date string using multiple formats"""
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ImporterError(f"Could not parse date: {date_str}")

class CSVImporter(StatementImporter):
    """Base class for CSV statement importers"""
    
    # Override these in subclasses for specific banks
    date_column: str = "Date"
    amount_column: str = "Amount"
    description_column: str = "Description"
    type_column: str | None = None
    balance_column: str | None = None
    date_formats: list[str] = ["%d/%m/%Y", "%Y-%m-%d"]
    thousands_separator: str = ","
    decimal_separator: str = "."
    currency_symbols: list[str] = ["£", "$", "€"]
    encoding: str = "utf-8-sig"
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if file is a CSV file"""
        return file_path.suffix.lower() == '.csv'
    
    def _clean_description(self, desc: str) -> str:
        """Clean up transaction description"""
        return str(desc).strip()
    
    def _parse_amount(self, amount: str | float) -> Decimal:
        """Parse amount string or float to Decimal"""
        if isinstance(amount, float):
            return Decimal(str(amount))
        
        # Remove currency symbols and normalize separators
        amount_str = str(amount)
        for symbol in self.currency_symbols:
            amount_str = amount_str.replace(symbol, '')
            
        if self.thousands_separator != ",":
            # Convert to standard format first
            amount_str = amount_str.replace(self.thousands_separator, "")
            amount_str = amount_str.replace(self.decimal_separator, ".")
        
        return Decimal(amount_str)
    
    def import_file(self, file_path: Path) -> BankStatement:
        # Read CSV with pandas
        df = pd.read_csv(
            str(file_path),  # Convert Path to string
            encoding=self.encoding,
            parse_dates=[self.date_column],
            # Use dtype for string columns to avoid type inference
            dtype={self.description_column: str},  
            date_format=self.date_formats[0]  # Use the primary date format
        )
        
        if df.empty:
            raise ImporterError("No transactions found in file")
            
        # Convert amounts to Decimal
        transactions: list[ImportedTransaction] = []
        for _, row in df.iterrows():
            try:
                date = row[self.date_column].to_pydatetime()
                amount = self._parse_amount(row[self.amount_column])
                description = self._clean_description(row[self.description_column])
                
                tx = ImportedTransaction(
                    date=date,
                    amount=amount,
                    description=description,
                    type=row.get(self.type_column) if self.type_column else None,
                    balance=self._parse_amount(row[self.balance_column]) if self.balance_column and pd.notna(row[self.balance_column]) else None,
                    raw_description=str(row[self.description_column])
                )
                transactions.append(tx)
            except Exception as e:
                logger.warning(f"Error parsing row: {row.to_dict()}. Error: {str(e)}")
                continue
                
        if not transactions:
            raise ImporterError("No valid transactions found in file")
            
        # Get date range and final balance
        dates = [tx.date for tx in transactions]
        first_date = min(dates)
        last_date = max(dates)
        last_balance = next((tx.balance for tx in reversed(transactions) if tx.balance is not None), None)
            
        return BankStatement(
            start_date=first_date,
            end_date=last_date,
            end_balance=last_balance,
            transactions=transactions
        )