"""Worker welfare ledger and cooperative welfare fund reporting."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Certification, WelfareRecord, Worker


def welfare_overview(db: Session, cooperative_id: int) -> dict[str, Any]:
    """Per-worker welfare position plus cooperative fund totals."""
    workers = list(
        db.execute(
            select(Worker)
            .where(Worker.cooperative_id == cooperative_id)
            .options(
                selectinload(Worker.user),
                selectinload(Worker.certifications),
                selectinload(Worker.primary_service),
                selectinload(Worker.zone),
            )
        ).scalars()
    )

    contribution_rows = db.execute(
        select(WelfareRecord.worker_id, func.sum(WelfareRecord.amount))
        .where(
            WelfareRecord.cooperative_id == cooperative_id,
            WelfareRecord.kind == "CONTRIBUTION",
        )
        .group_by(WelfareRecord.worker_id)
    ).all()
    contributions = {row[0]: float(row[1] or 0) for row in contribution_rows}

    credit_rows = db.execute(
        select(WelfareRecord.worker_id, func.sum(WelfareRecord.credits))
        .where(
            WelfareRecord.cooperative_id == cooperative_id,
            WelfareRecord.kind == "TRAINING_CREDIT",
        )
        .group_by(WelfareRecord.worker_id)
    ).all()
    earned_credits = {row[0]: int(row[1] or 0) for row in credit_rows}

    rows: list[dict[str, Any]] = []
    for worker in workers:
        rows.append(
            {
                "worker_id": worker.id,
                "worker": worker.user.full_name if worker.user else f"Worker {worker.id}",
                "service": worker.primary_service.name if worker.primary_service else "",
                "zone": worker.zone.name if worker.zone else "",
                "jobs_completed": worker.jobs_completed,
                "earnings": round(worker.total_earnings, 2),
                "welfare_contribution": round(contributions.get(worker.id, 0.0), 2),
                "insurance_active": worker.insurance_active,
                "training_credits": worker.training_credits,
                "training_credits_earned": earned_credits.get(worker.id, 0),
                "certifications": [
                    {"name": cert.name, "verified": cert.verified}
                    for cert in worker.certifications
                ],
                "certification_count": sum(1 for c in worker.certifications if c.verified),
                "rating_avg": round(worker.rating_avg, 2),
            }
        )
    rows.sort(key=lambda row: row["welfare_contribution"], reverse=True)

    fund_total = sum(row["welfare_contribution"] for row in rows)
    insured = sum(1 for row in rows if row["insurance_active"])

    return {
        "fund_total": round(fund_total, 2),
        "workers_covered": insured,
        "workers_total": len(rows),
        "coverage_pct": round(100 * insured / len(rows)) if rows else 0,
        "training_credits_outstanding": sum(row["training_credits"] for row in rows),
        "certified_workers": sum(1 for row in rows if row["certification_count"] > 0),
        "workers": rows,
    }


def worker_welfare(db: Session, worker_id: int) -> dict[str, Any]:
    """Ledger for a single worker, newest entry first."""
    records = list(
        db.execute(
            select(WelfareRecord)
            .where(WelfareRecord.worker_id == worker_id)
            .order_by(WelfareRecord.created_at.desc())
            .limit(50)
        ).scalars()
    )
    total = db.execute(
        select(func.sum(WelfareRecord.amount)).where(
            WelfareRecord.worker_id == worker_id, WelfareRecord.kind == "CONTRIBUTION"
        )
    ).scalar()
    worker = db.get(Worker, worker_id)
    return {
        "worker_id": worker_id,
        "total_contribution": round(float(total or 0), 2),
        "insurance_active": bool(worker.insurance_active) if worker else False,
        "training_credits": worker.training_credits if worker else 0,
        "entries": [
            {
                "id": record.id,
                "kind": record.kind,
                "amount": round(record.amount, 2),
                "credits": record.credits,
                "note": record.note,
                "booking_id": record.booking_id,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ],
    }
