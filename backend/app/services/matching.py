"""AI #2 - Explainable worker matching and fair allocation.

This is deliberately *not* "nearest worker wins" and *not* "highest rated wins".
Every candidate is scored on five weighted components, one of which is
fairness: how much of their weekly capacity a worker has already committed.
A slightly closer but heavily loaded worker will lose to a nearby member who
has room, which is the behaviour a cooperative actually wants.

The score is computed server-side and the full component breakdown is returned
with every candidate, so the interface can always answer "why this worker?".

Nothing here is a black box: it is a transparent weighted model over real
database facts. It is labelled as such in the UI rather than being dressed up
as deep learning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ACTIVE_BOOKING_STATUSES,
    AvailabilityStatus,
    Booking,
    Certification,
    ServiceCategory,
    Skill,
    VerificationStatus,
    Worker,
    WorkerSkill,
)
from app.core.timeutils import ensure_utc
from app.services.geo import eta_minutes, proximity_score, travel_distance_km
from app.services.workload import WorkloadSnapshot, workload_map

# ---------------------------------------------------------------------------
# Scoring weights. These are the product's fairness policy, in one place.
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "skill": 0.30,
    "availability": 0.20,
    "location": 0.15,
    "rating": 0.15,
    "fairness": 0.20,
}

COMPONENT_LABELS: dict[str, str] = {
    "skill": "Skill Match",
    "availability": "Availability",
    "location": "Location",
    "rating": "Rating",
    "fairness": "Fairness",
}

#: Ratings are shrunk towards this prior so a worker with a single 5-star job
#: does not outrank a consistently strong member with 90 ratings.
RATING_PRIOR = 4.0
RATING_PRIOR_WEIGHT = 5.0

#: A worker more than this far over their weekly capacity is not offered work.
OVERLOAD_CUTOFF = 1.25

#: Jobs within this window of the requested slot count as a clash.
CLASH_WINDOW = timedelta(minutes=90)


@dataclass
class ComponentScore:
    key: str
    label: str
    score: float           # 0..1
    weight: float
    reason: str

    @property
    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "score": round(self.score, 4),
            "percent": round(self.score * 100),
            "weight": self.weight,
            "weight_percent": round(self.weight * 100),
            "contribution": round(self.weighted * 100, 1),
            "reason": self.reason,
        }


@dataclass
class MatchCandidate:
    worker_id: int
    worker_name: str
    headline: str
    zone_name: str
    rating_avg: float
    rating_count: int
    jobs_completed: int
    distance_km: float
    eta_minutes: int
    availability_status: str
    verification_status: str
    workload_pct: int
    matched_skills: list[str]
    missing_skills: list[str]
    certifications: list[str]
    components: list[ComponentScore]
    final_score: float          # 0..1
    explanation: str
    warnings: list[str] = field(default_factory=list)
    recommended: bool = False

    @property
    def score_percent(self) -> int:
        return round(self.final_score * 100)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["components"] = [component.to_dict() for component in self.components]
        payload["final_score"] = round(self.final_score, 4)
        payload["score_percent"] = self.score_percent
        return payload


@dataclass
class MatchResult:
    candidates: list[MatchCandidate]
    considered: int
    excluded: list[dict[str, str]]
    weights: dict[str, float]
    workers_required: int
    method: str = "weighted_explainable_scoring"

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "workers_required": self.workers_required,
            "considered": self.considered,
            "weights": {
                key: {"label": COMPONENT_LABELS[key], "percent": round(value * 100)}
                for key, value in self.weights.items()
            },
            "excluded": self.excluded,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "recommended": (
                self.candidates[0].to_dict() if self.candidates else None
            ),
        }


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------


def _skill_component(
    worker: Worker, required_skill_ids: set[int], service_id: int
) -> tuple[ComponentScore, list[str], list[str]]:
    held = {link.skill_id: link for link in worker.skills}
    matched_names: list[str] = []
    missing_names: list[str] = []

    if not required_skill_ids:
        coverage = 1.0 if worker.primary_service_id == service_id else 0.6
    else:
        per_skill: list[float] = []
        for link in worker.skills:
            if link.skill_id in required_skill_ids:
                matched_names.append(link.skill.name)
        for skill_id in required_skill_ids:
            link = held.get(skill_id)
            if link is None:
                per_skill.append(0.0)
            else:
                # proficiency 1..5 maps to 0.65..1.00
                per_skill.append(0.65 + 0.35 * (link.proficiency - 1) / 4)
        coverage = sum(per_skill) / len(per_skill)

    service_bonus = 1.0 if worker.primary_service_id == service_id else 0.0
    score = min(1.0, 0.85 * coverage + 0.15 * service_bonus)

    covered = len(matched_names)
    total = len(required_skill_ids) or 1
    if required_skill_ids:
        reason = f"Holds {covered} of {total} required skills"
        if matched_names:
            reason += f" ({', '.join(sorted(matched_names))})"
    else:
        reason = "No specific skills required; scored on primary service"

    return (
        ComponentScore("skill", COMPONENT_LABELS["skill"], score, WEIGHTS["skill"], reason),
        sorted(set(matched_names)),
        missing_names,
    )


#: A worker who is on a job right now is only penalised for work starting
#: within this window. Being busy this afternoon says nothing about whether
#: someone can take a job tomorrow morning.
IMMINENT_WINDOW = timedelta(hours=4)


def _availability_component(
    worker: Worker,
    scheduled_for: datetime | None,
    clashing_jobs: int,
    now: datetime | None = None,
) -> ComponentScore:
    now = now or datetime.now(timezone.utc)
    imminent = scheduled_for is None or scheduled_for <= now + IMMINENT_WINDOW

    if worker.availability_status == AvailabilityStatus.AVAILABLE:
        score = 1.0
        reason = "Marked available"
    elif worker.availability_status == AvailabilityStatus.BUSY:
        if imminent:
            score = 0.45
            reason = "On another job right now"
        else:
            score = 0.9
            reason = "On a job now, but free before the requested slot"
    else:
        score = 0.0
        reason = "Off duty"

    if scheduled_for is not None and worker.availability:
        weekday = scheduled_for.weekday()
        slot = next(
            (a for a in worker.availability if a.day_of_week == weekday), None
        )
        if slot is None or not slot.is_available:
            score *= 0.4
            reason += "; does not normally work that day"
        elif not (slot.start_time <= scheduled_for.time() <= slot.end_time):
            score *= 0.7
            reason += "; requested time is outside usual hours"
        else:
            reason += "; free in the requested window"

    if clashing_jobs:
        score *= 0.35
        reason += f"; {clashing_jobs} job(s) already near that time"

    return ComponentScore(
        "availability", COMPONENT_LABELS["availability"], round(score, 4),
        WEIGHTS["availability"], reason,
    )


def _location_component(distance_km: float) -> ComponentScore:
    score = proximity_score(distance_km)
    return ComponentScore(
        "location", COMPONENT_LABELS["location"], score, WEIGHTS["location"],
        f"{distance_km} km from the job address",
    )


def _rating_component(worker: Worker) -> ComponentScore:
    if worker.rating_count == 0:
        adjusted = RATING_PRIOR
        reason = "No ratings yet; scored at the cooperative average"
    else:
        adjusted = (
            worker.rating_avg * worker.rating_count + RATING_PRIOR * RATING_PRIOR_WEIGHT
        ) / (worker.rating_count + RATING_PRIOR_WEIGHT)
        reason = f"{worker.rating_avg:.1f} stars across {worker.rating_count} ratings"
    return ComponentScore(
        "rating", COMPONENT_LABELS["rating"], round(adjusted / 5.0, 4),
        WEIGHTS["rating"], reason,
    )


def _fairness_component(snapshot: WorkloadSnapshot) -> ComponentScore:
    score = snapshot.fairness_score
    reason = (
        f"{snapshot.workload_pct}% of weekly capacity used "
        f"({snapshot.committed_jobs}/{snapshot.weekly_capacity} jobs)"
    )
    return ComponentScore(
        "fairness", COMPONENT_LABELS["fairness"], score, WEIGHTS["fairness"], reason
    )


def _build_explanation(
    worker_name: str, components: list[ComponentScore], snapshot: WorkloadSnapshot
) -> str:
    ranked = sorted(components, key=lambda c: c.weighted, reverse=True)
    strengths = [c.label.lower() for c in ranked[:3] if c.score >= 0.7]
    weak = [c.label.lower() for c in ranked if c.score < 0.5]

    parts: list[str] = []
    if strengths:
        parts.append("strong " + ", ".join(strengths))
    if snapshot.workload_pct <= 60:
        parts.append(f"and a relatively light workload at {snapshot.workload_pct}%")
    elif snapshot.workload_pct >= 85:
        parts.append(f"despite an already heavy workload at {snapshot.workload_pct}%")

    summary = f"{worker_name} scores well on " + " ".join(parts) if parts else (
        f"{worker_name} is a workable but not outstanding fit"
    )
    if weak:
        summary += f". Weakest area: {weak[0]}"
    return summary + "."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _clash_counts(
    db: Session, worker_ids: list[int], scheduled_for: datetime | None
) -> dict[int, int]:
    if scheduled_for is None or not worker_ids:
        return {}
    low, high = scheduled_for - CLASH_WINDOW, scheduled_for + CLASH_WINDOW
    rows = db.execute(
        select(Booking.worker_id).where(
            Booking.worker_id.in_(worker_ids),
            Booking.status.in_([str(s) for s in ACTIVE_BOOKING_STATUSES]),
            Booking.scheduled_for.between(low, high),
        )
    ).all()
    counts: dict[int, int] = {}
    for (worker_id,) in rows:
        counts[worker_id] = counts.get(worker_id, 0) + 1
    return counts


def find_matches(
    db: Session,
    *,
    service_id: int,
    required_skill_ids: list[int] | None = None,
    lat: float,
    lng: float,
    scheduled_for: datetime | None = None,
    zone_id: int | None = None,
    cooperative_id: int | None = None,
    workers_required: int = 1,
    limit: int = 8,
    exclude_worker_ids: list[int] | None = None,
    emergency: bool = False,
    now: datetime | None = None,
) -> MatchResult:
    """Rank workers for a job, with a full explanation per candidate."""
    now = ensure_utc(now) or datetime.now(timezone.utc)
    # Values loaded from SQLite arrive naive; normalise before comparing.
    scheduled_for = ensure_utc(scheduled_for)
    required_ids = set(required_skill_ids or [])
    excluded_ids = set(exclude_worker_ids or [])

    query = (
        select(Worker)
        .options(
            selectinload(Worker.user),
            selectinload(Worker.zone),
            selectinload(Worker.skills).selectinload(WorkerSkill.skill),
            selectinload(Worker.certifications),
            selectinload(Worker.availability),
        )
    )
    if cooperative_id is not None:
        query = query.where(Worker.cooperative_id == cooperative_id)
    workers = list(db.execute(query).scalars().unique())

    # Certification gate: safety-critical skills need a verified credential.
    cert_required_skills = {
        skill.id: skill.name
        for skill in db.execute(
            select(Skill).where(
                Skill.id.in_(required_ids), Skill.requires_certification.is_(True)
            )
        ).scalars()
    } if required_ids else {}

    service = db.get(ServiceCategory, service_id)
    workload = workload_map(db, [w.id for w in workers], reference=now)
    clashes = _clash_counts(db, [w.id for w in workers], scheduled_for)

    candidates: list[MatchCandidate] = []
    excluded: list[dict[str, str]] = []

    for worker in workers:
        name = worker.user.full_name if worker.user else f"Worker {worker.id}"

        if worker.id in excluded_ids:
            excluded.append({"worker": name, "reason": "Already declined this job"})
            continue
        if worker.verification_status != VerificationStatus.VERIFIED:
            excluded.append({"worker": name, "reason": "Profile not verified"})
            continue
        if worker.availability_status == AvailabilityStatus.OFF_DUTY:
            excluded.append({"worker": name, "reason": "Marked off duty"})
            continue

        held_skill_ids = {link.skill_id for link in worker.skills}
        if required_ids and not (held_skill_ids & required_ids):
            if worker.primary_service_id != service_id:
                excluded.append({"worker": name, "reason": "No matching skill"})
                continue

        if cert_required_skills:
            verified_cert_skill_ids = {
                cert.skill_id
                for cert in worker.certifications
                if cert.verified and cert.skill_id is not None
            }
            missing_certs = [
                label
                for skill_id, label in cert_required_skills.items()
                if skill_id not in verified_cert_skill_ids
            ]
            if missing_certs:
                excluded.append(
                    {
                        "worker": name,
                        "reason": f"No verified certification for {', '.join(missing_certs)}",
                    }
                )
                continue

        snapshot = workload[worker.id]
        if snapshot.committed_jobs > snapshot.weekly_capacity * OVERLOAD_CUTOFF:
            excluded.append(
                {
                    "worker": name,
                    "reason": f"Overloaded at {snapshot.workload_pct}% of weekly capacity",
                }
            )
            continue

        distance = travel_distance_km(worker.base_lat, worker.base_lng, lat, lng)
        skill_component, matched_names, missing_names = _skill_component(
            worker, required_ids, service_id
        )
        components = [
            skill_component,
            _availability_component(
                worker, scheduled_for, clashes.get(worker.id, 0), now
            ),
            _location_component(distance),
            _rating_component(worker),
            _fairness_component(snapshot),
        ]

        final = sum(component.weighted for component in components)

        warnings: list[str] = []
        if emergency and distance > 8:
            warnings.append("Further than ideal for an emergency call-out")
        if snapshot.workload_pct >= 85:
            warnings.append("Close to weekly capacity")

        missing_names = sorted(
            {
                skill_name
                for skill_id, skill_name in _skill_names(db, required_ids).items()
                if skill_id not in held_skill_ids
            }
        )

        candidates.append(
            MatchCandidate(
                worker_id=worker.id,
                worker_name=name,
                headline=worker.headline or (service.name if service else ""),
                zone_name=worker.zone.name if worker.zone else "",
                rating_avg=round(worker.rating_avg, 2),
                rating_count=worker.rating_count,
                jobs_completed=worker.jobs_completed,
                distance_km=distance,
                eta_minutes=eta_minutes(distance),
                availability_status=worker.availability_status,
                verification_status=worker.verification_status,
                workload_pct=snapshot.workload_pct,
                matched_skills=matched_names,
                missing_skills=missing_names,
                certifications=[c.name for c in worker.certifications if c.verified],
                components=components,
                final_score=round(final, 4),
                explanation=_build_explanation(name, components, snapshot),
                warnings=warnings,
            )
        )

    # Emergency calls trade some fairness for speed: still scored the same way,
    # but ties are broken by who can physically get there first.
    if emergency:
        candidates.sort(key=lambda c: (-c.final_score, c.distance_km))
    else:
        candidates.sort(key=lambda c: (-c.final_score, c.workload_pct, c.distance_km))

    for index, candidate in enumerate(candidates):
        candidate.recommended = index < max(1, workers_required)

    return MatchResult(
        candidates=candidates[:limit],
        considered=len(workers),
        excluded=excluded[:12],
        weights=WEIGHTS,
        workers_required=workers_required,
    )


def _skill_names(db: Session, skill_ids: set[int]) -> dict[int, str]:
    if not skill_ids:
        return {}
    return {
        skill.id: skill.name
        for skill in db.execute(select(Skill).where(Skill.id.in_(skill_ids))).scalars()
    }


def simulate_fair_distribution(
    workloads: list[tuple[str, int]],
    rolloff: float = 0.45,
    fairness_pull: float = 1.0,
) -> list[dict[str, Any]]:
    """Project one rolling week forward under workload-aware allocation.

    SIMULATION, NOT MEASURED HISTORY. Every surface that shows this labels it
    as a projection.

    The model is deliberately simple and stated in full:

    1. Over the next seven days a fraction (``rolloff``) of each worker's
       current commitments completes and leaves the rolling window.
    2. The same volume of new work arrives.
    3. That new work is shared out in proportion to each worker's remaining
       headroom, which is what the fairness component of the allocator does.

    Total load is therefore conserved; only its distribution changes. Because
    fairness is one input among five rather than the only one, the spread
    narrows without flattening completely.
    """
    if not workloads:
        return []

    current = [(name, max(0, min(100, pct))) for name, pct in workloads]
    retained = [(name, pct * (1 - rolloff)) for name, pct in current]
    incoming_total = sum(pct for _, pct in current) * rolloff

    headroom = [max(1.0, (100 - pct) ** fairness_pull) for _, pct in retained]
    headroom_total = sum(headroom)

    projected = [
        (name, pct + incoming_total * (room / headroom_total))
        for (name, pct), room in zip(retained, headroom, strict=True)
    ]

    return [
        {
            "worker": name,
            "before": before,
            "after": max(0, min(100, round(after))),
        }
        for (name, before), (_, after) in zip(current, projected, strict=True)
    ]
