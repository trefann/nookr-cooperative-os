"""Booking, payment and rating schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import BookingStatus, Urgency


class BookingCreate(BaseModel):
    """Create a job.

    ``service_id`` may be omitted when ``raw_request`` is supplied: the AI
    understanding engine then determines the service. If both are given the
    explicit service wins, because the customer's correction beats the model.
    """

    raw_request: str = Field(default="", max_length=2000)
    service_id: int | None = None
    problem_summary: str = Field(default="", max_length=160)
    skill_ids: list[int] = Field(default_factory=list, max_length=6)
    zone_id: int | None = None
    address: str = Field(default="", max_length=500)
    lat: float | None = None
    lng: float | None = None
    urgency: Urgency | None = None
    workers_required: int = Field(default=1, ge=1, le=6)
    scheduled_for: datetime | None = None
    preferred_time_label: str = Field(default="", max_length=64)
    is_emergency: bool = False
    auto_assign: bool = False

    @field_validator("raw_request")
    @classmethod
    def _clean(cls, value: str) -> str:
        return value.strip()

    def model_post_init(self, _context: Any) -> None:
        if not self.raw_request and self.service_id is None:
            raise ValueError(
                "Describe what you need, or choose a service from the list."
            )


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    note: str = Field(default="", max_length=500)


class PaymentRequest(BaseModel):
    booking_id: int
    method: str = Field(default="UPI_SIMULATED", max_length=32)


class RatingRequest(BaseModel):
    booking_id: int
    stars: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    invoice_number: str
    amount: float
    worker_amount: float
    cooperative_amount: float
    welfare_amount: float
    technology_amount: float
    status: str
    method: str
    paid_at: datetime | None = None


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    stars: int
    comment: str
    created_at: datetime | None = None


class BookingWorkerOut(BaseModel):
    id: int
    name: str
    headline: str
    rating_avg: float
    rating_count: int
    jobs_completed: int
    phone: str = ""
    availability_status: str = ""
    verification_status: str = ""
    zone: str = ""
    lat: float = 0.0
    lng: float = 0.0


class BookingOut(BaseModel):
    id: int
    reference: str
    status: str
    urgency: str
    is_emergency: bool
    service_id: int
    service_name: str
    service_slug: str
    zone_id: int
    zone_name: str
    problem_summary: str
    raw_request: str = ""
    address: str = ""
    lat: float = 0.0
    lng: float = 0.0
    workers_required: int = 1
    scheduled_for: datetime | None = None
    preferred_time_label: str = ""
    estimated_price: float = 0.0
    final_price: float | None = None
    distance_km: float | None = None
    customer_id: int
    customer_name: str = ""
    worker: BookingWorkerOut | None = None
    required_skills: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    assigned_at: datetime | None = None
    accepted_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    payment: PaymentOut | None = None
    rating: RatingOut | None = None
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class BookingDetail(BookingOut):
    ai_interpretation: dict[str, Any] | None = None
    match_breakdown: dict[str, Any] | None = None
    declined_worker_ids: list[int] = Field(default_factory=list)
    payment_split_preview: dict[str, float] | None = None
    eta_minutes: int | None = None
