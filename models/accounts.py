import enum
from sqlalchemy import Column, Integer, Numeric, String, Date, ForeignKey, Boolean, Enum as SqlEnum
from sqlalchemy.orm import relationship
from database import Base
from decimal import Decimal

class AccountType(str, enum.Enum):
    current = "current"
    savings = "savings"
    credit_card = "credit_card"
    loan = "loan"
    mortgage = "mortgage"

class Currency(str, enum.Enum):
    GBP = "GBP"
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    CNY = "CNY"
    
    @property
    def symbol(self) -> str:
        """Get the currency symbol for display"""
        symbols = {
            "GBP": "£",
            "USD": "$",
            "EUR": "€",
            "JPY": "¥",
            "AUD": "A$",
            "CAD": "C$",
            "CHF": "Fr",
            "CNY": "¥"
        }
        return symbols.get(self.value, self.value)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    type = Column(SqlEnum(AccountType), nullable=False, default=AccountType.current)
    currency = Column(SqlEnum(Currency), nullable=False, default=Currency.GBP)
    balance = Column(Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    is_external = Column(Boolean, default=False)  # True for external accounts
    # Interest-related fields
    interest_rate = Column(Numeric(5, 4))  # e.g. 0.0750 for 7.5%
    interest_compounding = Column(String)  # e.g. 'daily', 'monthly'

    pots = relationship("Pot", back_populates="account")

    # For debts
    minimum_payment = Column(Numeric(12, 2))
    
    # Overdraft config (for current accounts)
    overdraft_limit = Column(Numeric(12, 2))  # How far below 0 allowed
    overdraft_interest_rate = Column(Numeric(5, 4))  # e.g. 0.19 for 19% APR

class Pot(Base):
    __tablename__ = "pots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    target_amount = Column(Numeric(12, 2), default=Decimal('0.00'))
    current_amount = Column(Numeric(12, 2), default=Decimal('0.00'))
    is_active = Column(Boolean, default=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    account = relationship("Account", back_populates="pots")
