"""Cooperative analytics.

Every figure on the admin dashboard and the analytics screen is computed here
from the database. The frontend renders what this returns; it never invents a
number of its own.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.orm import Session

from app.models import (
    ACTIVE_BOOKING_STATUSES,
    FINISHED_BOOKING_STATUSES,
    AvailabilityStatus,
    Booking,
    BookingStatus,
    Payment,
    Rating,
    ServiceCategory,
    User,
    Worker,
    Zone,
)
from app.core.timeutils import local_day_start
from app.services.forecasting import demand_trend_series
from app.services.workload import gini_fairness_score, workload_map


def _start_of_today(now: datetime) -> datetime:
    """Midnight in the cooperative's own timezone, expressed in UTC."""
    return local_day_start(now)


def dashboard_summary(
    db: Session, cooperative_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """The KPI band on the cooperative intelligence dashboard."""
    now = now or datetime.now(timezone.utc)
    today_start = _start_of_today(now)

    workers = list(
        db.execute(select(Worker).where(Worker.cooperative_id == cooperative_id))
        .scalars()
        .all()
    )
    worker_ids = [worker.id for worker in workers]
    loads = workload_map(db, worker_ids, reference=now)

    total_workers = len(workers)
    available_workers = sum(
        1 for w in workers if w.availability_status == AvailabilityStatus.AVAILABLE
    )
    off_duty = sum(
        1 for w in workers if w.availability_status == AvailabilityStatus.OFF_DUTY
    )

    active_jobs = db.execute(
        select(func.count(Booking.id)).where(
            Booking.cooperative_id == cooperative_id,
            Booking.status.in_([str(s) for s in ACTIVE_BOOKING_STATUSES]),
        )
    ).scalar() or 0

    unassigned_jobs = db.execute(
        select(func.count(Booking.id)).where(
            Booking.cooperative_id == cooperative_id,
            Booking.status == str(BookingStatus.REQUESTED),
        )
    ).scalar() or 0

    completed_today = db.execute(
        select(func.count(Booking.id)).where(
            Booking.cooperative_id == cooperative_id,
            Booking.status.in_([str(s) for s in FINISHED_BOOKING_STATUSES]),
            Booking.completed_at >= today_start,
        )
    ).scalar() or 0

    utilisation_values = [snapshot.workload_pct for snapshot in loads.values()]
    utilisation = round(sum(utilisation_values) / len(utilisation_values)) if utilisation_values else 0
    fairness = gini_fairness_score(utilisation_values)

    rating_row = db.execute(
        select(func.avg(Rating.stars), func.count(Rating.id))
        .join(Booking, Booking.id == Rating.booking_id)
        .where(Booking.cooperative_id == cooperative_id)
    ).first()
    average_rating = round(float(rating_row[0]), 2) if rating_row and rating_row[0] else 0.0
    rating_count = int(rating_row[1]) if rating_row else 0

    revenue_row = db.execute(
        select(
            func.sum(Payment.amount),
            func.sum(Payment.worker_amount),
            func.sum(Payment.welfare_amount),
            func.sum(Payment.cooperative_amount),
            func.sum(Payment.technology_amount),
        )
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Booking.cooperative_id == cooperative_id)
    ).first()

    total_bookings = db.execute(
        select(func.count(Booking.id)).where(Booking.cooperative_id == cooperative_id)
    ).scalar() or 0
    finished_bookings = db.execute(
        select(func.count(Booking.id)).where(
            Booking.cooperative_id == cooperative_id,
            Booking.status.in_([str(s) for s in FINISHED_BOOKING_STATUSES]),
        )
    ).scalar() or 0
    cancelled = db.execute(
        select(func.count(Booking.id)).where(
            Booking.cooperative_id == cooperative_id,
            Booking.status == str(BookingStatus.CANCELLED),
        )
    ).scalar() or 0

    customers = db.execute(
        select(func.count(User.id)).where(
            User.cooperative_id == cooperative_id, User.role == "CUSTOMER"
        )
    ).scalar() or 0

    return {
        "workers": total_workers,
        "available_workers": available_workers,
        "off_duty_workers": off_duty,
        "active_jobs": int(active_jobs),
        "unassigned_jobs": int(unassigned_jobs),
        "completed_today": int(completed_today),
        "worker_utilisation_pct": utilisation,
        "fairness_score": fairness,
        "average_rating": average_rating,
        "rating_count": rating_count,
        "total_bookings": int(total_bookings),
        "completed_bookings": int(finished_bookings),
        "cancelled_bookings": int(cancelled),
        "completion_rate_pct": (
            round(100 * finished_bookings / total_bookings) if total_bookings else 0
        ),
        "customers": int(customers),
        "revenue": {
            "total": float(revenue_row[0] or 0) if revenue_row else 0.0,
            "worker_earnings": float(revenue_row[1] or 0) if revenue_row else 0.0,
            "welfare_fund": float(revenue_row[2] or 0) if revenue_row else 0.0,
            "cooperative_fund": float(revenue_row[3] or 0) if revenue_row else 0.0,
            "technology_fund": float(revenue_row[4] or 0) if revenue_row else 0.0,
        },
        "generated_at": now.isoformat(),
    }


def jobs_by_service(db: Session, cooperative_id: int, days: int = 30) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(ServiceCategory.name, func.count(Booking.id))
        .join(Booking, Booking.service_id == ServiceCategory.id)
        .where(Booking.cooperative_id == cooperative_id, Booking.created_at >= since)
        .group_by(ServiceCategory.name)
        .order_by(func.count(Booking.id).desc())
    ).all()
    return [{"service": row[0], "jobs": int(row[1])} for row in rows]


def jobs_by_zone(db: Session, cooperative_id: int, days: int = 30) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(Zone.name, func.count(Booking.id))
        .join(Booking, Booking.zone_id == Zone.id)
        .where(Booking.cooperative_id == cooperative_id, Booking.created_at >= since)
        .group_by(Zone.name)
        .order_by(func.count(Booking.id).desc())
    ).all()
    return [{"zone": row[0], "jobs": int(row[1])} for row in rows]


def worker_utilisation(
    db: Session, cooperative_id: int, now: datetime | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    workers = list(
        db.execute(
            select(Worker).where(Worker.cooperative_id == cooperative_id)
        ).scalars()
    )
    loads = workload_map(db, [w.id for w in workers], reference=now)
    rows = [
        {
            "worker_id": worker.id,
            "worker": worker.user.full_name if worker.user else f"Worker {worker.id}",
            "service": worker.primary_service.name if worker.primary_service else "",
            "zone": worker.zone.name if worker.zone else "",
            "workload_pct": loads[worker.id].workload_pct,
            "committed_jobs": loads[worker.id].committed_jobs,
            "active_jobs": loads[worker.id].active_jobs,
            "weekly_capacity": loads[worker.id].weekly_capacity,
            "availability_status": worker.availability_status,
        }
        for worker in workers
        if worker.id in loads
    ]
    rows.sort(key=lambda row: row["workload_pct"], reverse=True)
    return rows[:limit] if limit else rows


def earnings_series(
    db: Session, cooperative_id: int, days: int = 30
) -> list[dict[str, Any]]:
    """Daily payment totals and how they were split."""
    now = datetime.now(timezone.utc)
    start = _start_of_today(now) - timedelta(days=days - 1)
    rows = db.execute(
        select(
            func.date(Payment.paid_at),
            func.sum(Payment.amount),
            func.sum(Payment.worker_amount),
            func.sum(Payment.welfare_amount),
        )
        .join(Booking, Booking.id == Payment.booking_id)
        .where(
            Booking.cooperative_id == cooperative_id,
            Payment.paid_at >= start,
        )
        .group_by(func.date(Payment.paid_at))
        .order_by(func.date(Payment.paid_at))
    ).all()

    by_day = {
        str(row[0]): {
            "total": float(row[1] or 0),
            "worker": float(row[2] or 0),
            "welfare": float(row[3] or 0),
        }
        for row in rows
    }
    series = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).date().isoformat()
        entry = by_day.get(day, {"total": 0.0, "worker": 0.0, "welfare": 0.0})
        series.append({"date": day, **entry})
    return series


def rating_distribution(db: Session, cooperative_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Rating.stars, func.count(Rating.id))
        .join(Booking, Booking.id == Rating.booking_id)
        .where(Booking.cooperative_id == cooperative_id)
        .group_by(Rating.stars)
    ).all()
    counts = {int(row[0]): int(row[1]) for row in rows}
    return [{"stars": stars, "count": counts.get(stars, 0)} for stars in range(1, 6)]


def rating_trend(db: Session, cooperative_id: int, weeks: int = 8) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    series: list[dict[str, Any]] = []
    for index in range(weeks - 1, -1, -1):
        end = now - timedelta(days=7 * index)
        start = end - timedelta(days=7)
        row = db.execute(
            select(func.avg(Rating.stars), func.count(Rating.id))
            .join(Booking, Booking.id == Rating.booking_id)
            .where(
                Booking.cooperative_id == cooperative_id,
                Rating.created_at >= start,
                Rating.created_at < end,
            )
        ).first()
        series.append(
            {
                "label": "This week" if index == 0 else f"-{index}w",
                "average_rating": round(float(row[0]), 2) if row and row[0] else None,
                "ratings": int(row[1]) if row else 0,
            }
        )
    return series


def completion_funnel(db: Session, cooperative_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Booking.status, func.count(Booking.id))
        .where(Booking.cooperative_id == cooperative_id)
        .group_by(Booking.status)
    ).all()
    counts = {row[0]: int(row[1]) for row in rows}
    return [
        {"status": status.value, "label": status.value.replace("_", " ").title(),
         "count": counts.get(str(status), 0)}
        for status in BookingStatus
    ]


def analytics_bundle(db: Session, cooperative_id: int, days: int = 30) -> dict[str, Any]:
    """Everything the analytics screen needs, in one round trip."""
    return {
        "range_days": days,
        "summary": dashboard_summary(db, cooperative_id),
        "jobs_by_service": jobs_by_service(db, cooperative_id, days),
        "jobs_by_zone": jobs_by_zone(db, cooperative_id, days),
        "worker_utilisation": worker_utilisation(db, cooperative_id, limit=12),
        "earnings": earnings_series(db, cooperative_id, days),
        "rating_distribution": rating_distribution(db, cooperative_id),
        "rating_trend": rating_trend(db, cooperative_id),
        "demand_trend": demand_trend_series(db, cooperative_id, days),
        "completion_funnel": completion_funnel(db, cooperative_id),
    }
