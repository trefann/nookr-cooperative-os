"""SIH demo mode.

Gives a judge a deterministic, repeatable path through the whole product:
reset to a known state, run the scripted scenario end to end, reset again.

Nothing here bypasses the real system. The demo scenario drives exactly the
same endpoints a real customer would; it only guarantees the starting state.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, token_expires_in_seconds
from app.db.seed import is_seeded, reset_database, seed_all
from app.db.seed_data import DEMO_ADMIN_EMAIL, DEMO_CUSTOMER_EMAIL, DEMO_WORKER_EMAIL
from app.db.session import get_db
from app.models import Booking, BookingStatus, Cooperative, User, Worker

router = APIRouter(prefix="/demo", tags=["demo"])

#: The scripted request. Deterministic on purpose: the rule engine resolves it
#: to Plumbing / Kitchen Sink Leakage / Tomorrow Morning every single time.
SCENARIO_REQUEST = (
    "My kitchen sink is leaking. I need a plumber tomorrow morning."
)

SCENARIO_STEPS: tuple[dict[str, str], ...] = (
    {
        "key": "understand",
        "title": "AI understands the request",
        "detail": "Free text becomes a service, problem, skills, urgency and time slot.",
        "route": "/customer",
        "actor": "Customer",
    },
    {
        "key": "candidates",
        "title": "Eligible workers are found",
        "detail": "Only members with the right skills, certification and availability.",
        "route": "/matching",
        "actor": "System",
    },
    {
        "key": "allocate",
        "title": "Fair allocation picks a worker",
        "detail": "Skill, availability, location, rating and workload, with the reasoning shown.",
        "route": "/matching",
        "actor": "Cooperative",
    },
    {
        "key": "accept",
        "title": "Worker accepts the job",
        "detail": "The offer appears in the worker portal and is accepted there.",
        "route": "/worker",
        "actor": "Worker",
    },
    {
        "key": "start",
        "title": "Worker starts the job",
        "detail": "Status moves to in progress and the customer can track it.",
        "route": "/worker",
        "actor": "Worker",
    },
    {
        "key": "complete",
        "title": "Worker completes the job",
        "detail": "The job closes and payment becomes due.",
        "route": "/worker",
        "actor": "Worker",
    },
    {
        "key": "pay",
        "title": "Customer pays",
        "detail": "Simulated payment, split across worker, cooperative, welfare and technology.",
        "route": "/customer",
        "actor": "Customer",
    },
    {
        "key": "rate",
        "title": "Customer rates the service",
        "detail": "Feedback updates the worker's rating and the cooperative's analytics.",
        "route": "/customer",
        "actor": "Customer",
    },
    {
        "key": "dashboard",
        "title": "Cooperative dashboard updates",
        "detail": "Utilisation, fairness and completion figures move with the new data.",
        "route": "/dashboard",
        "actor": "Cooperative",
    },
    {
        "key": "forecast",
        "title": "AI recommends a workforce action",
        "detail": "Demand forecast turns into a staffing and training recommendation.",
        "route": "/forecast",
        "actor": "Cooperative",
    },
)


def _demo_tokens(db: Session) -> dict[str, Any]:
    tokens: dict[str, Any] = {}
    for key, email in (
        ("customer", DEMO_CUSTOMER_EMAIL),
        ("worker", DEMO_WORKER_EMAIL),
        ("admin", DEMO_ADMIN_EMAIL),
    ):
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is not None:
            tokens[key] = {
                "user_id": user.id,
                "email": user.email,
                "name": user.full_name,
                "access_token": create_access_token(user.id, user.role),
                "expires_in": token_expires_in_seconds(),
            }
    return tokens


@router.get("/state")
def demo_state(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Is the database seeded, and is a scenario job already in flight?"""
    seeded = is_seeded(db)
    scenario_booking = None
    if seeded:
        customer = db.execute(
            select(User).where(User.email == DEMO_CUSTOMER_EMAIL)
        ).scalar_one_or_none()
        if customer is not None:
            booking = db.execute(
                select(Booking)
                .where(
                    Booking.customer_id == customer.id,
                    Booking.is_demo_seed.is_(False),
                )
                .order_by(Booking.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if booking is not None:
                scenario_booking = {
                    "id": booking.id,
                    "reference": booking.reference,
                    "status": booking.status,
                    "problem": booking.problem_summary,
                }

    return {
        "seeded": seeded,
        "bookings": db.execute(select(func.count(Booking.id))).scalar() or 0,
        "workers": db.execute(select(func.count(Worker.id))).scalar() or 0,
        "scenario_request": SCENARIO_REQUEST,
        "steps": list(SCENARIO_STEPS),
        "active_scenario_booking": scenario_booking,
        "demo_password": settings.demo_password,
        "llm_configured": settings.llm_enabled,
    }


@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Wipe and reseed, then hand back fresh tokens for the three personas.

    Seeding is deterministic, so the cooperative comes back exactly as the
    judge first saw it and the scenario can be run again from the top.
    """
    reset_database(db)
    counts = seed_all(db, quiet=True)
    return {
        "reset": True,
        "message": "Demo data restored. The scenario can be run again from the start.",
        "counts": counts,
        "tokens": _demo_tokens(db),
        "scenario_request": SCENARIO_REQUEST,
    }


@router.post("/scenario/start")
def start_scenario(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Clear any half-finished scenario job so the flow starts clean.

    Seeded history is untouched; only a previous run of the scripted scenario
    is closed off.
    """
    customer = db.execute(
        select(User).where(User.email == DEMO_CUSTOMER_EMAIL)
    ).scalar_one_or_none()
    if customer is None:
        return {
            "ready": False,
            "message": "Demo accounts are missing. Run a demo reset first.",
        }

    open_statuses = [
        str(BookingStatus.REQUESTED),
        str(BookingStatus.ASSIGNED),
        str(BookingStatus.ACCEPTED),
        str(BookingStatus.IN_PROGRESS),
        str(BookingStatus.COMPLETED),
        str(BookingStatus.PAID),
    ]
    stale = list(
        db.execute(
            select(Booking).where(
                Booking.customer_id == customer.id,
                Booking.is_demo_seed.is_(False),
                Booking.status.in_(open_statuses),
            )
        ).scalars()
    )
    for booking in stale:
        booking.status = str(BookingStatus.CANCELLED)
        if booking.worker_id is not None:
            worker = db.get(Worker, booking.worker_id)
            if worker is not None and worker.availability_status == "BUSY":
                worker.availability_status = "AVAILABLE"
    db.commit()

    cooperative = db.execute(select(Cooperative)).scalars().first()
    return {
        "ready": True,
        "cleared": len(stale),
        "scenario_request": SCENARIO_REQUEST,
        "steps": list(SCENARIO_STEPS),
        "customer": {
            "id": customer.id,
            "name": customer.full_name,
            "zone_id": customer.zone_id,
            "address": customer.address,
        },
        "cooperative": cooperative.name if cooperative else None,
        "message": (
            f"Cleared {len(stale)} in-flight demo booking(s). Ready to run."
            if stale
            else "Ready to run."
        ),
    }
