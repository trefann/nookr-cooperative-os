"""Domain enumerations.

Stored as plain strings so that migrations stay portable between SQLite and
PostgreSQL (native PG ENUM types are painful to alter).
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    WORKER = "WORKER"
    ADMIN = "ADMIN"


class BookingStatus(StrEnum):
    REQUESTED = "REQUESTED"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PAID = "PAID"
    RATED = "RATED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


#: Legal state machine for a booking.  Enforced in the service layer so an
#: invalid transition returns 409 rather than silently corrupting data.
BOOKING_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.REQUESTED: {BookingStatus.ASSIGNED, BookingStatus.CANCELLED},
    BookingStatus.ASSIGNED: {
        BookingStatus.ACCEPTED,
        BookingStatus.DECLINED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.ACCEPTED: {BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED},
    BookingStatus.IN_PROGRESS: {BookingStatus.COMPLETED},
    BookingStatus.COMPLETED: {BookingStatus.PAID},
    BookingStatus.PAID: {BookingStatus.RATED},
    BookingStatus.RATED: set(),
    # A declined job returns to the pool and can be re-assigned.
    BookingStatus.DECLINED: {BookingStatus.ASSIGNED, BookingStatus.CANCELLED},
    BookingStatus.CANCELLED: set(),
}

#: Statuses that occupy a worker's capacity right now.
ACTIVE_BOOKING_STATUSES = (
    BookingStatus.ASSIGNED,
    BookingStatus.ACCEPTED,
    BookingStatus.IN_PROGRESS,
)

#: Statuses meaning the work itself is finished.
FINISHED_BOOKING_STATUSES = (
    BookingStatus.COMPLETED,
    BookingStatus.PAID,
    BookingStatus.RATED,
)


class Urgency(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFF_DUTY = "OFF_DUTY"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"


class NotificationKind(StrEnum):
    JOB_OFFER = "JOB_OFFER"
    JOB_UPDATE = "JOB_UPDATE"
    PAYMENT = "PAYMENT"
    RATING = "RATING"
    SYSTEM = "SYSTEM"
