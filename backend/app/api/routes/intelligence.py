"""The AI surface: service understanding, matching, allocation, forecasting,
workforce planning, skill gaps and welfare."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.bookings import assert_can_view, load_booking
from app.core.config import settings
from app.core.deps import get_current_user, require_admin
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, UnprocessableError
from app.db.session import get_db
from app.models import (
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
from app.schemas.intelligence import AssignRequest, MatchRequest, UnderstandRequest
from app.services.ai_understanding import METHOD_RULES, understand_request
from app.services.analytics import analytics_bundle, dashboard_summary, worker_utilisation
from app.services.bookings import assign_worker
from app.services.forecasting import forecast_services
from app.services.matching import WEIGHTS, find_matches, simulate_fair_distribution
from app.services.welfare import welfare_overview
from app.services.workforce import (
    detect_skill_gaps,
    most_demanded_skills,
    plan_workforce,
    zone_pressure,
)
from app.services.workload import workload_map

router = APIRouter(tags=["intelligence"])


def _cooperative_id(db: Session, user: User) -> int:
    if user.cooperative_id is not None:
        return user.cooperative_id
    cooperative = db.execute(select(Cooperative)).scalars().first()
    if cooperative is None:
        raise ConflictError("No cooperative is configured. Seed the database first.")
    return cooperative.id


# ---------------------------------------------------------------------------
# AI #1 - Service understanding
# ---------------------------------------------------------------------------


@router.post("/ai/understand-request")
async def understand(
    payload: UnderstandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Natural language to a structured service requirement."""
    result = await understand_request(payload.text)

    service = db.execute(
        select(ServiceCategory).where(ServiceCategory.slug == result.service_slug)
    ).scalar_one_or_none()
    skills = list(
        db.execute(select(Skill).where(Skill.slug.in_(result.skill_slugs))).scalars()
    )
    zone_id = payload.zone_id or current_user.zone_id
    zone = db.get(Zone, zone_id) if zone_id else None

    estimated_price = None
    if service is not None:
        from app.services.bookings import estimate_price

        estimated_price = estimate_price(service, result.urgency, result.workers_required)

    return {
        "understanding": result.to_dict(),
        "engine": {
            "method": result.method,
            "llm_configured": settings.llm_enabled,
            "is_fallback": result.method != "llm",
            "confidence": result.confidence,
            "explanation": (
                "Interpreted by the built-in rule engine, which needs no external "
                "service."
                if result.method.startswith(METHOD_RULES)
                or result.method == "rule_based_llm_unavailable"
                else "Interpreted by the configured language model, then validated "
                "against the cooperative's service catalogue."
            ),
        },
        "service": (
            {
                "id": service.id,
                "name": service.name,
                "slug": service.slug,
                "base_price": service.base_price,
                "emergency_supported": service.emergency_supported,
            }
            if service
            else None
        ),
        "skills": [
            {"id": skill.id, "name": skill.name, "slug": skill.slug} for skill in skills
        ],
        "zone": {"id": zone.id, "name": zone.name} if zone else None,
        "estimated_price": estimated_price,
    }


# ---------------------------------------------------------------------------
# AI #2 - Matching and fair allocation
# ---------------------------------------------------------------------------


@router.post("/matching")
def match(
    payload: MatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Rank workers for a job, with the full score breakdown per candidate."""
    cooperative_id = _cooperative_id(db, current_user)

    booking: Booking | None = None
    if payload.booking_id is not None:
        booking = load_booking(db, payload.booking_id)
        assert_can_view(current_user, booking)

    if booking is not None:
        service_id = payload.service_id or booking.service_id
        skill_ids = payload.skill_ids or [
            link.skill_id for link in booking.required_skills
        ]
        lat = payload.lat if payload.lat is not None else booking.lat
        lng = payload.lng if payload.lng is not None else booking.lng
        scheduled_for = payload.scheduled_for or booking.scheduled_for
        zone_id = payload.zone_id or booking.zone_id
        workers_required = payload.workers_required or booking.workers_required
        emergency = booking.is_emergency
        exclude = list(booking.declined_worker_ids or [])
    else:
        service_id = payload.service_id
        skill_ids = payload.skill_ids
        lat = payload.lat if payload.lat is not None else current_user.lat
        lng = payload.lng if payload.lng is not None else current_user.lng
        scheduled_for = payload.scheduled_for
        zone_id = payload.zone_id or current_user.zone_id
        workers_required = payload.workers_required
        emergency = payload.urgency is Urgency.EMERGENCY
        exclude = []

    if db.get(ServiceCategory, service_id) is None:
        raise NotFoundError("That service does not exist.")

    result = find_matches(
        db,
        service_id=service_id,
        required_skill_ids=skill_ids,
        lat=lat,
        lng=lng,
        scheduled_for=scheduled_for,
        zone_id=zone_id,
        cooperative_id=cooperative_id,
        workers_required=workers_required,
        limit=payload.limit,
        exclude_worker_ids=exclude,
        emergency=emergency,
    )

    payload_out = result.to_dict()
    payload_out["booking_id"] = booking.id if booking else None
    payload_out["emergency"] = emergency
    if not result.candidates:
        payload_out["message"] = (
            "No worker currently meets the requirements for this job. "
            "Check the exclusion reasons below, or widen the requested skills."
        )
    return payload_out


@router.post("/matching/assign")
def assign(
    payload: AssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Allocate a worker, storing the score breakdown that justified it."""
    booking = load_booking(db, payload.booking_id)

    if current_user.role == UserRole.CUSTOMER and booking.customer_id != current_user.id:
        raise PermissionDeniedError("This is not your booking.")
    if current_user.role == UserRole.WORKER:
        raise PermissionDeniedError("Workers cannot allocate jobs to themselves.")

    worker = db.get(Worker, payload.worker_id)
    if worker is None:
        raise NotFoundError("That worker could not be found.")

    result = find_matches(
        db,
        service_id=booking.service_id,
        required_skill_ids=[link.skill_id for link in booking.required_skills],
        lat=booking.lat,
        lng=booking.lng,
        scheduled_for=booking.scheduled_for,
        zone_id=booking.zone_id,
        cooperative_id=booking.cooperative_id,
        workers_required=booking.workers_required,
        limit=50,
        exclude_worker_ids=list(booking.declined_worker_ids or []),
        emergency=booking.is_emergency,
    )
    candidate = next(
        (c for c in result.candidates if c.worker_id == worker.id), None
    )
    if candidate is None:
        excluded = next(
            (
                entry
                for entry in result.excluded
                if entry["worker"] == (worker.user.full_name if worker.user else "")
            ),
            None,
        )
        reason = excluded["reason"] if excluded else "not eligible for this job"
        raise ConflictError(f"{worker.user.full_name} cannot take this job: {reason}.")

    assign_worker(
        db,
        booking,
        worker,
        breakdown=candidate.to_dict(),
        distance_km=candidate.distance_km,
    )
    db.commit()

    from app.api.serializers import booking_to_detail

    return {
        "booking": booking_to_detail(db, load_booking(db, booking.id)).model_dump(),
        "allocation": candidate.to_dict(),
    }


# ---------------------------------------------------------------------------
# AI #3 - Demand forecasting
# ---------------------------------------------------------------------------


@router.get("/forecast")
def forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    zone_id: int | None = None,
) -> dict[str, Any]:
    cooperative_id = _cooperative_id(db, current_user)
    forecasts = forecast_services(db, cooperative_id, zone_id=zone_id)
    plans, headline = plan_workforce(db, cooperative_id)

    return {
        "horizon_days": 7,
        "method": "weighted_moving_average_with_damped_trend",
        "method_label": "Weighted moving average with damped trend",
        "method_note": (
            "Four weeks of cooperative history, weighted 40/30/20/10 towards "
            "recent weeks, adjusted by a halved recent trend. Confidence falls "
            "when history is short or demand has been volatile."
        ),
        "services": [item.to_dict() for item in forecasts],
        "insight": headline,
        "plans": [plan.to_dict() for plan in plans],
        "zone_pressure": zone_pressure(db, cooperative_id),
    }


# ---------------------------------------------------------------------------
# AI #4 and #5 - Workforce planning and skill gaps
# ---------------------------------------------------------------------------


@router.get("/workforce")
def workforce(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    cooperative_id = _cooperative_id(db, current_user)
    plans, headline = plan_workforce(db, cooperative_id)
    gaps = detect_skill_gaps(db, cooperative_id)
    utilisation = worker_utilisation(db, cooperative_id)

    projection_sample = (
        utilisation[:2] + utilisation[-2:] if len(utilisation) >= 4 else utilisation
    )
    return {
        "plans": [plan.to_dict() for plan in plans],
        "insight": headline,
        "skill_gaps": [gap.to_dict() for gap in gaps],
        "skill_gaps_top": [gap.to_dict() for gap in gaps if gap.gap > 0][:6],
        "most_demanded_skills": most_demanded_skills(db, cooperative_id),
        "zone_pressure": zone_pressure(db, cooperative_id),
        "utilisation": utilisation,
        "fair_distribution_projection": {
            "is_simulation": True,
            "label": "Projected effect of workload-aware allocation over the next 7 days",
            "note": (
                "A projection, not measured history. Total load is held constant; "
                "only its distribution changes as finished jobs roll out of the "
                "window and new work is shared by remaining headroom."
            ),
            "rows": simulate_fair_distribution(
                [(row["worker"], row["workload_pct"]) for row in projection_sample]
            ),
        },
        "weights": {
            key: round(value * 100) for key, value in WEIGHTS.items()
        },
    }


# ---------------------------------------------------------------------------
# Welfare
# ---------------------------------------------------------------------------


@router.get("/welfare")
def welfare(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    cooperative_id = _cooperative_id(db, current_user)
    if current_user.role == UserRole.CUSTOMER:
        raise PermissionDeniedError("Welfare records are internal to the cooperative.")
    overview = welfare_overview(db, cooperative_id)
    if current_user.role == UserRole.WORKER:
        worker = current_user.worker
        overview["workers"] = [
            row for row in overview["workers"] if worker and row["worker_id"] == worker.id
        ]
    return overview


# ---------------------------------------------------------------------------
# Dashboard and analytics
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    cooperative_id = _cooperative_id(db, current_user)
    now = datetime.now(timezone.utc)
    summary = dashboard_summary(db, cooperative_id, now)
    plans, headline = plan_workforce(db, cooperative_id)
    utilisation = worker_utilisation(db, cooperative_id)

    live_jobs = list(
        db.execute(
            select(Booking)
            .where(
                Booking.cooperative_id == cooperative_id,
                Booking.status.in_(
                    [
                        str(BookingStatus.REQUESTED),
                        str(BookingStatus.ASSIGNED),
                        str(BookingStatus.ACCEPTED),
                        str(BookingStatus.IN_PROGRESS),
                    ]
                ),
            )
            .order_by(Booking.scheduled_for.asc().nullsfirst())
            .limit(10)
        ).scalars()
    )

    cooperative = db.get(Cooperative, cooperative_id)
    return {
        "cooperative": {
            "id": cooperative.id,
            "name": cooperative.name,
            "code": cooperative.code,
            "city": cooperative.city,
            "state": cooperative.state,
            "founded_year": cooperative.founded_year,
        }
        if cooperative
        else None,
        "summary": summary,
        "insight": headline,
        "plans": [plan.to_dict() for plan in plans],
        "utilisation": utilisation[:10],
        "least_loaded": utilisation[-5:][::-1],
        "live_jobs": [
            {
                "id": job.id,
                "reference": job.reference,
                "status": job.status,
                "service": job.service.name if job.service else "",
                "zone": job.zone.name if job.zone else "",
                "problem": job.problem_summary,
                "worker": job.worker.user.full_name if job.worker and job.worker.user else None,
                "scheduled_for": job.scheduled_for.isoformat() if job.scheduled_for else None,
                "urgency": job.urgency,
            }
            for job in live_jobs
        ],
    }


@router.get("/analytics")
def analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(default=30, ge=7, le=90),
) -> dict[str, Any]:
    if current_user.role == UserRole.CUSTOMER:
        raise PermissionDeniedError("Cooperative analytics are internal.")
    cooperative_id = _cooperative_id(db, current_user)
    return analytics_bundle(db, cooperative_id, days)
