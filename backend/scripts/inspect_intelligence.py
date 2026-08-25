"""Developer utility: print what the AI engines derive from the seeded data.

Run with:  python -m scripts.inspect_intelligence
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models import Cooperative, ServiceCategory, Skill, User
from app.services.analytics import dashboard_summary, worker_utilisation
from app.services.forecasting import forecast_services
from app.services.matching import find_matches, simulate_fair_distribution
from app.services.workforce import detect_skill_gaps, plan_workforce
from app.services.workload import workload_map


def main() -> None:
    with SessionLocal() as db:
        coop = db.query(Cooperative).first()
        assert coop is not None, "Database is not seeded."

        print("\n=== DASHBOARD KPIs " + "=" * 52)
        summary = dashboard_summary(db, coop.id)
        for key in (
            "workers", "available_workers", "active_jobs", "unassigned_jobs",
            "completed_today", "worker_utilisation_pct", "fairness_score",
            "average_rating", "rating_count", "completion_rate_pct",
        ):
            print(f"  {key:26s} {summary[key]}")
        print(f"  {'revenue.total':26s} {summary['revenue']['total']:,.0f}")
        print(f"  {'revenue.welfare_fund':26s} {summary['revenue']['welfare_fund']:,.0f}")

        print("\n=== DEMAND FORECAST (next 7 days) " + "=" * 37)
        print(f"  {'service':18s} {'pred':>5s} {'lastwk':>7s} {'base':>7s} {'vs base':>8s} {'conf':>5s}  top zone")
        for f in forecast_services(db, coop.id):
            print(
                f"  {f.service_name:18s} {f.predicted_demand:5d} {f.last_week_demand:7d} "
                f"{f.baseline_demand:7.1f} {f.change_pct:+7.1f}% {f.confidence:5.2f}  {f.top_zone}"
            )

        print("\n=== WORKFORCE PLAN " + "=" * 52)
        plans, headline = plan_workforce(db, coop.id)
        print(f"  {'service':18s} {'demand':>7s} {'req':>4s} {'avail':>6s} {'gap':>5s}  status")
        for p in plans:
            print(
                f"  {p.service_name:18s} {p.predicted_demand:7d} {p.required_workers:4d} "
                f"{p.available_workers:6d} {p.gap:+5d}  {p.to_dict()['status']}"
            )
        print("\n  HEADLINE:", headline["headline"])
        print("  SUPPORT :", headline.get("supporting"))
        print("  ACTION  :", headline["recommendation"])
        if headline.get("reallocation"):
            print("  REALLOC :", headline["reallocation"])

        print("\n=== SKILL GAPS (top 6) " + "=" * 48)
        for gap in detect_skill_gaps(db, coop.id, limit=6):
            print(
                f"  {gap.skill_name:26s} recent={gap.recent_jobs:3d} proj={gap.projected_jobs:3d} "
                f"req={gap.required_workers:2d} avail={gap.available_workers:2d} "
                f"cert={gap.certified_workers:2d} gap={gap.gap}"
            )
            print(f"      -> {gap.recommendation}")

        print("\n=== WORKER UTILISATION " + "=" * 48)
        rows = worker_utilisation(db, coop.id)
        for row in rows:
            bar = "#" * (row["workload_pct"] // 4)
            print(
                f"  {row['worker']:20s} {row['workload_pct']:3d}%  "
                f"{row['committed_jobs']:2d}/{row['weekly_capacity']:2d} {bar}"
            )

        print("\n=== FAIR DISTRIBUTION PROJECTION (simulated) " + "=" * 26)
        top = rows[:2] + rows[-2:]
        for entry in simulate_fair_distribution(
            [(r["worker"], r["workload_pct"]) for r in top]
        ):
            print(f"  {entry['worker']:20s} {entry['before']:3d}% -> {entry['after']:3d}%")

        print("\n=== MATCHING: kitchen sink leak, tomorrow morning " + "=" * 21)
        customer = db.query(User).filter(User.email == "customer@demo.com").one()
        plumbing = db.query(ServiceCategory).filter(ServiceCategory.slug == "plumbing").one()
        skill_ids = [
            db.query(Skill).filter(Skill.slug == slug).one().id
            for slug in ("plumbing", "pipe-repair")
        ]
        now = datetime.now(timezone.utc)
        result = find_matches(
            db,
            service_id=plumbing.id,
            required_skill_ids=skill_ids,
            lat=customer.lat,
            lng=customer.lng,
            scheduled_for=(now.replace(hour=10, minute=0, second=0, microsecond=0)
                           + __import__("datetime").timedelta(days=1)),
            cooperative_id=coop.id,
            workers_required=1,
        )
        print(f"  considered {result.considered} workers, {len(result.excluded)} excluded")
        for candidate in result.candidates:
            flag = " <== RECOMMENDED" if candidate.recommended else ""
            print(
                f"  {candidate.worker_name:20s} score={candidate.score_percent:3d}%  "
                f"{candidate.distance_km:4.1f}km  rating {candidate.rating_avg:.1f}  "
                f"load {candidate.workload_pct:3d}%{flag}"
            )
        if result.candidates:
            best = result.candidates[0]
            print(f"\n  WHY {best.worker_name.upper()}?")
            for component in best.components:
                print(
                    f"    {component.label:14s} {round(component.score * 100):3d}%  "
                    f"(weight {round(component.weight * 100)}%)  {component.reason}"
                )
            print(f"    {'FINAL':14s} {best.score_percent:3d}%")
            print(f"    {best.explanation}")
        for entry in result.excluded[:5]:
            print(f"    excluded: {entry['worker']} - {entry['reason']}")
        print()


if __name__ == "__main__":
    main()
