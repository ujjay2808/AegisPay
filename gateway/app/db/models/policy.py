from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Policy(Base):
    __tablename__ = "policies"

    policy_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_type: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    maximum_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
