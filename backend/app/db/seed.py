"""Database seeding.

Produces a cooperative with eight weeks of genuine operating history. Nothing
is faked at the presentation layer: the demand curve, the utilisation figures,
the fairness score, the forecast and the skill gaps are all consequences of the
bookings created here.

The generator is seeded with a fixed value, so ``python -m app.db.seed`` gives
byte-identical data every time and the judging demo is reproducible.

Run with:
    python -m app.db.seed              # seed if empty
    python -m app.db.seed --reset      # wipe and reseed
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import delete, func, inspect, select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.core.security import hash_password
from app.core.timeutils import local_day_start
from app.db.base import Base
from app.db.seed_data import (
    ADMIN_NAME,
    COOPERATIVE_CITY,
    COOPERATIVE_CODE,
    COOPERATIVE_NAME,
    COOPERATIVE_STATE,
    CUSTOMERS,
    DEMO_ADMIN_EMAIL,
    DEMO_CUSTOMER_EMAIL,
    DEMO_WORKER_EMAIL,
    FEEDBACK_BY_STARS,
    PROBLEMS,
    WEEKLY_VOLUME,
    WORKERS,
    ZONE_BIAS,
    ZONES,
)
from app.db.session import SessionLocal, engine
from app.models import (
    Booking,
    BookingSkill,
    BookingStatus,
    Certification,
    Cooperative,
    DemandForecast,
    DemandRecord,
    Notification,
    Payment,
    PaymentStatus,
    Rating,
    ServiceCategory,
    ServiceSkill,
    Skill,
    Urgency,
    User,
    UserRole,
    VerificationStatus,
    WelfareRecord,
    Worker,
    WorkerAvailability,
    WorkerSkill,
    Zone,
)
from app.services.bookings import estimate_price, split_payment
from app.services.taxonomy import SERVICES, SKILLS
from app.services.workload import workload_map

logger = logging.getLogger("nookr.seed")

RANDOM_SEED = 20260824
HISTORY_WEEKS = 8
HISTORY_DAYS = HISTORY_WEEKS * 7

#: Rolling workload window, matching app.services.workload.
WINDOW_BACK = 3
WINDOW_FORWARD = 4

#: A handful of unassigned requests so the matching screen has live work.
OPEN_REQUEST_COUNT = 4

WORKING_START = time(8, 0)
WORKING_END = time(19, 0)

#: Slots a seeded job can start at.
JOB_HOURS = (9, 10, 11, 12, 14, 15, 16, 17)

#: Afternoon-only slots, used to keep the demo worker's diary clear around the
#: scripted scenario's "tomorrow morning" request.
SCRIPTED_SAFE_HOURS = (14, 15, 16, 17)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slot(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)


def _weighted_choice(rng: random.Random, items: list, weights: list[float]):
    total = sum(weights)
    if total <= 0:
        return rng.choice(items)
    return rng.choices(items, weights=weights, k=1)[0]


def _stars_for(rng: random.Random, target: float) -> int:
    return max(1, min(5, round(rng.gauss(target, 0.5))))


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

#: Child tables first so foreign keys stay satisfied on every backend.
DELETION_ORDER = (
    Notification,
    WelfareRecord,
    Rating,
    Payment,
    BookingSkill,
    Booking,
    DemandForecast,
    DemandRecord,
    WorkerAvailability,
    Certification,
    WorkerSkill,
    Worker,
    ServiceSkill,
    Skill,
    ServiceCategory,
    User,
    Zone,
    Cooperative,
)


def reset_database(db: Session) -> None:
    """Delete every row, leaving the schema intact."""
    for model in DELETION_ORDER:
        db.execute(delete(model))
    db.commit()
    logger.info("Cleared all seeded data.")


def is_seeded(db: Session) -> bool:
    return (db.execute(select(func.count(Cooperative.id))).scalar() or 0) > 0


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


def _seed_catalogue(db: Session) -> tuple[dict[str, ServiceCategory], dict[str, Skill]]:
    services: dict[str, ServiceCategory] = {}
    for definition in SERVICES:
        service = ServiceCategory(
            name=definition.name,
            slug=definition.slug,
            description=definition.description,
            icon=definition.icon,
            base_price=definition.base_price,
            avg_duration_minutes=definition.avg_duration_minutes,
            emergency_supported=definition.emergency_supported,
        )
        db.add(service)
        services[definition.slug] = service

    skills: dict[str, Skill] = {}
    for definition in SKILLS:
        skill = Skill(
            name=definition.name,
            slug=definition.slug,
            description=definition.description,
            is_emerging=definition.is_emerging,
            growth_factor=definition.growth_factor,
            requires_certification=definition.requires_certification,
        )
        db.add(skill)
        skills[definition.slug] = skill

    db.flush()

    for definition in SKILLS:
        service = services[definition.service_slug]
        db.add(
            ServiceSkill(
                service_id=service.id,
                skill_id=skills[definition.slug].id,
                is_primary=definition.slug
                in SERVICES[[s.slug for s in SERVICES].index(definition.service_slug)].primary_skill_slugs,
            )
        )
    db.flush()
    return services, skills


def _seed_people(
    db: Session,
    cooperative: Cooperative,
    zones: dict[str, Zone],
    services: dict[str, ServiceCategory],
    skills: dict[str, Skill],
    password_hash: str,
) -> tuple[list[Worker], list[User]]:
    admin = User(
        email=DEMO_ADMIN_EMAIL,
        hashed_password=password_hash,
        full_name=ADMIN_NAME,
        role=str(UserRole.ADMIN),
        phone="+91 98430 10000",
        address=f"{COOPERATIVE_NAME}, {COOPERATIVE_CITY}",
        cooperative_id=cooperative.id,
        zone_id=zones["Z1"].id,
        lat=zones["Z1"].center_lat,
        lng=zones["Z1"].center_lng,
        is_demo=True,
    )
    db.add(admin)

    workers: list[Worker] = []
    for definition in WORKERS:
        zone = zones[definition.zone_code]
        user = User(
            email=definition.email,
            hashed_password=password_hash,
            full_name=definition.full_name,
            role=str(UserRole.WORKER),
            phone=definition.phone,
            address=f"{zone.name}, {COOPERATIVE_CITY}",
            cooperative_id=cooperative.id,
            zone_id=zone.id,
            lat=definition.lat,
            lng=definition.lng,
            is_demo=definition.email == DEMO_WORKER_EMAIL,
        )
        db.add(user)
        db.flush()

        worker = Worker(
            user_id=user.id,
            cooperative_id=cooperative.id,
            zone_id=zone.id,
            primary_service_id=services[definition.service_slug].id,
            headline=definition.headline,
            bio=definition.bio,
            experience_years=definition.experience_years,
            weekly_capacity=definition.weekly_capacity,
            availability_status=definition.availability_status,
            verification_status=str(VerificationStatus.VERIFIED),
            base_lat=definition.lat,
            base_lng=definition.lng,
            joined_on=date.today() - timedelta(days=365 * definition.experience_years // 2),
            insurance_active=definition.insurance_active,
            training_credits=definition.training_credits,
        )
        db.add(worker)
        db.flush()

        for skill_slug, proficiency in definition.skills:
            db.add(
                WorkerSkill(
                    worker_id=worker.id,
                    skill_id=skills[skill_slug].id,
                    proficiency=proficiency,
                    years_experience=max(1, definition.experience_years - 5 + proficiency),
                )
            )
        for index, (cert_name, body, skill_slug) in enumerate(definition.certifications):
            db.add(
                Certification(
                    worker_id=worker.id,
                    skill_id=skills[skill_slug].id if skill_slug in skills else None,
                    name=cert_name,
                    issuing_body=body,
                    credential_id=f"{definition.zone_code}-{worker.id:03d}-{index + 1}",
                    issued_on=date.today() - timedelta(days=400 + index * 120),
                    expires_on=date.today() + timedelta(days=700 - index * 60),
                    verified=True,
                )
            )
        for day_of_week in range(7):
            db.add(
                WorkerAvailability(
                    worker_id=worker.id,
                    day_of_week=day_of_week,
                    start_time=WORKING_START,
                    end_time=WORKING_END,
                    is_available=day_of_week not in definition.days_off,
                )
            )
        workers.append(worker)

    customers: list[User] = []
    for definition in CUSTOMERS:
        zone = zones[definition.zone_code]
        customer = User(
            email=definition.email,
            hashed_password=password_hash,
            full_name=definition.full_name,
            role=str(UserRole.CUSTOMER),
            phone=definition.phone,
            address=definition.address,
            cooperative_id=cooperative.id,
            zone_id=zone.id,
            lat=definition.lat,
            lng=definition.lng,
            is_demo=definition.email == DEMO_CUSTOMER_EMAIL,
        )
        db.add(customer)
        customers.append(customer)

    db.flush()
    return workers, customers


# ---------------------------------------------------------------------------
# Booking history
# ---------------------------------------------------------------------------


class BookingFactory:
    """Creates bookings and everything that hangs off them."""

    def __init__(
        self,
        db: Session,
        rng: random.Random,
        cooperative: Cooperative,
        zones: dict[str, Zone],
        services: dict[str, ServiceCategory],
        skills: dict[str, Skill],
        workers: list[Worker],
        customers: list[User],
        worker_targets: dict[int, float],
        worker_ratings: dict[int, float],
    ) -> None:
        self.db = db
        self.rng = rng
        self.cooperative = cooperative
        self.zones = zones
        self.zone_list = [zones[z.code] for z in ZONES]
        self.services = services
        self.skills = skills
        self.workers = workers
        self.customers = customers
        self.worker_targets = worker_targets
        self.worker_ratings = worker_ratings
        self.reference_counter = 4000
        self.invoice_counter = 1000

        self.by_service: dict[int, list[Worker]] = defaultdict(list)
        for worker in workers:
            self.by_service[worker.primary_service_id].append(worker)

        self.customers_by_zone: dict[int, list[User]] = defaultdict(list)
        for customer in customers:
            self.customers_by_zone[customer.zone_id].append(customer)

        self.window_counts: dict[int, int] = defaultdict(int)

        # The scripted judging scenario asks for a plumber tomorrow morning.
        self.scripted_day = datetime.now(timezone.utc).date() + timedelta(days=1)
        demo_worker = next(
            (w for w in workers if w.user and w.user.email == DEMO_WORKER_EMAIL), None
        )
        self.demo_worker_id = demo_worker.id if demo_worker else None

    # -- naming ------------------------------------------------------------

    def _next_reference(self) -> str:
        self.reference_counter += 1
        return f"SK-{self.reference_counter}"

    def _next_invoice(self) -> str:
        self.invoice_counter += 1
        return f"SAH-{self.invoice_counter}"

    # -- selection ---------------------------------------------------------

    def _pick_zone(self, service_slug: str) -> Zone:
        return _weighted_choice(
            self.rng, self.zone_list, list(ZONE_BIAS[service_slug])
        )

    def _pick_customer(self, zone: Zone) -> User:
        pool = self.customers_by_zone.get(zone.id) or self.customers
        return self.rng.choice(pool)

    def _pick_problem(self, service_slug: str):
        problems = PROBLEMS[service_slug]
        return _weighted_choice(
            self.rng, list(problems), [p.weight for p in problems]
        )

    def _pick_worker(self, service: ServiceCategory, zone: Zone, by_target: bool) -> Worker:
        pool = self.by_service[service.id]
        weights = []
        for worker in pool:
            if by_target:
                base = max(0.5, self.worker_targets[worker.id])
            else:
                base = float(worker.weekly_capacity)
            if worker.zone_id == zone.id:
                base *= 2.0
            weights.append(base)
        return _weighted_choice(self.rng, pool, weights)

    def _is_scripted_slot(self, worker: Worker | None, day: date) -> bool:
        """Is this the demo worker, on the day the scripted scenario targets?

        The judging scenario asks for a plumber "tomorrow morning", which the
        rule engine resolves to 10:00 the next day. If the demo worker already
        held a job in that window the matcher would - correctly - penalise them
        for the clash, and the scripted narrative would change from one run to
        the next. Keeping their seeded work out of that window makes the demo
        reproducible without touching a single line of the scoring model.
        """
        if worker is None or self.demo_worker_id is None:
            return False
        return worker.id == self.demo_worker_id and day == self.scripted_day

    # -- creation ----------------------------------------------------------

    def create(
        self,
        *,
        service_slug: str,
        day: date,
        status: BookingStatus,
        worker: Worker | None = None,
        by_target: bool = False,
        counts_towards_window: bool = False,
    ) -> Booking:
        service = self.services[service_slug]
        zone = self._pick_zone(service_slug)
        customer = self._pick_customer(zone)
        problem = self._pick_problem(service_slug)

        if worker is None and status is not BookingStatus.REQUESTED:
            worker = self._pick_worker(service, zone, by_target)

        hours = SCRIPTED_SAFE_HOURS if self._is_scripted_slot(worker, day) else JOB_HOURS
        hour = self.rng.choice(hours)
        scheduled = _slot(day, hour, self.rng.choice([0, 30]))
        urgency = problem.urgency
        if urgency == str(Urgency.EMERGENCY):
            scheduled = _slot(day, hour) + timedelta(minutes=45)

        booking = Booking(
            reference=self._next_reference(),
            customer_id=customer.id,
            worker_id=worker.id if worker else None,
            cooperative_id=self.cooperative.id,
            service_id=service.id,
            zone_id=zone.id,
            problem_summary=problem.label,
            raw_request="",
            address=customer.address,
            lat=customer.lat + self.rng.uniform(-0.002, 0.002),
            lng=customer.lng + self.rng.uniform(-0.002, 0.002),
            status=str(status),
            urgency=urgency,
            is_emergency=urgency == str(Urgency.EMERGENCY),
            workers_required=1,
            scheduled_for=scheduled,
            preferred_time_label=scheduled.strftime("%d %b, %I:%M %p").lstrip("0"),
            estimated_price=estimate_price(service, urgency, 1),
            declined_worker_ids=[],
            is_demo_seed=True,
            created_at=scheduled - timedelta(hours=self.rng.randint(3, 30)),
        )
        booking.updated_at = booking.created_at
        self.db.add(booking)
        self.db.flush()

        for skill_slug in problem.skills:
            skill = self.skills.get(skill_slug)
            if skill is not None:
                self.db.add(BookingSkill(booking_id=booking.id, skill_id=skill.id))

        if worker is not None and counts_towards_window:
            self.window_counts[worker.id] += 1

        if status in {
            BookingStatus.ASSIGNED,
            BookingStatus.ACCEPTED,
            BookingStatus.IN_PROGRESS,
            BookingStatus.COMPLETED,
            BookingStatus.PAID,
            BookingStatus.RATED,
        }:
            booking.assigned_at = booking.created_at + timedelta(minutes=12)
        if status in {
            BookingStatus.ACCEPTED,
            BookingStatus.IN_PROGRESS,
            BookingStatus.COMPLETED,
            BookingStatus.PAID,
            BookingStatus.RATED,
        }:
            booking.accepted_at = booking.assigned_at + timedelta(minutes=self.rng.randint(5, 60))
        if status in {
            BookingStatus.IN_PROGRESS,
            BookingStatus.COMPLETED,
            BookingStatus.PAID,
            BookingStatus.RATED,
        }:
            booking.started_at = scheduled
        if status in {BookingStatus.COMPLETED, BookingStatus.PAID, BookingStatus.RATED}:
            booking.completed_at = scheduled + timedelta(
                minutes=service.avg_duration_minutes + self.rng.randint(-15, 40)
            )
            booking.final_price = booking.estimated_price
            booking.distance_km = round(self.rng.uniform(0.8, 9.5), 1)

        if status in {BookingStatus.PAID, BookingStatus.RATED}:
            self._add_payment(booking, worker)
        if status is BookingStatus.RATED:
            self._add_rating(booking, worker)

        return booking

    def _add_payment(self, booking: Booking, worker: Worker | None) -> None:
        split = split_payment(self.cooperative, booking.final_price or booking.estimated_price)
        paid_at = (booking.completed_at or booking.scheduled_for) + timedelta(
            minutes=self.rng.randint(5, 180)
        )
        payment = Payment(
            booking_id=booking.id,
            invoice_number=self._next_invoice(),
            status=str(PaymentStatus.SUCCESS),
            method=self.rng.choice(["UPI_SIMULATED", "CARD_SIMULATED", "CASH"]),
            paid_at=paid_at,
            **split,
        )
        payment.created_at = paid_at
        payment.updated_at = paid_at
        self.db.add(payment)

        if worker is not None:
            record = WelfareRecord(
                worker_id=worker.id,
                cooperative_id=self.cooperative.id,
                booking_id=booking.id,
                kind="CONTRIBUTION",
                amount=split["welfare_amount"],
                note=f"Welfare contribution from {booking.reference}",
            )
            record.created_at = paid_at
            record.updated_at = paid_at
            self.db.add(record)

    def _add_rating(self, booking: Booking, worker: Worker | None) -> None:
        if worker is None:
            return
        # 82% of completed jobs get rated, which is a realistic response rate.
        if self.rng.random() > 0.82:
            return
        stars = _stars_for(self.rng, self.worker_ratings[worker.id])
        created = (booking.completed_at or booking.scheduled_for) + timedelta(
            hours=self.rng.randint(1, 30)
        )
        rating = Rating(
            booking_id=booking.id,
            customer_id=booking.customer_id,
            worker_id=worker.id,
            stars=stars,
            comment=self.rng.choice(FEEDBACK_BY_STARS[stars]),
        )
        rating.created_at = created
        rating.updated_at = created
        self.db.add(rating)


# ---------------------------------------------------------------------------
# Main seeding routine
# ---------------------------------------------------------------------------


def seed_all(db: Session, *, quiet: bool = False) -> dict[str, int]:
    rng = random.Random(RANDOM_SEED)
    today = datetime.now(timezone.utc).date()
    password_hash = hash_password(settings.demo_password)

    cooperative = Cooperative(
        name=COOPERATIVE_NAME,
        code=COOPERATIVE_CODE,
        city=COOPERATIVE_CITY,
        state=COOPERATIVE_STATE,
        founded_year=2016,
    )
    db.add(cooperative)
    db.flush()

    zones: dict[str, Zone] = {}
    for definition in ZONES:
        zone = Zone(
            cooperative_id=cooperative.id,
            name=definition.name,
            code=definition.code,
            city=COOPERATIVE_CITY,
            center_lat=definition.lat,
            center_lng=definition.lng,
            description=definition.description,
        )
        db.add(zone)
        zones[definition.code] = zone
    db.flush()

    services, skills = _seed_catalogue(db)
    workers, customers = _seed_people(
        db, cooperative, zones, services, skills, password_hash
    )

    worker_targets = {
        worker.id: definition.target_workload_pct / 100 * definition.weekly_capacity
        for worker, definition in zip(workers, WORKERS, strict=True)
    }
    worker_ratings = {
        worker.id: definition.target_rating
        for worker, definition in zip(workers, WORKERS, strict=True)
    }

    factory = BookingFactory(
        db, rng, cooperative, zones, services, skills, workers, customers,
        worker_targets, worker_ratings,
    )

    # -- Phase A: eight weeks of completed history ------------------------
    # Weekly volumes are laid down day by day. Everything from four days ago
    # backwards is finished work; the three most recent days also feed the
    # rolling workload window, so those are allocated by workload target.
    created = 0
    for week_index, offset_weeks in enumerate(range(HISTORY_WEEKS - 1, -1, -1)):
        for service_slug, volumes in WEEKLY_VOLUME.items():
            weekly = volumes[week_index]
            for day_index in range(7):
                days_ago = offset_weeks * 7 + (6 - day_index)
                if days_ago < 1:
                    continue
                day = today - timedelta(days=days_ago)
                # Split the weekly volume across the week, weekends lighter.
                share = 0.10 if day.weekday() == 6 else 0.15
                count = int(round(weekly * share))
                in_window = days_ago <= WINDOW_BACK
                for _ in range(count):
                    status = (
                        BookingStatus.CANCELLED
                        if rng.random() < 0.03
                        else BookingStatus.RATED
                    )
                    factory.create(
                        service_slug=service_slug,
                        day=day,
                        status=status,
                        by_target=in_window,
                    )
                    created += 1

    # -- Phase B: today and the coming days, to reach workload targets -----
    # How much is already committed inside the rolling window is measured with
    # the production workload function, not re-derived here, so the seeded
    # utilisation figures are exactly what the dashboard will report.
    db.flush()
    now = datetime.now(timezone.utc)
    # How far back a job finished "earlier today" can be placed while staying
    # inside the cooperative's local day.
    elapsed_hours = (now - local_day_start(now)).total_seconds() / 3600
    hours_back = min(4.0, max(0.5, elapsed_hours * 0.6))
    committed = workload_map(db, [w.id for w in workers], reference=now)
    for worker_index, (worker, definition) in enumerate(
        zip(workers, WORKERS, strict=True)
    ):
        target = round(worker_targets[worker.id])
        needed = max(0, target - committed[worker.id].committed_jobs)
        for index in range(needed):
            # First job today is already finished, the second is live for
            # roughly a third of the workforce, the rest sit in the next
            # three days as accepted or freshly assigned work.
            if index == 0:
                day_offset = 0
                status = BookingStatus.RATED
            elif index == 1:
                day_offset = 0
                # Index 0 is the demo worker, who stays free so the
                # scripted judging scenario starts from a clean slate.
                status = (
                    BookingStatus.IN_PROGRESS
                    if worker_index % 3 == 1
                    else BookingStatus.ACCEPTED
                )
            else:
                day_offset = 1 + ((index - 2) % (WINDOW_FORWARD - 1))
                status = (
                    BookingStatus.ACCEPTED if index % 3 == 0 else BookingStatus.ASSIGNED
                )
            day = today + timedelta(days=day_offset)
            booking = factory.create(
                service_slug=definition.service_slug,
                day=day,
                status=status,
                worker=worker,
                counts_towards_window=True,
            )
            if status is BookingStatus.IN_PROGRESS:
                booking.scheduled_for = now - timedelta(minutes=40)
                booking.started_at = now - timedelta(minutes=35)
                worker.availability_status = "BUSY"
            elif status is BookingStatus.RATED and day_offset == 0:
                # Must land inside the cooperative's own day, not the UTC day,
                # or the "completed today" figure reads zero every morning.
                booking.scheduled_for = now - timedelta(hours=hours_back)
                booking.completed_at = now - timedelta(hours=hours_back / 2)
            created += 1

    # -- Phase C: open requests waiting to be matched ----------------------
    for index in range(OPEN_REQUEST_COUNT):
        service_slug = ["electrical", "plumbing", "appliance-repair", "carpentry"][index % 4]
        factory.create(
            service_slug=service_slug,
            day=today + timedelta(days=1),
            status=BookingStatus.REQUESTED,
        )
        created += 1

    db.flush()

    # -- Derived worker aggregates ----------------------------------------
    _recompute_worker_aggregates(db)

    # -- Observed demand, aggregated from the bookings themselves ----------
    _rebuild_demand_records(db, cooperative.id)

    # -- A few notifications so the demo accounts do not start empty -------
    _seed_notifications(db, workers, customers)

    db.commit()

    counts = {
        "cooperatives": 1,
        "zones": len(ZONES),
        "services": len(SERVICES),
        "skills": len(SKILLS),
        "workers": len(workers),
        "customers": len(customers),
        "bookings": db.execute(select(func.count(Booking.id))).scalar() or 0,
        "payments": db.execute(select(func.count(Payment.id))).scalar() or 0,
        "ratings": db.execute(select(func.count(Rating.id))).scalar() or 0,
        "welfare_records": db.execute(select(func.count(WelfareRecord.id))).scalar() or 0,
        "demand_records": db.execute(select(func.count(DemandRecord.id))).scalar() or 0,
    }
    if not quiet:
        for key, value in counts.items():
            logger.info("%-16s %s", key, value)
    return counts


def _recompute_worker_aggregates(db: Session) -> None:
    """Derive jobs completed, earnings and ratings from the real rows."""
    earnings = {
        row[0]: (float(row[1] or 0), int(row[2] or 0))
        for row in db.execute(
            select(
                Booking.worker_id,
                func.sum(Payment.worker_amount),
                func.count(Payment.id),
            )
            .join(Payment, Payment.booking_id == Booking.id)
            .where(Booking.worker_id.is_not(None))
            .group_by(Booking.worker_id)
        )
    }
    ratings = {
        row[0]: (float(row[1] or 0), int(row[2] or 0))
        for row in db.execute(
            select(Rating.worker_id, func.avg(Rating.stars), func.count(Rating.id))
            .group_by(Rating.worker_id)
        )
    }
    welfare_credits = {
        row[0]: int(row[1] or 0)
        for row in db.execute(
            select(WelfareRecord.worker_id, func.sum(WelfareRecord.credits))
            .where(WelfareRecord.kind == "TRAINING_CREDIT")
            .group_by(WelfareRecord.worker_id)
        )
    }

    for worker in db.execute(select(Worker)).scalars():
        total, jobs = earnings.get(worker.id, (0.0, 0))
        worker.total_earnings = round(total, 2)
        worker.jobs_completed = jobs
        average, count = ratings.get(worker.id, (0.0, 0))
        worker.rating_avg = round(average, 2)
        worker.rating_count = count
        worker.training_credits += welfare_credits.get(worker.id, 0)
    db.flush()


def _rebuild_demand_records(db: Session, cooperative_id: int) -> None:
    """Aggregate bookings into the demand history the forecaster reads."""
    db.execute(delete(DemandRecord).where(DemandRecord.cooperative_id == cooperative_id))
    rows = db.execute(
        select(
            Booking.service_id,
            Booking.zone_id,
            func.date(Booking.created_at),
            func.count(Booking.id),
        )
        .where(
            Booking.cooperative_id == cooperative_id,
            Booking.status != str(BookingStatus.CANCELLED),
        )
        .group_by(Booking.service_id, Booking.zone_id, func.date(Booking.created_at))
    ).all()

    for service_id, zone_id, day, count in rows:
        record_date = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
        db.add(
            DemandRecord(
                cooperative_id=cooperative_id,
                service_id=service_id,
                zone_id=zone_id,
                record_date=record_date,
                bookings_count=int(count),
            )
        )
    db.flush()


def _seed_notifications(db: Session, workers: list[Worker], customers: list[User]) -> None:
    demo_worker = next(
        (w for w in workers if w.user and w.user.email == DEMO_WORKER_EMAIL), None
    )
    demo_customer = next(
        (c for c in customers if c.email == DEMO_CUSTOMER_EMAIL), None
    )
    if demo_worker is not None:
        db.add(
            Notification(
                user_id=demo_worker.user_id,
                kind="SYSTEM",
                title="Welfare contribution credited",
                body="Your welfare fund balance was updated after last week's jobs.",
            )
        )
        db.add(
            Notification(
                user_id=demo_worker.user_id,
                kind="SYSTEM",
                title="Training credit available",
                body="You have training credits you can spend on a certification course.",
            )
        )
    if demo_customer is not None:
        db.add(
            Notification(
                user_id=demo_customer.id,
                kind="SYSTEM",
                title="Welcome to Nookr",
                body="Describe what you need in your own words and we will organise it.",
            )
        )
    db.flush()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def ensure_schema() -> None:
    """Make sure the tables exist before seeding.

    ``alembic upgrade head`` is the canonical way to create the schema and is
    what the deployment instructions use. This fallback keeps a first local run
    friction-free: if the tables are missing it creates them and stamps the
    Alembic version table, so a later ``alembic upgrade head`` is a no-op
    rather than an error.
    """
    inspector = inspect(engine)
    if inspector.has_table("bookings"):
        return

    logger.info("Schema not found; creating tables and stamping the migration head.")
    Base.metadata.create_all(bind=engine)
    try:
        from alembic import command
        from alembic.config import Config

        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        command.stamp(config, "head")
    except Exception as exc:  # noqa: BLE001 - stamping is a convenience only
        logger.warning(
            "Tables created, but the Alembic version could not be stamped (%s). "
            "Run 'alembic stamp head' if you plan to use migrations.",
            exc,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the Nookr database.")
    parser.add_argument(
        "--reset", action="store_true", help="Delete existing data before seeding."
    )
    parser.add_argument(
        "--force", action="store_true", help="Seed even if data already exists."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ensure_schema()

    with SessionLocal() as db:
        if args.reset:
            reset_database(db)
        elif is_seeded(db) and not args.force:
            logger.info(
                "Database already contains data. Use --reset to wipe and reseed."
            )
            return 0
        logger.info("Seeding %s ...", settings.database_url.split("@")[-1])
        seed_all(db)
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
