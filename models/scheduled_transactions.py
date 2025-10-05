from sqlalchemy import Integer, String, Date, ForeignKey, Boolean, Enum, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base
import enum
from decimal import Decimal
from datetime import datetime
from models.accounts import Account, Pot


class RecurrenceType(enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # for complex patterns like "2nd Monday"


class ScheduledTransaction(Base):
    __tablename__: str = "scheduled_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    from_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    to_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    from_pot_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pots.id"), nullable=True
    )
    to_pot_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pots.id"), nullable=True
    )

    recurrence: Mapped[RecurrenceType] = mapped_column(
        Enum(RecurrenceType), default=RecurrenceType.MONTHLY
    )
    custom_rule: Mapped[str] = mapped_column(
        String, nullable=True
    )  # e.g., "2nd monday"
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=True)

    shift_for_holidays: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    from_account: Mapped["Account"] = relationship(
        "Account", foreign_keys=[from_account_id]
    )
    to_account: Mapped["Account"] = relationship(
        "Account", foreign_keys=[to_account_id]
    )
    from_pot: Mapped["Pot | None"] = relationship("Pot", foreign_keys=[from_pot_id])
    to_pot: Mapped["Pot | None"] = relationship("Pot", foreign_keys=[to_pot_id])
