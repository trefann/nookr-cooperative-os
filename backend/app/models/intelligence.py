"""Welfare ledger, historical demand, forecasts and notifications."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import NotificationKind

if TYPE_CHECKING:
    from app.models.catalog import ServiceCategory
    from app.models.core import Zone
    from app.models.worker import Worker


class WelfareRecord(Base, TimestampMixin):
    """One entry in a worker's welfare ledger.

    kind is one of CONTRIBUTION, INSURANCE_PREMIUM or TRAINING_CREDIT.
    """

    __tablename__ = "welfare"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cooperative_id: Mapped[int] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default="CONTRIBUTION")
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    worker: Mapped["Worker"] = relationship()


class DemandRecord(Base):
    """Observed demand: how many jobs of a service ran in a zone on a day.

    This is the training data for the forecasting engine.
    """

    __tablename__ = "demand_records"
    __table_args__ = (
        UniqueConstraint("service_id", "zone_id", "record_date", name="uq_demand_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cooperative_id: Mapped[int] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    bookings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    service: Mapped["ServiceCategory"] = relationship()
    zone: Mapped["Zone"] = relationship()


class DemandForecast(Base, TimestampMixin):
    """A stored forecast produced by the forecasting engine."""

    __tablename__ = "demand_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    cooperative_id: Mapped[int] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), nullable=True, index=True
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    predicted_demand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    baseline_demand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    change_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    method: Mapped[str] = mapped_column(String(48), nullable=False, default="weighted_moving_average")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    service: Mapped["ServiceCategory"] = relationship()
    zone: Mapped["Zone | None"] = relationship()


class Notification(Base, TimestampMixin):
    """In-app notification for a user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default=NotificationKind.SYSTEM)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
