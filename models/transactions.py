from sqlalchemy import Integer, String, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base
from decimal import Decimal
from datetime import datetime
from .accounts import Account, Pot, Currency


class Transaction(Base):
    __tablename__: str = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(Date)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), nullable=False)
    
    # Relationships
    currency: Mapped["Currency"] = relationship("Currency")
    legs: Mapped[list["TransactionLeg"]] = relationship("TransactionLeg", back_populates="transaction", cascade="all, delete-orphan")


class TransactionLeg(Base):
    __tablename__: str = "transaction_legs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transactions.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    pot_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pots.id"), nullable=True
    )
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )

    debit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    credit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)

    # validations can be enforced in app logic:
    # exactly one of debit or credit must be non-null and positive
    # if pot_id is set, the pot must belong to the specified account
    # exchange_rate represents the rate used to convert from transaction currency to leg currency

    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="legs"
    )
    account: Mapped["Account"] = relationship("Account")
    pot: Mapped["Pot"] = relationship("Pot")
    currency: Mapped["Currency"] = relationship("Currency")


Transaction.legs = relationship(
    "TransactionLeg", back_populates="transaction", cascade="all, delete-orphan"
)
