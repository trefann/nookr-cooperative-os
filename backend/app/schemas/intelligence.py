"""Request schemas for the AI and matching endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Urgency


class UnderstandRequest(BaseModel):
    """Natural language in, structured service requirement out."""

    text: str = Field(min_length=3, max_length=2000)
    zone_id: int | None = None

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Please describe the problem in a few more words.")
        return cleaned


class MatchRequest(BaseModel):
    """Rank workers for a job.

    Either give a ``booking_id`` to match an existing job, or describe the job
    directly with a service, location and optional skills.
    """

    booking_id: int | None = None
    service_id: int | None = None
    skill_ids: list[int] = Field(default_factory=list, max_length=6)
    zone_id: int | None = None
    lat: float | None = None
    lng: float | None = None
    scheduled_for: datetime | None = None
    urgency: Urgency | None = None
    workers_required: int = Field(default=1, ge=1, le=6)
    limit: int = Field(default=8, ge=1, le=25)

    def model_post_init(self, _context: object) -> None:
        if self.booking_id is None and self.service_id is None:
            raise ValueError("Provide either a booking_id or a service_id.")


class AssignRequest(BaseModel):
    booking_id: int
    worker_id: int
