"""CSV statement importer with configurable column mappings"""
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from decimal import Decimal
import pandas as pd
from sqlalchemy.orm import Session

from schemas.import_formats import ImportFormat
from schemas.imports import ImportedTransaction, BankStatement
from modules.accounts.service import AccountService

class CSVImporter:
    """Configurable CSV statement importer"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def can_handle(self, file_path: Path) -> bool:
        """Check if file is a CSV file"""
        return file_path.suffix.lower() == '.csv'
    
    def import_file(self, file_path: Path, fmt: ImportFormat, account_id: Optional[int] = None) -> BankStatement:
        """Import transactions from a bank statement file
        
        Args:
            file_path: Path to CSV file
            fmt: Import format defining column mappings
            account_id: Optional account ID to get default format
        """
        # Read CSV with pandas
        df = pd.read_csv(
            str(file_path),
            encoding=fmt.encoding,
            thousands=fmt.thousands_separator if fmt.thousands_separator != "," else None,
            decimal=fmt.decimal_separator,
            dtype={fmt.description_column: str}
        )
        
        if df.empty:
            raise ValueError("No transactions found in file")
            
        transactions: list[ImportedTransaction] = []
        for _, row in df.iterrows():
            try:
                # Parse amount
                amount_str = str(row[fmt.amount_column])
                if fmt.currency_symbol:
                    amount_str = amount_str.replace(fmt.currency_symbol, '')
                amount = Decimal(amount_str.replace(fmt.thousands_separator, ''))
                
                # Parse date
                date = pd.to_datetime(row[fmt.date_column], format=fmt.date_format)
                
                # Create transaction
                tx = ImportedTransaction(
                    date=date,
                    amount=amount,
                    description=str(row[fmt.description_column]).strip(),
                    type=str(row[fmt.type_column]) if fmt.type_column else None,
                    balance=Decimal(str(row[fmt.balance_column])) if fmt.balance_column else None,
                    reference=str(row[fmt.reference_column]) if fmt.reference_column else None,
                    raw_description=str(row[fmt.description_column])
                )
                transactions.append(tx)
                
            except Exception as e:
                # Log error but continue with other rows
                print(f"Error parsing row: {row.to_dict()}. Error: {str(e)}")
                continue
                
        if not transactions:
            raise ValueError("No valid transactions could be parsed from file")
            
        # Get date range and balances
        dates = [tx.date for tx in transactions]
        balances = [tx.balance for tx in transactions if tx.balance is not None]
        
        statement = BankStatement(
            start_date=min(dates),
            end_date=max(dates),
            end_balance=balances[-1] if balances else None,
            start_balance=balances[0] if balances else None,
            transactions=transactions
        )
        
        # If this is a new format for this account, save it
        if account_id:
            self._save_format_for_account(account_id, fmt)
            
        return statement
    
    def _save_format_for_account(self, account_id: int, fmt: ImportFormat) -> None:
        """Save import format as default for an account"""
        account_service = AccountService(db=self.db)
        account = account_service.get(account_id)
        if account:
            # TODO: Save format in account settings or a separate table
            pass

    def get_format_for_account(self, account_id: int) -> Optional[ImportFormat]:
        """Get the saved import format for an account"""
        account_service = AccountService(db=self.db)
        account = account_service.get(account_id)
        if account:
            # TODO: Load format from account settings or formats table
            pass
        return None