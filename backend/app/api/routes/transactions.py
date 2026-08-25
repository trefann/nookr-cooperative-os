"""Payments, ratings and notifications."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.bookings import load_booking
from app.api.serializers import booking_to_detail
from app.core.deps import get_current_user
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.db.session import get_db
from app.models import Booking, Cooperative, Notification, Payment, User, UserRole
from app.schemas.booking import PaymentOut, PaymentRequest, RatingRequest

router = APIRouter(tags=["transactions"])


@router.post("/payments", status_code=status.HTTP_201_CREATED)
def pay(
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Simulated payment. No real money moves anywhere in this system."""
    booking = load_booking(db, payload.booking_id)
    if current_user.role == UserRole.CUSTOMER and booking.customer_id != current_user.id:
        raise PermissionDeniedError("This is not your booking.")
    if current_user.role == UserRole.WORKER:
        raise PermissionDeniedError("Workers cannot take payment on a customer's behalf.")

    from app.services.bookings import record_payment

    payment = record_payment(db, booking, method=payload.method)
    db.commit()

    cooperative = db.get(Cooperative, booking.cooperative_id)
    return {
        "simulated": True,
        "notice": "Demo cooperative payment distribution. No real transaction occurred.",
        "payment": PaymentOut.model_validate(payment).model_dump(),
        "split": [
            {"label": "Worker earnings", "amount": payment.worker_amount, "key": "worker"},
            {"label": "Cooperative fund", "amount": payment.cooperative_amount, "key": "cooperative"},
            {"label": "Welfare contribution", "amount": payment.welfare_amount, "key": "welfare"},
            {"label": "Technology fund", "amount": payment.technology_amount, "key": "technology"},
        ],
        "shares": {
            "worker": cooperative.worker_share if cooperative else None,
            "cooperative": cooperative.cooperative_share if cooperative else None,
            "welfare": cooperative.welfare_share if cooperative else None,
            "technology": cooperative.technology_share if cooperative else None,
        },
        "booking": booking_to_detail(db, load_booking(db, booking.id)).model_dump(),
    }


@router.get("/payments/{booking_id}/invoice")
def invoice(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Invoice payload. The frontend renders and offers it for download."""
    booking = load_booking(db, booking_id)
    if current_user.role == UserRole.CUSTOMER and booking.customer_id != current_user.id:
        raise PermissionDeniedError("This is not your booking.")
    if booking.payment is None:
        raise NotFoundError("No payment has been recorded for this booking yet.")

    cooperative = db.get(Cooperative, booking.cooperative_id)
    payment = booking.payment
    return {
        "invoice_number": payment.invoice_number,
        "issued_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "simulated": True,
        "cooperative": {
            "name": cooperative.name if cooperative else "",
            "code": cooperative.code if cooperative else "",
            "city": cooperative.city if cooperative else "",
            "state": cooperative.state if cooperative else "",
        },
        "customer": {
            "name": booking.customer.full_name if booking.customer else "",
            "address": booking.address,
            "phone": booking.customer.phone if booking.customer else "",
        },
        "worker": {
            "name": booking.worker.user.full_name
            if booking.worker and booking.worker.user
            else None,
            "headline": booking.worker.headline if booking.worker else None,
        },
        "booking": {
            "reference": booking.reference,
            "service": booking.service.name if booking.service else "",
            "problem": booking.problem_summary,
            "completed_at": booking.completed_at.isoformat() if booking.completed_at else None,
        },
        "lines": [
            {
                "description": f"{booking.service.name if booking.service else 'Service'} - {booking.problem_summary}",
                "amount": payment.amount,
            }
        ],
        "distribution": [
            {"label": "Worker earnings", "amount": payment.worker_amount},
            {"label": "Cooperative fund", "amount": payment.cooperative_amount},
            {"label": "Welfare contribution", "amount": payment.welfare_amount},
            {"label": "Technology fund", "amount": payment.technology_amount},
        ],
        "total": payment.amount,
        "method": payment.method,
        "status": payment.status,
    }


@router.post("/ratings", status_code=status.HTTP_201_CREATED)
def rate(
    payload: RatingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    booking = load_booking(db, payload.booking_id)
    if current_user.role == UserRole.CUSTOMER and booking.customer_id != current_user.id:
        raise PermissionDeniedError("This is not your booking.")
    if current_user.role == UserRole.WORKER:
        raise PermissionDeniedError("Workers cannot rate their own jobs.")

    from app.services.bookings import record_rating

    rating = record_rating(db, booking, stars=payload.stars, comment=payload.comment)
    db.commit()

    refreshed = load_booking(db, booking.id)
    worker = refreshed.worker
    return {
        "recorded": True,
        "effects": [
            "Feedback recorded",
            "Worker performance updated",
            "Cooperative analytics updated",
            "Service data added to the intelligence layer",
        ],
        "rating": {
            "id": rating.id,
            "stars": rating.stars,
            "comment": rating.comment,
        },
        "worker": (
            {
                "id": worker.id,
                "name": worker.user.full_name if worker.user else "",
                "rating_avg": round(worker.rating_avg, 2),
                "rating_count": worker.rating_count,
            }
            if worker
            else None
        ),
        "booking": booking_to_detail(db, refreshed).model_dump(),
    }


@router.get("/notifications")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = False,
    limit: int = 30,
) -> list[dict[str, Any]]:
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    rows = db.execute(
        query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
    ).scalars()
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "body": row.body,
            "booking_id": row.booking_id,
            "is_read": row.is_read,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.patch("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise NotFoundError("That notification could not be found.")
    notification.is_read = True
    db.commit()
    return {"id": notification.id, "is_read": True}
