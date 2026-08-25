"""Service catalogue and skill taxonomy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.worker import WorkerSkill


class ServiceCategory(Base, TimestampMixin):
    """One of the household / community services the cooperative offers."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon: Mapped[str] = mapped_column(String(40), nullable=False, default="wrench")
    base_price: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)
    avg_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    emergency_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    skills: Mapped[list["ServiceSkill"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )


class Skill(Base, TimestampMixin):
    """A discrete capability a worker can hold and a job can require."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_emerging: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    growth_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    requires_certification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    services: Mapped[list["ServiceSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    worker_links: Mapped[list["WorkerSkill"]] = relationship(back_populates="skill")


class ServiceSkill(Base):
    """Which skills a service normally needs."""

    __tablename__ = "service_skills"
    __table_args__ = (UniqueConstraint("service_id", "skill_id", name="uq_service_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    service: Mapped["ServiceCategory"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="services")
