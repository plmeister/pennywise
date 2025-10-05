import enum
from sqlalchemy import (
    Integer,
    Numeric,
    String,
    ForeignKey,
    Boolean,
    Enum as SqlEnum,
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
            "CNY": "¥",
        }
        return symbols.get(self.value, self.value)


class Account(Base):
    __tablename__: str = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[AccountType] = mapped_column(
        SqlEnum(AccountType), nullable=False, default=AccountType.current
    )
    currency: Mapped[Currency] = mapped_column(
        SqlEnum(Currency), nullable=False, default=Currency.GBP
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
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
        Numeric(12, 2), default=Decimal("0.00")
    )
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"))
    account: Mapped["Account"] = relationship("Account", back_populates="pots")
