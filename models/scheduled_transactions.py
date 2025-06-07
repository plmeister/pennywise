from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum

class RecurrenceType(enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # for complex patterns like "2nd Monday"

class ScheduledTransaction(Base):
    __tablename__ = "scheduled_transactions"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    amount = Column(Float)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    from_pot_id = Column(Integer, ForeignKey("pots.id"), nullable=True)
    to_pot_id = Column(Integer, ForeignKey("pots.id"), nullable=True)

    recurrence = Column(Enum(RecurrenceType), default=RecurrenceType.MONTHLY)
    custom_rule = Column(String, nullable=True)  # e.g., "2nd monday"
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)

    shift_for_holidays = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    from_pot = relationship("Pot", foreign_keys=[from_pot_id])
    to_pot = relationship("Pot", foreign_keys=[to_pot_id])
