"""Import format storage models"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base

class ImportFormat(Base):
    """Database model for import format definitions"""
    __tablename__ = "import_formats"
    
    name = Column(String, index=True)
    date_column = Column(String, nullable=False)
    amount_column = Column(String, nullable=False)
    description_column = Column(String, nullable=False)
    type_column = Column(String)
    balance_column = Column(String)
    reference_column = Column(String)
    date_format = Column(String, nullable=False, default="%Y-%m-%d")
    thousands_separator = Column(String, default=",")
    decimal_separator = Column(String, default=".")
    encoding = Column(String, default="utf-8-sig")
    notes = Column(String)
    
    # Optional link to account for default format
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    account = relationship("Account", back_populates="import_format")
    
    __table_args__ = (
        UniqueConstraint('name', name='uix_import_format_name'),
        UniqueConstraint('account_id', name='uix_account_import_format'),
    )