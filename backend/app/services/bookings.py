"""Booking lifecycle: creation, assignment, state transitions, payment, rating.

All business rules live here rather than in the route handlers, so the demo
flow, the seed script and the HTTP API all move bookings through exactly the
same state machine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models import (
    BOOKING_TRANSITIONS,
    AvailabilityStatus,
    Booking,
    BookingSkill,
    BookingStatus,
    Cooperative,
    Notification,
    NotificationKind,
    Payment,
    PaymentStatus,
    Rating,
    ServiceCategory,
    Skill,
    Urgency,
    User,
    WelfareRecord,
    Worker,
)

#: Price multipliers by urgency. Emergency call-outs cost more because the
#: cooperative has to interrupt a member's schedule.
URGENCY_MULTIPLIER: dict[str, float] = {
    str(Urgency.LOW): 0.95,
    str(Urgency.NORMAL): 1.0,
    str(Urgency.HIGH): 1.1,
    str(Urgency.EMERGENCY): 1.25,
}

#: Additional workers cost less than the first (shared travel and setup).
EXTRA_WORKER_FACTOR = 0.7

BOOKING_REFERENCE_PREFIX = "SK-"
INVOICE_PREFIX = "SAH-"


# ---------------------------------------------------------------------------
# Pricing and revenue split
# ---------------------------------------------------------------------------


def estimate_price(
    service: ServiceCategory, urgency: str, workers_required: int = 1
) -> float:
    multiplier = URGENCY_MULTIPLIER.get(urgency, 1.0)
    crew_factor = 1 + EXTRA_WORKER_FACTOR * max(0, workers_required - 1)
    raw = service.base_price * multiplier * crew_factor
    return float(round(raw / 10) * 10)


def split_payment(cooperative: Cooperative, amount: float) -> dict[str, float]:
    """Split a customer payment across the cooperative's funds.

    The worker takes the remainder rather than a rounded share, so the four
    parts always add back to exactly the amount the customer paid.
    """
    total = round(float(amount))
    cooperative_amount = round(total * cooperative.cooperative_share)
    welfare_amount = round(total * cooperative.welfare_share)
    technology_amount = round(total * cooperative.technology_share)
    worker_amount = total - cooperative_amount - welfare_amount - technology_amount
    return {
        "amount": float(total),
        "worker_amount": float(worker_amount),
        "cooperative_amount": float(cooperative_amount),
        "welfare_amount": float(welfare_amount),
        "technology_amount": float(technology_amount),
    }


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def _next_sequence(db: Session, model, column, prefix: str, start: int) -> str:
    highest = db.execute(select(func.count(model.id))).scalar() or 0
    candidate = start + highest + 1
    existing = {
        value
        for (value,) in db.execute(select(column).where(column.like(f"{prefix}%")))
    }
    while f"{prefix}{candidate}" in existing:
        candidate += 1
    return f"{prefix}{candidate}"


def next_booking_reference(db: Session) -> str:
    return _next_sequence(db, Booking, Booking.reference, BOOKING_REFERENCE_PREFIX, 4000)


def next_invoice_number(db: Session) -> str:
    return _next_sequence(db, Payment, Payment.invoice_number, INVOICE_PREFIX, 1000)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def notify(
    db: Session,
    user_id: int,
    kind: NotificationKind,
    title: str,
    body: str = "",
    booking_id: int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        kind=str(kind),
        title=title,
        body=body,
        booking_id=booking_id,
    )
    db.add(notification)
    return notification


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def create_booking(
    db: Session,
    *,
    customer: User,
    service: ServiceCategory,
    zone_id: int,
    cooperative_id: int,
    problem_summary: str,
    raw_request: str = "",
    address: str = "",
    lat: float = 0.0,
    lng: float = 0.0,
    urgency: str = str(Urgency.NORMAL),
    workers_required: int = 1,
    scheduled_for: datetime | None = None,
    preferred_time_label: str = "",
    skill_ids: list[int] | None = None,
    ai_interpretation: dict[str, Any] | None = None,
    is_emergency: bool = False,
    is_demo_seed: bool = False,
    status: BookingStatus = BookingStatus.REQUESTED,
    created_at: datetime | None = None,
) -> Booking:
    if urgency not in set(Urgency):
        raise UnprocessableError(f"Unknown urgency {urgency!r}.")

    booking = Booking(
        reference=next_booking_reference(db),
        customer_id=customer.id,
        cooperative_id=cooperative_id,
        service_id=service.id,
        zone_id=zone_id,
        problem_summary=problem_summary.strip()[:160] or f"{service.name} request",
        raw_request=raw_request.strip(),
        address=address.strip(),
        lat=lat,
        lng=lng,
        status=str(status),
        urgency=urgency,
        is_emergency=is_emergency or urgency == str(Urgency.EMERGENCY),
        workers_required=max(1, min(6, workers_required)),
        scheduled_for=scheduled_for,
        preferred_time_label=preferred_time_label[:64],
        estimated_price=estimate_price(service, urgency, workers_required),
        ai_interpretation=ai_interpretation,
        declined_worker_ids=[],
        is_demo_seed=is_demo_seed,
    )
    if created_at is not None:
        booking.created_at = created_at
        booking.updated_at = created_at
    db.add(booking)
    db.flush()

    for skill_id in dict.fromkeys(skill_ids or []):
        if db.get(Skill, skill_id) is not None:
            db.add(BookingSkill(booking_id=booking.id, skill_id=skill_id))

    return booking


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------


def _require_transition(booking: Booking, target: BookingStatus) -> None:
    current = BookingStatus(booking.status)
    allowed = BOOKING_TRANSITIONS.get(current, set())
    if target not in allowed:
        readable = ", ".join(sorted(str(s) for s in allowed)) or "no further changes"
        raise ConflictError(
            f"A booking that is {current.value.replace('_', ' ').lower()} cannot become "
            f"{target.value.replace('_', ' ').lower()}. Allowed next: {readable}.",
            details={"current": current.value, "attempted": target.value},
        )


def assign_worker(
    db: Session,
    booking: Booking,
    worker: Worker,
    breakdown: dict[str, Any] | None = None,
    distance_km: float | None = None,
    now: datetime | None = None,
) -> Booking:
    """Allocate a worker to a booking (REQUESTED/DECLINED -> ASSIGNED)."""
    _require_transition(booking, BookingStatus.ASSIGNED)
    if worker.availability_status == AvailabilityStatus.OFF_DUTY:
        raise ConflictError(f"{worker.user.full_name} is currently off duty.")

    now = now or datetime.now(timezone.utc)
    booking.worker_id = worker.id
    booking.status = str(BookingStatus.ASSIGNED)
    booking.assigned_at = now
    if breakdown is not None:
        booking.match_breakdown = breakdown
    if distance_km is not None:
        booking.distance_km = distance_km

    notify(
        db,
        worker.user_id,
        NotificationKind.JOB_OFFER,
        f"New {booking.service.name.lower()} job offered",
        f"{booking.problem_summary} - {booking.preferred_time_label or 'time to be confirmed'}.",
        booking.id,
    )
    notify(
        db,
        booking.customer_id,
        NotificationKind.JOB_UPDATE,
        "Worker assigned",
        f"{worker.user.full_name} has been allocated to {booking.reference}.",
        booking.id,
    )
    return booking


def change_status(
    db: Session,
    booking: Booking,
    target: BookingStatus,
    *,
    now: datetime | None = None,
    silent: bool = False,
) -> Booking:
    """Move a booking through its lifecycle, applying every side effect."""
    _require_transition(booking, target)
    now = now or datetime.now(timezone.utc)

    if target in {
        BookingStatus.ACCEPTED,
        BookingStatus.IN_PROGRESS,
        BookingStatus.COMPLETED,
    } and booking.worker_id is None:
        raise ConflictError("No worker is allocated to this booking yet.")

    worker = db.get(Worker, booking.worker_id) if booking.worker_id else None

    if target is BookingStatus.ACCEPTED:
        booking.accepted_at = now
    elif target is BookingStatus.IN_PROGRESS:
        booking.started_at = now
        if worker is not None:
            worker.availability_status = str(AvailabilityStatus.BUSY)
    elif target is BookingStatus.COMPLETED:
        booking.completed_at = now
        booking.final_price = booking.final_price or booking.estimated_price
        if worker is not None:
            worker.availability_status = str(AvailabilityStatus.AVAILABLE)
    elif target is BookingStatus.DECLINED:
        if worker is not None:
            declined = list(booking.declined_worker_ids or [])
            if worker.id not in declined:
                declined.append(worker.id)
            booking.declined_worker_ids = declined
        booking.worker_id = None
        booking.assigned_at = None
        booking.match_breakdown = None
    elif target is BookingStatus.CANCELLED:
        if worker is not None and worker.availability_status == AvailabilityStatus.BUSY:
            worker.availability_status = str(AvailabilityStatus.AVAILABLE)

    booking.status = str(target)

    if not silent:
        _notify_status(db, booking, target, worker)
    return booking


def _notify_status(
    db: Session, booking: Booking, target: BookingStatus, worker: Worker | None
) -> None:
    worker_name = worker.user.full_name if worker and worker.user else "The worker"
    messages: dict[BookingStatus, tuple[int, str, str]] = {
        BookingStatus.ACCEPTED: (
            booking.customer_id,
            "Job accepted",
            f"{worker_name} accepted {booking.reference}.",
        ),
        BookingStatus.IN_PROGRESS: (
            booking.customer_id,
            "Work started",
            f"{worker_name} has started work on {booking.reference}.",
        ),
        BookingStatus.COMPLETED: (
            booking.customer_id,
            "Service completed",
            f"{booking.problem_summary} is done. Payment is now due.",
        ),
        BookingStatus.CANCELLED: (
            booking.customer_id,
            "Booking cancelled",
            f"{booking.reference} was cancelled.",
        ),
    }
    if target in messages:
        user_id, title, body = messages[target]
        notify(db, user_id, NotificationKind.JOB_UPDATE, title, body, booking.id)

    if target is BookingStatus.DECLINED and worker is not None:
        notify(
            db,
            booking.customer_id,
            NotificationKind.JOB_UPDATE,
            "Reallocating your job",
            f"{worker_name} was unavailable. We are finding another member.",
            booking.id,
        )


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


def record_payment(
    db: Session,
    booking: Booking,
    *,
    method: str = "UPI_SIMULATED",
    now: datetime | None = None,
    silent: bool = False,
) -> Payment:
    """Simulated payment. No real financial transaction takes place."""
    if booking.payment is not None and booking.payment.status == PaymentStatus.SUCCESS:
        raise ConflictError(
            f"{booking.reference} has already been paid "
            f"(invoice {booking.payment.invoice_number})."
        )
    _require_transition(booking, BookingStatus.PAID)

    now = now or datetime.now(timezone.utc)
    cooperative = db.get(Cooperative, booking.cooperative_id)
    if cooperative is None:
        raise NotFoundError("Cooperative not found for this booking.")

    amount = booking.final_price or booking.estimated_price
    split = split_payment(cooperative, amount)

    payment = Payment(
        booking_id=booking.id,
        invoice_number=next_invoice_number(db),
        status=str(PaymentStatus.SUCCESS),
        method=method,
        paid_at=now,
        **split,
    )
    db.add(payment)

    booking.final_price = split["amount"]
    booking.status = str(BookingStatus.PAID)

    worker = db.get(Worker, booking.worker_id) if booking.worker_id else None
    if worker is not None:
        worker.total_earnings = round(worker.total_earnings + split["worker_amount"], 2)
        worker.jobs_completed += 1
        db.add(
            WelfareRecord(
                worker_id=worker.id,
                cooperative_id=cooperative.id,
                booking_id=booking.id,
                kind="CONTRIBUTION",
                amount=split["welfare_amount"],
                note=f"Welfare contribution from {booking.reference}",
            )
        )
        # Every ten completed jobs earns a training credit.
        if worker.jobs_completed % 10 == 0:
            worker.training_credits += 1
            db.add(
                WelfareRecord(
                    worker_id=worker.id,
                    cooperative_id=cooperative.id,
                    booking_id=booking.id,
                    kind="TRAINING_CREDIT",
                    amount=0.0,
                    credits=1,
                    note="Training credit earned at 10 completed jobs",
                )
            )
        if not silent:
            notify(
                db,
                worker.user_id,
                NotificationKind.PAYMENT,
                "Payment received",
                f"You earned Rs.{split['worker_amount']:.0f} from {booking.reference}.",
                booking.id,
            )

    db.flush()
    return payment


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------


def record_rating(
    db: Session,
    booking: Booking,
    *,
    stars: int,
    comment: str = "",
    silent: bool = False,
) -> Rating:
    if not 1 <= stars <= 5:
        raise UnprocessableError("A rating must be between 1 and 5 stars.")
    if booking.rating is not None:
        raise ConflictError(f"{booking.reference} has already been rated.")
    if booking.worker_id is None:
        raise ConflictError("This booking has no worker to rate.")
    _require_transition(booking, BookingStatus.RATED)

    rating = Rating(
        booking_id=booking.id,
        customer_id=booking.customer_id,
        worker_id=booking.worker_id,
        stars=stars,
        comment=comment.strip()[:2000],
    )
    db.add(rating)
    booking.status = str(BookingStatus.RATED)

    worker = db.get(Worker, booking.worker_id)
    if worker is not None:
        total = worker.rating_avg * worker.rating_count + stars
        worker.rating_count += 1
        worker.rating_avg = round(total / worker.rating_count, 2)
        if not silent:
            notify(
                db,
                worker.user_id,
                NotificationKind.RATING,
                f"New {stars}-star rating",
                comment.strip()[:200] or f"Feedback recorded for {booking.reference}.",
                booking.id,
            )

    db.flush()
    return rating


# ---------------------------------------------------------------------------
# Serialisation helper shared by the routes
# ---------------------------------------------------------------------------

STATUS_TIMELINE = (
    BookingStatus.ASSIGNED,
    BookingStatus.ACCEPTED,
    BookingStatus.IN_PROGRESS,
    BookingStatus.COMPLETED,
    BookingStatus.PAID,
    BookingStatus.RATED,
)

STATUS_ORDER = {status: index for index, status in enumerate(STATUS_TIMELINE)}


def timeline_for(booking: Booking) -> list[dict[str, Any]]:
    """Progress steps for the tracking view."""
    try:
        current_index = STATUS_ORDER[BookingStatus(booking.status)]
    except KeyError:
        current_index = -1

    timestamps = {
        BookingStatus.ASSIGNED: booking.assigned_at,
        BookingStatus.ACCEPTED: booking.accepted_at,
        BookingStatus.IN_PROGRESS: booking.started_at,
        BookingStatus.COMPLETED: booking.completed_at,
        BookingStatus.PAID: booking.payment.paid_at if booking.payment else None,
        BookingStatus.RATED: booking.rating.created_at if booking.rating else None,
    }

    steps = []
    for index, status in enumerate(STATUS_TIMELINE):
        if index < current_index:
            state = "done"
        elif index == current_index:
            state = "current"
        else:
            state = "pending"
        steps.append(
            {
                "status": str(status),
                "label": status.value.replace("_", " ").title(),
                "state": state,
                "at": timestamps[status].isoformat() if timestamps[status] else None,
            }
        )
    return steps
