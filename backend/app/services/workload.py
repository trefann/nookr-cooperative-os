"""Worker workload measurement.

Workload is *derived from the database*, never stored as a hand-set number.
A worker's load is the count of jobs committed inside a rolling seven-day
window (three days back, four days forward) measured against the weekly job
capacity recorded on their profile.  Jobs that were declined or cancelled do
not count, because they consume none of the worker's time.

This single definition is used by the fairness component of matching, by the
admin utilisation panel and by the workforce planner, so all three always
agree.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import ACTIVE_BOOKING_STATUSES, Booking, BookingStatus, Worker

WINDOW_DAYS_BACK = 3
WINDOW_DAYS_FORWARD = 4

#: Statuses that consume capacity: everything except declined/cancelled.
COUNTED_STATUSES = tuple(
    status
    for status in BookingStatus
    if status not in {BookingStatus.DECLINED, BookingStatus.CANCELLED}
)


@dataclass(frozen=True)
class WorkloadSnapshot:
    worker_id: int
    committed_jobs: int
    active_jobs: int
    weekly_capacity: int

    @property
    def workload_pct(self) -> int:
        if self.weekly_capacity <= 0:
            return 100
        return min(100, round(100 * self.committed_jobs / self.weekly_capacity))

    @property
    def fairness_score(self) -> float:
        """0..1, where 1 means this worker has the most room to take work."""
        return round(1.0 - (self.workload_pct / 100.0), 4)

    @property
    def has_headroom(self) -> bool:
        return self.committed_jobs < self.weekly_capacity


def window_bounds(reference: datetime | None = None) -> tuple[datetime, datetime]:
    now = reference or datetime.now(timezone.utc)
    return (
        now - timedelta(days=WINDOW_DAYS_BACK),
        now + timedelta(days=WINDOW_DAYS_FORWARD),
    )


def workload_map(
    db: Session,
    worker_ids: Sequence[int] | None = None,
    reference: datetime | None = None,
) -> dict[int, WorkloadSnapshot]:
    """Workload snapshot per worker id.

    Workers with no bookings still get an entry, so callers never have to
    guard against a missing key.
    """
    start, end = window_bounds(reference)

    worker_query = select(Worker.id, Worker.weekly_capacity)
    if worker_ids is not None:
        if not worker_ids:
            return {}
        worker_query = worker_query.where(Worker.id.in_(worker_ids))
    capacities = {row.id: row.weekly_capacity for row in db.execute(worker_query)}
    if not capacities:
        return {}

    committed_stmt = (
        select(Booking.worker_id, func.count(Booking.id))
        .where(
            Booking.worker_id.in_(capacities.keys()),
            Booking.status.in_([str(s) for s in COUNTED_STATUSES]),
            or_(
                Booking.scheduled_for.is_(None),
                Booking.scheduled_for.between(start, end),
            ),
        )
        .group_by(Booking.worker_id)
    )
    committed = {row[0]: row[1] for row in db.execute(committed_stmt)}

    active_stmt = (
        select(Booking.worker_id, func.count(Booking.id))
        .where(
            Booking.worker_id.in_(capacities.keys()),
            Booking.status.in_([str(s) for s in ACTIVE_BOOKING_STATUSES]),
        )
        .group_by(Booking.worker_id)
    )
    active = {row[0]: row[1] for row in db.execute(active_stmt)}

    return {
        worker_id: WorkloadSnapshot(
            worker_id=worker_id,
            committed_jobs=committed.get(worker_id, 0),
            active_jobs=active.get(worker_id, 0),
            weekly_capacity=capacity,
        )
        for worker_id, capacity in capacities.items()
    }


def snapshot_for(
    db: Session, worker_id: int, reference: datetime | None = None
) -> WorkloadSnapshot:
    result = workload_map(db, [worker_id], reference)
    return result.get(
        worker_id,
        WorkloadSnapshot(
            worker_id=worker_id, committed_jobs=0, active_jobs=0, weekly_capacity=1
        ),
    )


def gini_fairness_score(workloads: Sequence[int]) -> int:
    """Cooperative fairness score out of 100.

    Computed as 100 * (1 - Gini coefficient) over worker workload percentages.
    A perfectly even distribution of work scores 100; work concentrated on a
    few members scores low.  This is a real inequality measure, not a
    hand-tuned number.
    """
    values = [max(0, v) for v in workloads]
    if len(values) < 2:
        return 100
    total = sum(values)
    if total == 0:
        return 100
    values.sort()
    n = len(values)
    weighted = sum((index + 1) * value for index, value in enumerate(values))
    gini = (2 * weighted) / (n * total) - (n + 1) / n
    return max(0, min(100, round(100 * (1 - gini))))
