"""Service for handling bank statement imports"""
import logging
from pathlib import Path
from typing import Union, Optional

from modules.common.base_service import BaseService
from modules.imports.csv_importer import CSVImporter
from modules.imports.formats import ImportFormatService
from models.import_formats import ImportFormat as ImportFormatModel
from schemas.imports import BankStatement
from schemas.import_formats import ImportFormat
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ImportService(BaseService):
    """Service for handling bank statement imports"""
    
    def __init__(self, model: type, db: Session):
        super().__init__(model, db)
        self.csv_importer = CSVImporter(db)
        self._format_service = ImportFormatService(db)
        
    def _convert_model_to_schema(self, model: ImportFormatModel) -> ImportFormat:
        """Convert a format model to a schema"""
        model_dict = {
            'name': str(model.name),
            'date_column': str(model.date_column),
            'amount_column': str(model.amount_column),
            'description_column': str(model.description_column),
            'date_format': str(model.date_format),
            'thousands_separator': str(model.thousands_separator),
            'decimal_separator': str(model.decimal_separator),
            'encoding': str(model.encoding)
        }
        for field in ['type_column', 'balance_column', 'reference_column', 'notes']:
            value = getattr(model, field)
            if value is not None:
                model_dict[field] = str(value)
        return ImportFormat(**model_dict)
    
    def import_file(
        self,
        file_path: Union[str, Path],
        fmt: Optional[Union[ImportFormat, int, str]] = None,
        account_id: Optional[int] = None
    ) -> BankStatement:
        """Import transactions from a bank statement file
        
        Args:
            file_path: Path to CSV file
            fmt: Optional format definition, format ID, or format name
            account_id: Optional account ID to load/save format for
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
            
        # Check if file can be handled
        if not self.csv_importer.can_handle(file_path):
            raise ValueError(f"Unsupported file type: {file_path}")
            
        resolved_format: Optional[ImportFormat] = None
            
        # Resolve format if ID or name given
        if isinstance(fmt, int):
            model = self._format_service.get(fmt)
            if model:
                resolved_format = self._convert_model_to_schema(model)
        elif isinstance(fmt, str):
            model = self._format_service.get_by_name(fmt)
            if model:
                resolved_format = self._convert_model_to_schema(model)
        elif isinstance(fmt, ImportFormat):
            resolved_format = fmt
            
        # Try to get format from account if none resolved
        if not resolved_format and account_id:
            model = self._format_service.get_by_account(account_id)
            if model:
                resolved_format = self._convert_model_to_schema(model)
            
        if not resolved_format:
            raise ValueError("Import format must be provided if not stored with account")
            
        try:
            return self.csv_importer.import_file(file_path, resolved_format, account_id)
        except Exception as e:
            logger.error(f"Error importing file: {str(e)}")
            raise