import enum
from datetime import datetime
from sqlalchemy import (
    Integer,
    Numeric,
    String,
    ForeignKey,
    Boolean,
    Enum as SqlEnum,
    DateTime,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base
from decimal import Decimal


class AccountType(str, enum.Enum):
    current = "current"
    savings = "savings"
    credit_card = "credit_card"
    loan = "loan"
    mortgage = "mortgage"
    crypto = "crypto"


class CurrencyType(str, enum.Enum):
    fiat = "fiat"
    crypto = "crypto"


class Currency(Base):
    """Currency model for both fiat and crypto currencies"""
    __tablename__ = "currencies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)  # e.g., "USD", "BTC"
    name: Mapped[str] = mapped_column(String)  # e.g., "US Dollar", "Bitcoin"
    symbol: Mapped[str] = mapped_column(String)  # e.g., "$", "₿"
    type: Mapped[CurrencyType] = mapped_column(SqlEnum(CurrencyType), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, default=2)  # e.g., 2 for USD, 8 for BTC
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    accounts: Mapped[list["Account"]] = relationship(back_populates="currency")
    exchange_rates_from: Mapped[list["ExchangeRate"]] = relationship(
        foreign_keys="ExchangeRate.from_currency_id",
        back_populates="from_currency"
    )
    exchange_rates_to: Mapped[list["ExchangeRate"]] = relationship(
        foreign_keys="ExchangeRate.to_currency_id",
        back_populates="to_currency"
    )


class ExchangeRate(Base):
    """Stores exchange rates between currencies"""
    __tablename__ = "exchange_rates"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    from_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    to_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)  # High precision for both fiat and crypto
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    from_currency: Mapped["Currency"] = relationship(
        foreign_keys=[from_currency_id],
        back_populates="exchange_rates_from"
    )
    to_currency: Mapped["Currency"] = relationship(
        foreign_keys=[to_currency_id],
        back_populates="exchange_rates_to"
    )


class Account(Base):
    __tablename__: str = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[AccountType] = mapped_column(
        SqlEnum(AccountType), nullable=False, default=AccountType.current
    )
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(24, 12), nullable=False, default=Decimal("0.00")
    )
    
    # Relationships
    currency: Mapped["Currency"] = relationship(back_populates="accounts")
    is_external: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # True for external accounts
    # Interest-related fields
    interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4)
    )  # e.g. 0.0750 for 7.5%
    interest_compounding: Mapped[str] = mapped_column(String)  # e.g. 'daily', 'monthly'

    pots: Mapped[list["Pot"]] = relationship("Pot", back_populates="account")

    # For debts
    minimum_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # Overdraft config (for current accounts)
    overdraft_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )  # How far below 0 allowed
    overdraft_interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4)
    )  # e.g. 0.19 for 19% APR


class Pot(Base):
    __tablename__: str = "pots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(24, 12), default=Decimal("0.00")
    )
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(24, 12), default=Decimal("0.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"))
    account: Mapped["Account"] = relationship("Account", back_populates="pots")
