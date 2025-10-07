"""Service for managing import formats"""
import json
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from modules.common.base_service import BaseService
from models.import_formats import ImportFormat as ImportFormatModel
from schemas.import_formats import ImportFormat as ImportFormatSchema

class ImportFormatService(BaseService[ImportFormatModel]):
    """Service for managing import formats"""
    
    def __init__(self, db: Session):
        super().__init__(ImportFormatModel, db)
    
    def create(self, data) -> ImportFormatModel:
        """Create a new import format"""
        db_fmt = ImportFormatModel(**data.model_dump())
        self.db.add(db_fmt)
        self.db.commit()
        self.db.refresh(db_fmt)
        return db_fmt
    
    def get_by_name(self, name: str) -> Optional[ImportFormatModel]:
        """Get import format by name"""
        return self.db.scalar(
            select(ImportFormatModel).where(ImportFormatModel.name == name)
        )
        
    def get_by_account(self, account_id: int) -> Optional[ImportFormatModel]:
        """Get import format for an account"""
        return self.db.scalar(
            select(ImportFormatModel).where(ImportFormatModel.account_id == account_id)
        )
    
    def list_formats(self) -> List[ImportFormatModel]:
        """Get all import formats"""
        return list(self.db.scalars(select(ImportFormatModel)))
    
    def set_account_format(self, account_id: int, format_id: int) -> None:
        """Set the default format for an account"""
        # Clear any existing default format for this account
        self.db.query(ImportFormatModel).filter(ImportFormatModel.account_id == account_id).update({"account_id": None})
        # Set new default
        fmt = self.get(format_id)
        if fmt:
            object.__setattr__(fmt, 'account_id', account_id)
            self.db.commit()
            
    def import_json(self, file_path: Path) -> ImportFormatModel:
        """Import format from JSON file"""
        data = json.loads(file_path.read_text())
        fmt = ImportFormatSchema(**data)
        return self.create(fmt)
        
    def export_json(self, format_id: int, file_path: Path) -> None:
        """Export format to JSON file"""
        fmt = self.get(format_id)
        if fmt:
            schema = ImportFormatSchema(
                name=str(fmt.name),
                date_column=str(fmt.date_column),
                amount_column=str(fmt.amount_column),
                description_column=str(fmt.description_column),
                type_column=str(fmt.type_column) if fmt.type_column is not None else None,
                balance_column=str(fmt.balance_column) if fmt.balance_column is not None else None,
                reference_column=str(fmt.reference_column) if fmt.reference_column is not None else None,
                date_format=str(fmt.date_format),
                thousands_separator=str(fmt.thousands_separator),
                decimal_separator=str(fmt.decimal_separator),
                encoding=str(fmt.encoding),
                notes=str(fmt.notes) if fmt.notes is not None else None
            )
            file_path.write_text(schema.model_dump_json(indent=2))