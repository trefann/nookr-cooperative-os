"""Bookings and everything that hangs off a completed job."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
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
from app.models.enums import BookingStatus, PaymentStatus, Urgency

if TYPE_CHECKING:
    from app.models.catalog import ServiceCategory, Skill
    from app.models.core import User, Zone
    from app.models.worker import Worker


class Booking(Base, TimestampMixin):
    """A single service job, from customer request to rating."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_id: Mapped[int | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cooperative_id: Mapped[int] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    problem_summary: Mapped[str] = mapped_column(String(160), nullable=False)
    raw_request: Mapped[str] = mapped_column(Text, nullable=False, default="")
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=BookingStatus.REQUESTED, index=True
    )
    urgency: Mapped[str] = mapped_column(String(16), nullable=False, default=Urgency.NORMAL)
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    workers_required: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    preferred_time_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    estimated_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    ai_interpretation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    match_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    declined_worker_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)

    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_demo_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    customer: Mapped["User"] = relationship(
        back_populates="bookings", foreign_keys=[customer_id]
    )
    worker: Mapped["Worker | None"] = relationship(back_populates="bookings")
    service: Mapped["ServiceCategory"] = relationship()
    zone: Mapped["Zone"] = relationship()
    required_skills: Mapped[list["BookingSkill"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )
    payment: Mapped["Payment | None"] = relationship(
        back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )
    rating: Mapped["Rating | None"] = relationship(
        back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )


class BookingSkill(Base):
    """A skill the AI determined this job requires."""

    __tablename__ = "booking_skills"
    __table_args__ = (UniqueConstraint("booking_id", "skill_id", name="uq_booking_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )

    booking: Mapped["Booking"] = relationship(back_populates="required_skills")
    skill: Mapped["Skill"] = relationship()


class Payment(Base, TimestampMixin):
    """Simulated payment plus the cooperative revenue split it produced."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(
        String(24), unique=True, nullable=False, index=True
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    worker_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cooperative_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    welfare_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    technology_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PaymentStatus.PENDING)
    method: Mapped[str] = mapped_column(String(32), nullable=False, default="UPI_SIMULATED")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    booking: Mapped["Booking"] = relationship(back_populates="payment")


class Rating(Base, TimestampMixin):
    """Customer feedback on a completed job."""

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")

    booking: Mapped["Booking"] = relationship(back_populates="rating")
