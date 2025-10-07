"""Import format storage models"""
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, mapped_column, Mapped

from database import Base

class ImportFormat(Base):
    """Database model for import format definitions"""
    __tablename__ = "import_formats"
    
    name: Mapped[str] = mapped_column(String, index=True)
    date_column: Mapped[str] = mapped_column(String, nullable=False)
    amount_column: Mapped[str] = mapped_column(String, nullable=False)
    description_column: Mapped[str] = mapped_column(String, nullable=False)
    type_column: Mapped[str] = mapped_column(String)
    balance_column: Mapped[str] = mapped_column(String)
    reference_column: Mapped[str] = mapped_column(String)
    date_format: Mapped[str] = mapped_column(String, nullable=False, default="%Y-%m-%d")
    thousands_separator: Mapped[str] = mapped_column(String, default=",")
    decimal_separator: Mapped[str] = mapped_column(String, default=".")
    notes: Mapped[str] = mapped_column(String)
    
    accounts = relationship("Account", back_populates="import_format")
    
    __table_args__ = (
        UniqueConstraint('name', name='uix_import_format_name'),
    )