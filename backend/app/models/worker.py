"""Workers, their skills, certifications and weekly availability."""

from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AvailabilityStatus, VerificationStatus

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.catalog import ServiceCategory, Skill
    from app.models.core import Cooperative, User, Zone


class Worker(Base, TimestampMixin):
    """A cooperative member who performs services."""

    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    cooperative_id: Mapped[int] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    primary_service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    headline: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    rating_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_earnings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    weekly_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)

    availability_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AvailabilityStatus.AVAILABLE
    )
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=VerificationStatus.VERIFIED
    )

    base_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    base_lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    insurance_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    training_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(back_populates="worker")
    cooperative: Mapped["Cooperative"] = relationship(back_populates="workers")
    zone: Mapped["Zone"] = relationship()
    primary_service: Mapped["ServiceCategory"] = relationship()
    skills: Mapped[list["WorkerSkill"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )
    availability: Mapped[list["WorkerAvailability"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="worker")


class WorkerSkill(Base):
    """A skill held by a worker, with self-declared proficiency (1-5)."""

    __tablename__ = "worker_skills"
    __table_args__ = (UniqueConstraint("worker_id", "skill_id", name="uq_worker_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proficiency: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    worker: Mapped["Worker"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="worker_links")


class Certification(Base, TimestampMixin):
    """A verifiable credential held by a worker."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    issuing_body: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    credential_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    worker: Mapped["Worker"] = relationship(back_populates="certifications")
    skill: Mapped["Skill | None"] = relationship()


class WorkerAvailability(Base):
    """Recurring weekly availability window. day_of_week: 0=Mon .. 6=Sun."""

    __tablename__ = "worker_availability"
    __table_args__ = (
        UniqueConstraint("worker_id", "day_of_week", name="uq_worker_availability_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    worker: Mapped["Worker"] = relationship(back_populates="availability")
