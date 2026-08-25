"""Worker directory and the signed-in worker's own profile."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import booking_to_out, worker_to_detail, worker_to_out
from app.core.deps import get_current_user, get_current_worker
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import (
    ACTIVE_BOOKING_STATUSES,
    AvailabilityStatus,
    Booking,
    Payment,
    User,
    Worker,
    WorkerSkill,
)
from app.schemas.worker import AvailabilityUpdate, WorkerDetail, WorkerOut
from app.services.geo import travel_distance_km
from app.services.welfare import worker_welfare
from app.services.workload import snapshot_for, workload_map

router = APIRouter(prefix="/workers", tags=["workers"])


def _loaded_worker_query():
    return select(Worker).options(
        selectinload(Worker.user),
        selectinload(Worker.zone),
        selectinload(Worker.primary_service),
        selectinload(Worker.skills).selectinload(WorkerSkill.skill),
        selectinload(Worker.certifications),
        selectinload(Worker.availability),
    )


@router.get("", response_model=list[WorkerOut])
def list_workers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service_id: int | None = None,
    zone_id: int | None = None,
    skill_id: int | None = None,
    availability: AvailabilityStatus | None = None,
    search: str | None = Query(default=None, max_length=80),
    lat: float | None = None,
    lng: float | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WorkerOut]:
    query = _loaded_worker_query()
    if current_user.cooperative_id is not None:
        query = query.where(Worker.cooperative_id == current_user.cooperative_id)
    if service_id is not None:
        query = query.where(Worker.primary_service_id == service_id)
    if zone_id is not None:
        query = query.where(Worker.zone_id == zone_id)
    if availability is not None:
        query = query.where(Worker.availability_status == str(availability))
    if skill_id is not None:
        query = query.where(
            Worker.id.in_(select(WorkerSkill.worker_id).where(WorkerSkill.skill_id == skill_id))
        )
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.join(User, User.id == Worker.user_id).where(
            User.full_name.ilike(term)
        )

    workers = list(db.execute(query.limit(limit)).scalars().unique())
    loads = workload_map(db, [worker.id for worker in workers])

    results = []
    for worker in workers:
        distance = (
            travel_distance_km(worker.base_lat, worker.base_lng, lat, lng)
            if lat is not None and lng is not None
            else None
        )
        results.append(worker_to_out(worker, loads.get(worker.id), distance))
    results.sort(key=lambda w: (-w.rating_avg, w.workload_pct))
    return results


@router.get("/me", response_model=WorkerDetail)
def my_profile(
    worker: Worker = Depends(get_current_worker), db: Session = Depends(get_db)
) -> WorkerDetail:
    loaded = db.execute(
        _loaded_worker_query().where(Worker.id == worker.id)
    ).scalar_one()
    return worker_to_detail(loaded, snapshot_for(db, worker.id))


@router.get("/me/summary")
def my_summary(
    worker: Worker = Depends(get_current_worker), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Everything the worker portal home needs in one call."""
    now = datetime.now(timezone.utc)
    snapshot = snapshot_for(db, worker.id, now)

    bookings = list(
        db.execute(
            select(Booking)
            .where(Booking.worker_id == worker.id)
            .options(
                selectinload(Booking.service),
                selectinload(Booking.zone),
                selectinload(Booking.customer),
                selectinload(Booking.worker).selectinload(Worker.user),
                selectinload(Booking.worker).selectinload(Worker.zone),
                selectinload(Booking.payment),
                selectinload(Booking.rating),
                selectinload(Booking.required_skills),
            )
            .order_by(Booking.scheduled_for.desc())
            .limit(60)
        ).scalars().unique()
    )

    active_statuses = {str(s) for s in ACTIVE_BOOKING_STATUSES}
    active = [b for b in bookings if b.status in active_statuses]
    completed = [b for b in bookings if b.status in {"COMPLETED", "PAID", "RATED"}]

    earnings_row = db.execute(
        select(Payment.worker_amount)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Booking.worker_id == worker.id)
    ).scalars().all()
    week_start = now - timedelta(days=7)
    week_earnings = db.execute(
        select(Payment.worker_amount)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Booking.worker_id == worker.id, Payment.paid_at >= week_start)
    ).scalars().all()

    return {
        "profile": worker_to_detail(
            db.execute(_loaded_worker_query().where(Worker.id == worker.id)).scalar_one(),
            snapshot,
        ).model_dump(),
        "workload": {
            "workload_pct": snapshot.workload_pct,
            "committed_jobs": snapshot.committed_jobs,
            "active_jobs": snapshot.active_jobs,
            "weekly_capacity": snapshot.weekly_capacity,
            "has_headroom": snapshot.has_headroom,
        },
        "earnings": {
            "total": round(sum(earnings_row), 2),
            "last_7_days": round(sum(week_earnings), 2),
            "jobs_paid": len(earnings_row),
        },
        "active_jobs": [booking_to_out(b).model_dump() for b in active],
        "recent_jobs": [booking_to_out(b).model_dump() for b in completed[:10]],
        "welfare": worker_welfare(db, worker.id),
    }


@router.patch("/me/availability", response_model=WorkerDetail)
def update_availability(
    payload: AvailabilityUpdate,
    worker: Worker = Depends(get_current_worker),
    db: Session = Depends(get_db),
) -> WorkerDetail:
    worker.availability_status = str(payload.availability_status)
    db.commit()
    loaded = db.execute(_loaded_worker_query().where(Worker.id == worker.id)).scalar_one()
    return worker_to_detail(loaded, snapshot_for(db, worker.id))


@router.get("/{worker_id}", response_model=WorkerDetail)
def get_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    lat: float | None = None,
    lng: float | None = None,
) -> WorkerDetail:
    worker = db.execute(
        _loaded_worker_query().where(Worker.id == worker_id)
    ).scalar_one_or_none()
    if worker is None:
        raise NotFoundError("That worker could not be found.")
    distance = (
        travel_distance_km(worker.base_lat, worker.base_lng, lat, lng)
        if lat is not None and lng is not None
        else None
    )
    return worker_to_detail(worker, snapshot_for(db, worker.id), distance)
