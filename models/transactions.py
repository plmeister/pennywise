from sqlalchemy import Column, Integer, String, Decimal, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    date = Column(Date)
    account_id = Column(Integer, ForeignKey("accounts.id"))

class TransactionLeg(Base):
    __tablename__ = "transaction_legs"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    pot_id = Column(Integer, ForeignKey("pots.id"), nullable=True)

    debit = Column(Decimal, nullable=True)
    credit = Column(Decimal, nullable=True)

    # validations can be enforced in app logic:
    # exactly one of debit or credit must be non-null and positive
    # if pot_id is set, the pot must belong to the specified account

    transaction = relationship("Transaction", back_populates="legs")
    account = relationship("Account")
    pot = relationship("Pot")
Transaction.legs = relationship("TransactionLeg", back_populates="transaction", cascade="all, delete-orphan")
