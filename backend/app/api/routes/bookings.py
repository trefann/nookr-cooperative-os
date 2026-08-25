"""Bookings: create, list, inspect and move through the lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import booking_to_detail, booking_to_out
from app.core.deps import get_current_user
from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnprocessableError,
)
from app.db.session import get_db
from app.models import (
    ACTIVE_BOOKING_STATUSES,
    Booking,
    BookingStatus,
    Cooperative,
    ServiceCategory,
    Skill,
    Urgency,
    User,
    UserRole,
    Worker,
    Zone,
)
from app.schemas.booking import BookingCreate, BookingDetail, BookingOut, BookingStatusUpdate
from app.services.ai_understanding import understand_request
from app.services.bookings import change_status, create_booking
from app.services.geo import travel_distance_km

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _loaded_booking_query():
    return select(Booking).options(
        selectinload(Booking.service),
        selectinload(Booking.zone),
        selectinload(Booking.customer),
        selectinload(Booking.worker).selectinload(Worker.user),
        selectinload(Booking.worker).selectinload(Worker.zone),
        selectinload(Booking.payment),
        selectinload(Booking.rating),
        selectinload(Booking.required_skills),
    )


def load_booking(db: Session, booking_id: int) -> Booking:
    booking = db.execute(
        _loaded_booking_query().where(Booking.id == booking_id)
    ).scalar_one_or_none()
    if booking is None:
        raise NotFoundError("That booking could not be found.")
    return booking


def assert_can_view(user: User, booking: Booking) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.CUSTOMER and booking.customer_id == user.id:
        return
    if user.role == UserRole.WORKER:
        worker = user.worker
        if worker is not None and booking.worker_id == worker.id:
            return
        # Workers may also view unassigned jobs they could be offered.
        if booking.worker_id is None:
            return
    raise PermissionDeniedError("You do not have access to this booking.")


@router.post("", response_model=BookingDetail, status_code=status.HTTP_201_CREATED)
async def create(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingDetail:
    """Create a job from a description, a chosen service, or both.

    When a description is supplied the AI understanding engine fills in the
    service, problem, skills, urgency and preferred time. Anything the customer
    set explicitly overrides what the model inferred.
    """
    if current_user.role == UserRole.WORKER:
        raise PermissionDeniedError("Workers cannot raise service requests.")

    cooperative = db.execute(select(Cooperative)).scalars().first()
    if cooperative is None:
        raise ConflictError(
            "No cooperative is configured. Seed the database before creating jobs."
        )

    interpretation: dict[str, Any] | None = None
    understanding = None
    if payload.raw_request:
        understanding = await understand_request(payload.raw_request)
        interpretation = understanding.to_dict()

    service: ServiceCategory | None = None
    if payload.service_id is not None:
        service = db.get(ServiceCategory, payload.service_id)
        if service is None:
            raise NotFoundError("That service does not exist.")
    elif understanding is not None:
        service = db.execute(
            select(ServiceCategory).where(
                ServiceCategory.slug == understanding.service_slug
            )
        ).scalar_one_or_none()
    if service is None:
        raise UnprocessableError("We could not work out which service you need.")

    zone_id = payload.zone_id or current_user.zone_id
    if zone_id is None:
        first_zone = db.execute(select(Zone).order_by(Zone.id)).scalars().first()
        if first_zone is None:
            raise ConflictError("No service zones are configured.")
        zone_id = first_zone.id
    elif db.get(Zone, zone_id) is None:
        raise NotFoundError("That service zone does not exist.")

    skill_ids = list(payload.skill_ids)
    if not skill_ids and understanding is not None:
        skill_ids = [
            skill.id
            for skill in db.execute(
                select(Skill).where(Skill.slug.in_(understanding.skill_slugs))
            ).scalars()
        ]

    urgency = (
        str(payload.urgency)
        if payload.urgency is not None
        else (understanding.urgency if understanding else str(Urgency.NORMAL))
    )
    if payload.is_emergency:
        urgency = str(Urgency.EMERGENCY)

    scheduled_for = payload.scheduled_for or (
        understanding.scheduled_for if understanding else None
    )
    if scheduled_for is None:
        scheduled_for = datetime.now(timezone.utc) + timedelta(days=1)
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)

    problem = (
        payload.problem_summary
        or (understanding.problem if understanding else "")
        or f"{service.name} request"
    )

    booking = create_booking(
        db,
        customer=current_user,
        service=service,
        zone_id=zone_id,
        cooperative_id=cooperative.id,
        problem_summary=problem,
        raw_request=payload.raw_request,
        address=payload.address or current_user.address,
        lat=payload.lat if payload.lat is not None else current_user.lat,
        lng=payload.lng if payload.lng is not None else current_user.lng,
        urgency=urgency,
        workers_required=payload.workers_required
        or (understanding.workers_required if understanding else 1),
        scheduled_for=scheduled_for,
        preferred_time_label=payload.preferred_time_label
        or (understanding.preferred_time_label if understanding else ""),
        skill_ids=skill_ids,
        ai_interpretation=interpretation,
        is_emergency=payload.is_emergency,
    )
    db.commit()
    return booking_to_detail(db, load_booking(db, booking.id))


@router.get("", response_model=list[BookingOut])
def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_status: BookingStatus | None = Query(default=None, alias="status"),
    active_only: bool = False,
    service_id: int | None = None,
    zone_id: int | None = None,
    worker_id: int | None = None,
    unassigned: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[BookingOut]:
    query = _loaded_booking_query()

    if current_user.role == UserRole.CUSTOMER:
        query = query.where(Booking.customer_id == current_user.id)
    elif current_user.role == UserRole.WORKER:
        worker = current_user.worker
        if worker is None:
            raise PermissionDeniedError("No worker profile is linked to this account.")
        # A worker sees their own jobs plus open work they could be offered.
        query = query.where(
            or_(Booking.worker_id == worker.id, Booking.worker_id.is_(None))
        )
    elif current_user.cooperative_id is not None:
        query = query.where(Booking.cooperative_id == current_user.cooperative_id)

    if booking_status is not None:
        query = query.where(Booking.status == str(booking_status))
    if active_only:
        query = query.where(
            Booking.status.in_([str(s) for s in ACTIVE_BOOKING_STATUSES])
        )
    if unassigned:
        query = query.where(Booking.worker_id.is_(None))
    if service_id is not None:
        query = query.where(Booking.service_id == service_id)
    if zone_id is not None:
        query = query.where(Booking.zone_id == zone_id)
    if worker_id is not None:
        query = query.where(Booking.worker_id == worker_id)

    bookings = db.execute(
        query.order_by(Booking.scheduled_for.desc().nullslast(), Booking.id.desc()).limit(limit)
    ).scalars().unique()
    return [booking_to_out(booking) for booking in bookings]


@router.get("/{booking_id}", response_model=BookingDetail)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingDetail:
    booking = load_booking(db, booking_id)
    assert_can_view(current_user, booking)
    return booking_to_detail(db, booking)


#: Which roles may drive which transition.
TRANSITION_PERMISSIONS: dict[BookingStatus, set[str]] = {
    BookingStatus.ACCEPTED: {UserRole.WORKER, UserRole.ADMIN},
    BookingStatus.DECLINED: {UserRole.WORKER, UserRole.ADMIN},
    BookingStatus.IN_PROGRESS: {UserRole.WORKER, UserRole.ADMIN},
    BookingStatus.COMPLETED: {UserRole.WORKER, UserRole.ADMIN},
    BookingStatus.CANCELLED: {UserRole.CUSTOMER, UserRole.ADMIN},
}


@router.patch("/{booking_id}/status", response_model=BookingDetail)
def update_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingDetail:
    """Move a booking forward. Payment and rating have their own endpoints."""
    booking = load_booking(db, booking_id)
    target = payload.status

    if target in {BookingStatus.PAID, BookingStatus.RATED}:
        raise UnprocessableError(
            "Use POST /payments to pay and POST /ratings to leave feedback."
        )
    if target is BookingStatus.ASSIGNED:
        raise UnprocessableError("Use POST /matching/assign to allocate a worker.")

    allowed_roles = TRANSITION_PERMISSIONS.get(target)
    if allowed_roles is None:
        raise UnprocessableError(f"{target.value} is not a status you can set directly.")
    if current_user.role not in allowed_roles:
        raise PermissionDeniedError(
            f"Your role cannot move a booking to {target.value.lower()}."
        )

    if current_user.role == UserRole.WORKER:
        worker = current_user.worker
        if worker is None or booking.worker_id != worker.id:
            raise PermissionDeniedError("This job is not allocated to you.")
    if current_user.role == UserRole.CUSTOMER and booking.customer_id != current_user.id:
        raise PermissionDeniedError("This is not your booking.")

    if target is BookingStatus.IN_PROGRESS and booking.worker is not None:
        booking.distance_km = booking.distance_km or travel_distance_km(
            booking.worker.base_lat, booking.worker.base_lng, booking.lat, booking.lng
        )

    change_status(db, booking, target)
    db.commit()
    return booking_to_detail(db, load_booking(db, booking_id))
