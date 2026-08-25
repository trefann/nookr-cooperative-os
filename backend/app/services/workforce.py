"""AI #4 - Workforce planning, and AI #5 - Skill gap detection.

Both are deterministic capacity models that consume the demand forecast:

  forecast demand  ->  jobs a worker can absorb in a week  ->  workers required
  workers required vs workers available                    ->  gap
  gap                                                      ->  recommendation

Every number on the workforce and skill-gap screens is produced here from
database facts. Nothing is hardcoded in the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from math import ceil
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AvailabilityStatus,
    Booking,
    BookingSkill,
    Certification,
    ServiceCategory,
    ServiceSkill,
    Skill,
    VerificationStatus,
    Worker,
    WorkerSkill,
    Zone,
)
from app.core.timeutils import local_today
from app.services.forecasting import forecast_services

#: A cooperative plans to run its members at this utilisation, not at 100%:
#: headroom absorbs emergencies, travel and sick days.
TARGET_UTILISATION = 0.85

#: Fallback when a worker has no capacity recorded.
DEFAULT_WEEKLY_CAPACITY = 12

#: Window used to measure which skills real jobs have been asking for.
SKILL_DEMAND_DAYS = 28

#: Specialist skills (certified or emerging) are only part of a holder's week:
#: an electrician certified for solar still spends most of their time on
#: general electrical work. This is the share of a month they can give to one
#: specialist skill, and it is the only reason specialist gaps look tighter
#: than general ones.
SPECIALIST_CAPACITY_SHARE = 0.30


@dataclass
class ServicePlan:
    service_id: int
    service_name: str
    service_slug: str
    predicted_demand: int
    required_workers: int
    available_workers: int
    gap: int                       # available - required; negative is a shortage
    utilisation_pct: int
    priority_zone: str | None
    priority_zone_id: int | None
    confidence: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_slug": self.service_slug,
            "predicted_demand": self.predicted_demand,
            "required_workers": self.required_workers,
            "available_workers": self.available_workers,
            "gap": self.gap,
            "status": (
                "shortage" if self.gap < 0 else "surplus" if self.gap > 0 else "balanced"
            ),
            "utilisation_pct": self.utilisation_pct,
            "priority_zone": self.priority_zone,
            "priority_zone_id": self.priority_zone_id,
            "confidence": round(self.confidence, 2),
            "recommendation": self.recommendation,
        }


@dataclass
class SkillGap:
    skill_id: int
    skill_name: str
    skill_slug: str
    service_name: str
    is_emerging: bool
    requires_certification: bool
    is_specialist: bool
    recent_jobs: int
    projected_jobs: int
    required_workers: int
    available_workers: int
    certified_workers: int
    gap: int                       # required - available; positive is a shortage
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_slug": self.skill_slug,
            "service_name": self.service_name,
            "is_emerging": self.is_emerging,
            "requires_certification": self.requires_certification,
            "is_specialist": self.is_specialist,
            "capacity_basis": (
                "specialist_share" if self.is_specialist else "full_capacity"
            ),
            "recent_jobs": self.recent_jobs,
            "projected_jobs": self.projected_jobs,
            "required_workers": self.required_workers,
            "available_workers": self.available_workers,
            "certified_workers": self.certified_workers,
            "gap": self.gap,
            "status": "shortage" if self.gap > 0 else "covered",
            "recommendation": self.recommendation,
        }


def _effective_weekly_jobs(db: Session, cooperative_id: int) -> float:
    """Average jobs one worker can absorb per week at target utilisation."""
    average = db.execute(
        select(func.avg(Worker.weekly_capacity)).where(
            Worker.cooperative_id == cooperative_id
        )
    ).scalar()
    capacity = float(average or DEFAULT_WEEKLY_CAPACITY)
    return max(1.0, capacity * TARGET_UTILISATION)


def _available_workers_by_service(db: Session, cooperative_id: int) -> dict[int, int]:
    rows = db.execute(
        select(Worker.primary_service_id, func.count(Worker.id))
        .where(
            Worker.cooperative_id == cooperative_id,
            Worker.verification_status == str(VerificationStatus.VERIFIED),
            Worker.availability_status != str(AvailabilityStatus.OFF_DUTY),
        )
        .group_by(Worker.primary_service_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def plan_workforce(
    db: Session, cooperative_id: int, today: date | None = None
) -> tuple[list[ServicePlan], dict[str, Any]]:
    """AI #4. Returns per-service plans plus a headline recommendation."""
    forecasts = forecast_services(db, cooperative_id, today=today)
    jobs_per_worker = _effective_weekly_jobs(db, cooperative_id)
    available = _available_workers_by_service(db, cooperative_id)

    plans: list[ServicePlan] = []
    for forecast in forecasts:
        required = max(1, ceil(forecast.predicted_demand / jobs_per_worker)) if forecast.predicted_demand else 0
        have = available.get(forecast.service_id, 0)
        gap = have - required
        utilisation = (
            min(200, round(100 * forecast.predicted_demand / (have * jobs_per_worker)))
            if have
            else 0
        )

        if gap < 0:
            zone_hint = f" and prioritise {forecast.top_zone}" if forecast.top_zone else ""
            recommendation = (
                f"Activate {abs(gap)} additional "
                f"{forecast.service_name.lower()} worker{'s' if abs(gap) > 1 else ''}"
                f"{zone_hint}."
            )
        elif gap > 0:
            recommendation = (
                f"{gap} {forecast.service_name.lower()} worker"
                f"{'s have' if gap > 1 else ' has'} spare capacity. "
                "Consider cross-training or reallocating to a service in shortage."
            )
        else:
            recommendation = (
                f"{forecast.service_name} capacity matches forecast demand. Hold steady."
            )

        plans.append(
            ServicePlan(
                service_id=forecast.service_id,
                service_name=forecast.service_name,
                service_slug=forecast.service_slug,
                predicted_demand=forecast.predicted_demand,
                required_workers=required,
                available_workers=have,
                gap=gap,
                utilisation_pct=utilisation,
                priority_zone=forecast.top_zone,
                priority_zone_id=forecast.top_zone_id,
                confidence=forecast.confidence,
                recommendation=recommendation,
            )
        )

    plans.sort(key=lambda plan: (plan.gap, -plan.predicted_demand))

    shortages = [plan for plan in plans if plan.gap < 0]
    surpluses = [plan for plan in plans if plan.gap > 0]
    if shortages:
        worst = shortages[0]
        forecast = next(f for f in forecasts if f.service_id == worst.service_id)
        headline = {
            "kind": "shortage",
            "service": worst.service_name,
            "service_slug": worst.service_slug,
            "change_pct": round(forecast.change_pct, 1),
            "predicted_demand": worst.predicted_demand,
            "required_workers": worst.required_workers,
            "available_workers": worst.available_workers,
            "shortage": abs(worst.gap),
            "priority_zone": worst.priority_zone,
            "confidence": round(worst.confidence, 2),
            "headline": (
                f"{worst.service_name} demand is forecast to run "
                f"{forecast.change_pct:+.0f}% against its four-week average."
            ),
            "recommendation": worst.recommendation,
            "supporting": (
                f"Available {worst.service_name.lower()} workers: {worst.available_workers} - "
                f"required: {worst.required_workers} - shortage: {abs(worst.gap)}."
            ),
        }
        if surpluses:
            headline["reallocation"] = (
                f"{surpluses[-1].service_name} has {surpluses[-1].gap} worker"
                f"{'s' if surpluses[-1].gap > 1 else ''} with spare capacity that "
                f"could be cross-trained for {worst.service_name.lower()}."
            )
    else:
        top = max(plans, key=lambda plan: plan.predicted_demand, default=None)
        headline = {
            "kind": "balanced",
            "service": top.service_name if top else None,
            "headline": "Forecast demand is within current workforce capacity.",
            "recommendation": (
                "No activation needed this week. Keep monitoring emerging skills."
            ),
            "supporting": (
                f"Highest volume service: {top.service_name} "
                f"({top.predicted_demand} jobs forecast)." if top else ""
            ),
        }

    return plans, headline


# ---------------------------------------------------------------------------
# AI #5 - Skill gap detection
# ---------------------------------------------------------------------------


def detect_skill_gaps(
    db: Session,
    cooperative_id: int,
    today: date | None = None,
    limit: int | None = None,
) -> list[SkillGap]:
    """Compare projected skill demand against certified capacity."""
    today = today or local_today()
    since = datetime.combine(
        today - timedelta(days=SKILL_DEMAND_DAYS), datetime.min.time(), timezone.utc
    )

    demand_rows = db.execute(
        select(BookingSkill.skill_id, func.count(BookingSkill.id))
        .join(Booking, Booking.id == BookingSkill.booking_id)
        .where(
            Booking.cooperative_id == cooperative_id,
            Booking.created_at >= since,
        )
        .group_by(BookingSkill.skill_id)
    ).all()
    recent_by_skill = {row[0]: int(row[1]) for row in demand_rows}

    holder_rows = db.execute(
        select(WorkerSkill.skill_id, func.count(WorkerSkill.worker_id))
        .join(Worker, Worker.id == WorkerSkill.worker_id)
        .where(
            Worker.cooperative_id == cooperative_id,
            Worker.availability_status != str(AvailabilityStatus.OFF_DUTY),
        )
        .group_by(WorkerSkill.skill_id)
    ).all()
    holders_by_skill = {row[0]: int(row[1]) for row in holder_rows}

    cert_rows = db.execute(
        select(Certification.skill_id, func.count(func.distinct(Certification.worker_id)))
        .join(Worker, Worker.id == Certification.worker_id)
        .where(
            Worker.cooperative_id == cooperative_id,
            Certification.verified.is_(True),
            Certification.skill_id.is_not(None),
        )
        .group_by(Certification.skill_id)
    ).all()
    certified_by_skill = {row[0]: int(row[1]) for row in cert_rows}

    service_by_skill: dict[int, str] = {}
    skill_service_rows = db.execute(
        select(ServiceSkill.skill_id, ServiceCategory.name).join(
            ServiceCategory, ServiceCategory.id == ServiceSkill.service_id
        )
    ).all()
    for skill_id, service_name in skill_service_rows:
        service_by_skill.setdefault(skill_id, service_name)

    jobs_per_worker_month = _effective_weekly_jobs(db, cooperative_id) * 4

    gaps: list[SkillGap] = []
    for skill in db.execute(select(Skill)).scalars():
        recent = recent_by_skill.get(skill.id, 0)
        projected = round(recent * skill.growth_factor)
        available = holders_by_skill.get(skill.id, 0)
        certified = certified_by_skill.get(skill.id, 0)

        # Two regimes, both stated plainly in the API response:
        #  - general skills: every holder of the skill can serve it full time.
        #  - specialist skills (certified or emerging): a holder can only give
        #    part of their month to it, and certified skills count only workers
        #    holding a verified credential.
        specialist = skill.requires_certification or skill.is_emerging
        if specialist:
            capacity_per_worker = jobs_per_worker_month * SPECIALIST_CAPACITY_SHARE
            capacity_pool = certified if skill.requires_certification else available
        else:
            capacity_per_worker = jobs_per_worker_month
            capacity_pool = available

        required = ceil(projected / capacity_per_worker) if projected else 0
        gap = max(0, required - capacity_pool)

        if gap > 0:
            if skill.requires_certification:
                recommendation = (
                    f"Certify {gap} more worker{'s' if gap > 1 else ''} in "
                    f"{skill.name}; {available - certified} already have the skill "
                    "but no verified certification."
                    if available > certified
                    else f"Train and certify {gap} eligible "
                    f"{service_by_skill.get(skill.id, 'cooperative').lower()} "
                    f"worker{'s' if gap > 1 else ''} in {skill.name}."
                )
            elif specialist:
                recommendation = (
                    f"Train {gap} eligible "
                    f"{service_by_skill.get(skill.id, 'cooperative').lower()} "
                    f"worker{'s' if gap > 1 else ''} in {skill.name}."
                )
            else:
                # A general skill running short is a headcount problem, not a
                # training one: the people who have it are simply outnumbered.
                recommendation = (
                    f"Add {gap} more "
                    f"{service_by_skill.get(skill.id, 'cooperative').lower()} "
                    f"worker{'s' if gap > 1 else ''} - "
                    f"{available} member{'s' if available != 1 else ''} currently "
                    f"cover {skill.name} against {projected} projected jobs."
                )
        elif skill.is_emerging:
            recommendation = (
                f"{skill.name} is covered today, but demand is growing "
                f"{round((skill.growth_factor - 1) * 100)}% - keep training in the pipeline."
            )
        else:
            recommendation = f"{skill.name} is adequately covered."

        gaps.append(
            SkillGap(
                skill_id=skill.id,
                skill_name=skill.name,
                skill_slug=skill.slug,
                service_name=service_by_skill.get(skill.id, ""),
                is_emerging=skill.is_emerging,
                requires_certification=skill.requires_certification,
                is_specialist=specialist,
                recent_jobs=recent,
                projected_jobs=projected,
                required_workers=required,
                available_workers=available,
                certified_workers=certified,
                gap=gap,
                recommendation=recommendation,
            )
        )

    gaps.sort(key=lambda item: (-item.gap, -item.projected_jobs))
    return gaps[:limit] if limit else gaps


def most_demanded_skills(
    db: Session, cooperative_id: int, limit: int = 8, days: int = SKILL_DEMAND_DAYS
) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(Skill.name, func.count(BookingSkill.id))
        .join(BookingSkill, BookingSkill.skill_id == Skill.id)
        .join(Booking, Booking.id == BookingSkill.booking_id)
        .where(Booking.cooperative_id == cooperative_id, Booking.created_at >= since)
        .group_by(Skill.name)
        .order_by(func.count(BookingSkill.id).desc())
        .limit(limit)
    ).all()
    return [{"skill": row[0], "jobs": int(row[1])} for row in rows]


def zone_pressure(
    db: Session, cooperative_id: int, today: date | None = None
) -> list[dict[str, Any]]:
    """Which zones are carrying the most work relative to workers based there."""
    today = today or local_today()
    since = datetime.combine(
        today - timedelta(days=14), datetime.min.time(), timezone.utc
    )

    job_rows = db.execute(
        select(Booking.zone_id, func.count(Booking.id))
        .where(Booking.cooperative_id == cooperative_id, Booking.created_at >= since)
        .group_by(Booking.zone_id)
    ).all()
    jobs_by_zone = {row[0]: int(row[1]) for row in job_rows}

    worker_rows = db.execute(
        select(Worker.zone_id, func.count(Worker.id))
        .where(Worker.cooperative_id == cooperative_id)
        .group_by(Worker.zone_id)
    ).all()
    workers_by_zone = {row[0]: int(row[1]) for row in worker_rows}

    results: list[dict[str, Any]] = []
    for zone in db.execute(
        select(Zone).where(Zone.cooperative_id == cooperative_id).order_by(Zone.name)
    ).scalars():
        jobs = jobs_by_zone.get(zone.id, 0)
        workers = workers_by_zone.get(zone.id, 0)
        results.append(
            {
                "zone_id": zone.id,
                "zone": zone.name,
                "jobs_last_14_days": jobs,
                "workers": workers,
                "jobs_per_worker": round(jobs / workers, 1) if workers else None,
            }
        )
    results.sort(key=lambda item: item["jobs_per_worker"] or 0, reverse=True)
    return results
