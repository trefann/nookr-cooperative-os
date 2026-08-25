"""Everything the customer home screen needs, in one request."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import booking_to_out
from app.core.deps import get_current_user
from app.core.errors import PermissionDeniedError
from app.core.timeutils import ensure_utc
from app.db.session import get_db
from app.models import (
    ACTIVE_BOOKING_STATUSES,
    Booking,
    BookingStatus,
    Payment,
    User,
    UserRole,
    Worker,
)

router = APIRouter(prefix="/customer", tags=["customer"])


@router.get("/summary")
def customer_summary(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    if current_user.role == UserRole.WORKER:
        raise PermissionDeniedError("Workers use the worker portal.")

    bookings = list(
        db.execute(
            select(Booking)
            .where(Booking.customer_id == current_user.id)
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
            .order_by(Booking.id.desc())
            .limit(50)
        ).scalars().unique()
    )

    now = datetime.now(timezone.utc)
    active_statuses = {str(s) for s in ACTIVE_BOOKING_STATUSES}

    active = [b for b in bookings if b.status in active_statuses]
    awaiting_payment = [b for b in bookings if b.status == str(BookingStatus.COMPLETED)]
    awaiting_rating = [b for b in bookings if b.status == str(BookingStatus.PAID)]
    unmatched = [b for b in bookings if b.status == str(BookingStatus.REQUESTED)]
    history = [
        b
        for b in bookings
        if b.status in {str(BookingStatus.RATED), str(BookingStatus.CANCELLED)}
    ]
    upcoming = sorted(
        [b for b in active if ensure_utc(b.scheduled_for) and ensure_utc(b.scheduled_for) >= now],
        key=lambda b: ensure_utc(b.scheduled_for),
    )

    payments = list(
        db.execute(
            select(Payment)
            .join(Booking, Booking.id == Payment.booking_id)
            .where(Booking.customer_id == current_user.id)
            .order_by(Payment.paid_at.desc())
            .limit(10)
        ).scalars()
    )
    total_spent = sum(payment.amount for payment in payments)
    welfare_contributed = sum(payment.welfare_amount for payment in payments)

    ratings_given = [b.rating for b in bookings if b.rating is not None]

    return {
        "customer": {
            "id": current_user.id,
            "name": current_user.full_name,
            "email": current_user.email,
            "address": current_user.address,
            "zone_id": current_user.zone_id,
            "lat": current_user.lat,
            "lng": current_user.lng,
        },
        "counts": {
            "total": len(bookings),
            "active": len(active),
            "unmatched": len(unmatched),
            "awaiting_payment": len(awaiting_payment),
            "awaiting_rating": len(awaiting_rating),
            "completed": len(history),
        },
        "needs_attention": [
            booking_to_out(b).model_dump()
            for b in (unmatched + awaiting_payment + awaiting_rating)
        ],
        "active_service": booking_to_out(active[0]).model_dump() if active else None,
        "upcoming": [booking_to_out(b).model_dump() for b in upcoming[:5]],
        "previous": [booking_to_out(b).model_dump() for b in history[:8]],
        "payments": [
            {
                "id": payment.id,
                "invoice_number": payment.invoice_number,
                "booking_id": payment.booking_id,
                "amount": payment.amount,
                "welfare_amount": payment.welfare_amount,
                "method": payment.method,
                "status": payment.status,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            }
            for payment in payments
        ],
        "spend": {
            "total": round(total_spent, 2),
            "welfare_contributed": round(welfare_contributed, 2),
            "payments": len(payments),
        },
        "ratings": {
            "given": len(ratings_given),
            "average": (
                round(sum(r.stars for r in ratings_given) / len(ratings_given), 2)
                if ratings_given
                else None
            ),
        },
    }
