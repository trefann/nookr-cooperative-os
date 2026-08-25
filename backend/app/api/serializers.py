"""ORM to response-model conversion.

Kept in one place so a booking looks identical whichever endpoint returned it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Booking, Cooperative, Worker
from app.schemas.booking import (
    BookingDetail,
    BookingOut,
    BookingWorkerOut,
    PaymentOut,
    RatingOut,
)
from app.schemas.worker import (
    AvailabilitySlotOut,
    CertificationOut,
    WorkerDetail,
    WorkerOut,
    WorkerSkillOut,
)
from app.services.bookings import split_payment, timeline_for
from app.services.geo import eta_minutes, travel_distance_km
from app.services.workload import WorkloadSnapshot


def worker_to_out(
    worker: Worker,
    snapshot: WorkloadSnapshot | None = None,
    distance_km: float | None = None,
) -> WorkerOut:
    return WorkerOut(
        id=worker.id,
        user_id=worker.user_id,
        name=worker.user.full_name if worker.user else f"Worker {worker.id}",
        headline=worker.headline,
        service_id=worker.primary_service_id,
        service_name=worker.primary_service.name if worker.primary_service else "",
        zone_id=worker.zone_id,
        zone_name=worker.zone.name if worker.zone else "",
        rating_avg=round(worker.rating_avg, 2),
        rating_count=worker.rating_count,
        jobs_completed=worker.jobs_completed,
        experience_years=worker.experience_years,
        availability_status=worker.availability_status,
        verification_status=worker.verification_status,
        insurance_active=worker.insurance_active,
        training_credits=worker.training_credits,
        weekly_capacity=worker.weekly_capacity,
        workload_pct=snapshot.workload_pct if snapshot else 0,
        active_jobs=snapshot.active_jobs if snapshot else 0,
        skills=[
            WorkerSkillOut(
                skill_id=link.skill_id,
                name=link.skill.name,
                slug=link.skill.slug,
                proficiency=link.proficiency,
                years_experience=link.years_experience,
                is_emerging=link.skill.is_emerging,
            )
            for link in worker.skills
        ],
        certification_count=sum(1 for c in worker.certifications if c.verified),
        lat=worker.base_lat,
        lng=worker.base_lng,
        distance_km=distance_km,
    )


def worker_to_detail(
    worker: Worker,
    snapshot: WorkloadSnapshot | None = None,
    distance_km: float | None = None,
) -> WorkerDetail:
    base = worker_to_out(worker, snapshot, distance_km)
    return WorkerDetail(
        **base.model_dump(),
        bio=worker.bio,
        phone=worker.user.phone if worker.user else "",
        email=worker.user.email if worker.user else "",
        total_earnings=round(worker.total_earnings, 2),
        joined_on=worker.joined_on,
        certifications=[CertificationOut.model_validate(c) for c in worker.certifications],
        availability=[
            AvailabilitySlotOut(
                day_of_week=slot.day_of_week,
                start_time=slot.start_time.strftime("%H:%M"),
                end_time=slot.end_time.strftime("%H:%M"),
                is_available=slot.is_available,
            )
            for slot in sorted(worker.availability, key=lambda s: s.day_of_week)
        ],
        committed_jobs=snapshot.committed_jobs if snapshot else 0,
    )


def _booking_worker(booking: Booking) -> BookingWorkerOut | None:
    worker = booking.worker
    if worker is None:
        return None
    return BookingWorkerOut(
        id=worker.id,
        name=worker.user.full_name if worker.user else f"Worker {worker.id}",
        headline=worker.headline,
        rating_avg=round(worker.rating_avg, 2),
        rating_count=worker.rating_count,
        jobs_completed=worker.jobs_completed,
        phone=worker.user.phone if worker.user else "",
        availability_status=worker.availability_status,
        verification_status=worker.verification_status,
        zone=worker.zone.name if worker.zone else "",
        lat=worker.base_lat,
        lng=worker.base_lng,
    )


def _booking_fields(booking: Booking) -> dict[str, Any]:
    return {
        "id": booking.id,
        "reference": booking.reference,
        "status": booking.status,
        "urgency": booking.urgency,
        "is_emergency": booking.is_emergency,
        "service_id": booking.service_id,
        "service_name": booking.service.name if booking.service else "",
        "service_slug": booking.service.slug if booking.service else "",
        "zone_id": booking.zone_id,
        "zone_name": booking.zone.name if booking.zone else "",
        "problem_summary": booking.problem_summary,
        "raw_request": booking.raw_request,
        "address": booking.address,
        "lat": booking.lat,
        "lng": booking.lng,
        "workers_required": booking.workers_required,
        "scheduled_for": booking.scheduled_for,
        "preferred_time_label": booking.preferred_time_label,
        "estimated_price": booking.estimated_price,
        "final_price": booking.final_price,
        "distance_km": booking.distance_km,
        "customer_id": booking.customer_id,
        "customer_name": booking.customer.full_name if booking.customer else "",
        "worker": _booking_worker(booking),
        "required_skills": [link.skill.name for link in booking.required_skills],
        "created_at": booking.created_at,
        "assigned_at": booking.assigned_at,
        "accepted_at": booking.accepted_at,
        "started_at": booking.started_at,
        "completed_at": booking.completed_at,
        "payment": PaymentOut.model_validate(booking.payment) if booking.payment else None,
        "rating": RatingOut.model_validate(booking.rating) if booking.rating else None,
        "timeline": timeline_for(booking),
    }


def booking_to_out(booking: Booking) -> BookingOut:
    return BookingOut(**_booking_fields(booking))


def booking_to_detail(db: Session, booking: Booking) -> BookingDetail:
    fields = _booking_fields(booking)

    distance = booking.distance_km
    if distance is None and booking.worker is not None:
        distance = travel_distance_km(
            booking.worker.base_lat, booking.worker.base_lng, booking.lat, booking.lng
        )
        fields["distance_km"] = distance

    cooperative = db.get(Cooperative, booking.cooperative_id)
    amount = booking.final_price or booking.estimated_price
    preview = split_payment(cooperative, amount) if cooperative else None

    return BookingDetail(
        **fields,
        ai_interpretation=booking.ai_interpretation,
        match_breakdown=booking.match_breakdown,
        declined_worker_ids=list(booking.declined_worker_ids or []),
        payment_split_preview=preview,
        eta_minutes=eta_minutes(distance) if distance is not None else None,
    )
