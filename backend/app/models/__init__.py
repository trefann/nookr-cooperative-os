"""SQLAlchemy models.

Importing this package registers every table on the shared declarative Base,
which Alembic's autogenerate and the seed script both rely on.
"""

from app.models.booking import Booking, BookingSkill, Payment, Rating
from app.models.catalog import ServiceCategory, ServiceSkill, Skill
from app.models.core import Cooperative, User, Zone
from app.models.enums import (
    ACTIVE_BOOKING_STATUSES,
    BOOKING_TRANSITIONS,
    FINISHED_BOOKING_STATUSES,
    AvailabilityStatus,
    BookingStatus,
    NotificationKind,
    PaymentStatus,
    Urgency,
    UserRole,
    VerificationStatus,
)
from app.models.intelligence import (
    DemandForecast,
    DemandRecord,
    Notification,
    WelfareRecord,
)
from app.models.worker import Certification, Worker, WorkerAvailability, WorkerSkill

__all__ = [
    "ACTIVE_BOOKING_STATUSES",
    "BOOKING_TRANSITIONS",
    "FINISHED_BOOKING_STATUSES",
    "AvailabilityStatus",
    "Booking",
    "BookingSkill",
    "BookingStatus",
    "Certification",
    "Cooperative",
    "DemandForecast",
    "DemandRecord",
    "Notification",
    "NotificationKind",
    "Payment",
    "PaymentStatus",
    "Rating",
    "ServiceCategory",
    "ServiceSkill",
    "Skill",
    "Urgency",
    "User",
    "UserRole",
    "VerificationStatus",
    "WelfareRecord",
    "Worker",
    "WorkerAvailability",
    "WorkerSkill",
    "Zone",
]
