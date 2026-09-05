from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Intent(Base):
    __tablename__ = "intents"
    __table_args__ = (Index("ix_intents_user_id", "user_id"), Index("ix_intents_agent_id", "agent_id"))

    intent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.agent_id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    spending_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    spending_currency: Mapped[str | None] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    agent = relationship("Agent", back_populates="intents")
    user = relationship("User", back_populates="intents")
    carts = relationship("Cart", back_populates="intent")
