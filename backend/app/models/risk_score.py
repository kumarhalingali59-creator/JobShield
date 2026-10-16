
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(primary_key=True)

    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    target_value: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    risk_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UNKNOWN",
        server_default="UNKNOWN",
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Insufficient evidence to assess this target.",
        server_default="Insufficient evidence to assess this target.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
