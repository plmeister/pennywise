from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from decimal import Decimal

class ForecastScenario(Base):
    __tablename__ = "forecast_scenarios"

    name = Column(String, nullable=False)
    description = Column(Text)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("ScenarioTransaction", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioTransaction(Base):
    __tablename__ = "scenario_transactions"

    scenario_id = Column(Integer, ForeignKey("forecast_scenarios.id"), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String)
    is_materialised = Column(Boolean, default=False)

    scenario = relationship("ForecastScenario", back_populates="transactions")
    legs = relationship("ScenarioTransactionLeg", back_populates="transaction", cascade="all, delete-orphan")


class ScenarioTransactionLeg(Base):
    __tablename__ = "scenario_transaction_legs"

    transaction_id = Column(Integer, ForeignKey("scenario_transactions.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)  # Positive for inflow, negative for outflow
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    transaction = relationship("ScenarioTransaction", back_populates="legs")
