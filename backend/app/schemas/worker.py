"""Worker profile schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AvailabilityStatus


class WorkerSkillOut(BaseModel):
    skill_id: int
    name: str
    slug: str
    proficiency: int
    years_experience: int
    is_emerging: bool = False


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    issuing_body: str
    credential_id: str
    issued_on: date | None = None
    expires_on: date | None = None
    verified: bool


class AvailabilitySlotOut(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    is_available: bool


class WorkerOut(BaseModel):
    id: int
    user_id: int
    name: str
    headline: str
    service_id: int
    service_name: str
    zone_id: int
    zone_name: str
    rating_avg: float
    rating_count: int
    jobs_completed: int
    experience_years: int
    availability_status: str
    verification_status: str
    insurance_active: bool
    training_credits: int
    weekly_capacity: int
    workload_pct: int = 0
    active_jobs: int = 0
    skills: list[WorkerSkillOut] = Field(default_factory=list)
    certification_count: int = 0
    lat: float = 0.0
    lng: float = 0.0
    distance_km: float | None = None


class WorkerDetail(WorkerOut):
    bio: str = ""
    phone: str = ""
    email: str = ""
    total_earnings: float = 0.0
    joined_on: date | None = None
    certifications: list[CertificationOut] = Field(default_factory=list)
    availability: list[AvailabilitySlotOut] = Field(default_factory=list)
    committed_jobs: int = 0


class AvailabilityUpdate(BaseModel):
    availability_status: AvailabilityStatus
