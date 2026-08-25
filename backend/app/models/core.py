"""Cooperatives, zones and user accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.worker import Worker


class Cooperative(Base, TimestampMixin):
    """A labour cooperative: the organisation that owns the workforce."""

    __tablename__ = "cooperatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    founded_year: Mapped[int] = mapped_column(Integer, nullable=False, default=2015)

    # Revenue split.  Defaults reproduce the cooperative payment model:
    # a Rs.650 job -> worker 560, cooperative fund 40, welfare 20, technology 30.
    worker_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.8615)
    cooperative_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0615)
    welfare_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0308)
    technology_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0462)

    zones: Mapped[list["Zone"]] = relationship(back_populates="cooperative")
    workers: Mapped[list["Worker"]] = relationship(back_populates="cooperative")


class Zone(Base, TimestampMixin):
    """A geographic operating zone within a cooperative."""

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    cooperative_id: Mapped[int] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    center_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    center_lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    cooperative: Mapped["Cooperative"] = relationship(back_populates="zones")


class User(Base, TimestampMixin):
    """Login identity.  One row per human, whatever their role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=UserRole.CUSTOMER)
    phone: Mapped[str] = mapped_column(String(24), nullable=False, default="")
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    cooperative_id: Mapped[int | None] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="SET NULL"), nullable=True, index=True
    )
    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    cooperative: Mapped["Cooperative | None"] = relationship()
    zone: Mapped["Zone | None"] = relationship()
    worker: Mapped["Worker | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="customer", foreign_keys="Booking.customer_id"
    )
