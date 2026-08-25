"""AI #3 - Demand forecasting.

Method: a weighted moving average over weekly history, adjusted by a damped
recent trend. That is the whole model, and the API says so in the ``method``
field of every response. There is no neural network here and the product does
not pretend otherwise - with a few weeks of cooperative history a transparent
baseline is both more accurate and more defensible than a deep model.

Confidence is reported honestly: it falls when there is little history or when
demand has been volatile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from math import sqrt
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutils import local_today
from app.models import DemandRecord, ServiceCategory, Zone

HISTORY_DAYS = 56
HORIZON_DAYS = 7

#: Most recent week first. Recent weeks dominate but older weeks still count.
WEEK_WEIGHTS = (0.40, 0.30, 0.20, 0.10)

#: Trend is damped: a 30% week-on-week jump does not become a 30% forecast jump.
TREND_DAMPING = 0.5
MAX_TREND = 0.6

METHOD = "weighted_moving_average_with_damped_trend"


@dataclass
class ServiceForecast:
    service_id: int
    service_name: str
    service_slug: str
    predicted_demand: int
    last_week_demand: int
    baseline_demand: float
    change_pct: float           # vs the 4-week weighted baseline
    change_vs_last_week_pct: float
    confidence: float
    weeks_of_history: int
    history: list[dict[str, Any]] = field(default_factory=list)
    top_zone: str | None = None
    top_zone_id: int | None = None
    method: str = METHOD

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_slug": self.service_slug,
            "predicted_demand": self.predicted_demand,
            "last_week_demand": self.last_week_demand,
            "baseline_demand": round(self.baseline_demand, 2),
            "change_pct": round(self.change_pct, 1),
            "change_basis": "four_week_weighted_average",
            "change_vs_last_week_pct": round(self.change_vs_last_week_pct, 1),
            "confidence": round(self.confidence, 2),
            "weeks_of_history": self.weeks_of_history,
            "history": self.history,
            "top_zone": self.top_zone,
            "top_zone_id": self.top_zone_id,
            "method": self.method,
        }


def _weekly_buckets(
    daily: dict[date, int], today: date, weeks: int
) -> list[int]:
    """Totals per trailing week, most recent first."""
    buckets: list[int] = []
    for index in range(weeks):
        end = today - timedelta(days=7 * index)
        start = end - timedelta(days=6)
        buckets.append(
            sum(count for day, count in daily.items() if start <= day <= end)
        )
    return buckets


def _confidence(weekly: list[int], weeks_with_data: int) -> float:
    """Low history or high volatility means low confidence, and we say so."""
    populated = [value for value in weekly if value > 0]
    if len(populated) < 2:
        return 0.35
    mean = sum(populated) / len(populated)
    if mean == 0:
        return 0.35
    variance = sum((value - mean) ** 2 for value in populated) / len(populated)
    coefficient_of_variation = sqrt(variance) / mean
    stability = max(0.0, 1.0 - min(1.0, coefficient_of_variation))
    coverage = min(1.0, weeks_with_data / len(WEEK_WEIGHTS))
    return round(min(0.95, 0.35 + 0.4 * stability + 0.25 * coverage), 2)


def forecast_services(
    db: Session,
    cooperative_id: int,
    zone_id: int | None = None,
    today: date | None = None,
) -> list[ServiceForecast]:
    """Forecast next-7-day job volume per service."""
    today = today or local_today()
    window_start = today - timedelta(days=HISTORY_DAYS)

    query = (
        select(
            DemandRecord.service_id,
            DemandRecord.record_date,
            func.sum(DemandRecord.bookings_count),
        )
        .where(
            DemandRecord.cooperative_id == cooperative_id,
            DemandRecord.record_date >= window_start,
            DemandRecord.record_date <= today,
        )
        .group_by(DemandRecord.service_id, DemandRecord.record_date)
    )
    if zone_id is not None:
        query = query.where(DemandRecord.zone_id == zone_id)

    per_service: dict[int, dict[date, int]] = {}
    for service_id, record_date, total in db.execute(query):
        per_service.setdefault(service_id, {})[record_date] = int(total or 0)

    services = {
        service.id: service
        for service in db.execute(select(ServiceCategory)).scalars()
    }
    zone_names = {zone.id: zone.name for zone in db.execute(select(Zone)).scalars()}

    forecasts: list[ServiceForecast] = []
    for service_id, service in services.items():
        daily = per_service.get(service_id, {})
        weekly = _weekly_buckets(daily, today, len(WEEK_WEIGHTS))
        weeks_with_data = sum(1 for value in weekly if value > 0)

        weighted = sum(
            value * weight for value, weight in zip(weekly, WEEK_WEIGHTS, strict=True)
        )
        weight_total = sum(
            weight
            for value, weight in zip(weekly, WEEK_WEIGHTS, strict=True)
            if value > 0
        ) or 1.0
        baseline = weighted / weight_total if weeks_with_data else 0.0

        recent = weekly[0] + weekly[1]
        earlier = weekly[2] + weekly[3]
        if earlier > 0:
            raw_trend = (recent - earlier) / earlier
        else:
            raw_trend = 0.0
        trend = max(-MAX_TREND, min(MAX_TREND, raw_trend)) * TREND_DAMPING

        predicted = max(0, round(baseline * (1 + trend)))
        last_week = weekly[0]
        # Headline change is measured against the four-week weighted baseline,
        # which is the number the model actually reasons about. Change against
        # last week alone is reported separately so neither is misread.
        change_pct = ((predicted - baseline) / baseline * 100) if baseline else 0.0
        change_vs_last_week = (
            ((predicted - last_week) / last_week * 100) if last_week else 0.0
        )

        top_zone_id = None
        if zone_id is None:
            zone_query = (
                select(DemandRecord.zone_id, func.sum(DemandRecord.bookings_count))
                .where(
                    DemandRecord.cooperative_id == cooperative_id,
                    DemandRecord.service_id == service_id,
                    DemandRecord.record_date >= today - timedelta(days=21),
                )
                .group_by(DemandRecord.zone_id)
                .order_by(func.sum(DemandRecord.bookings_count).desc())
                .limit(1)
            )
            row = db.execute(zone_query).first()
            top_zone_id = row[0] if row else None

        history = [
            {
                "label": f"Week -{index}" if index else "This week",
                "jobs": value,
            }
            for index, value in enumerate(weekly)
        ][::-1]

        forecasts.append(
            ServiceForecast(
                service_id=service_id,
                service_name=service.name,
                service_slug=service.slug,
                predicted_demand=predicted,
                last_week_demand=last_week,
                baseline_demand=baseline,
                change_pct=change_pct,
                change_vs_last_week_pct=change_vs_last_week,
                confidence=_confidence(weekly, weeks_with_data),
                weeks_of_history=weeks_with_data,
                history=history,
                top_zone=zone_names.get(top_zone_id) if top_zone_id else None,
                top_zone_id=top_zone_id,
            )
        )

    forecasts.sort(key=lambda item: item.predicted_demand, reverse=True)
    return forecasts


def demand_trend_series(
    db: Session, cooperative_id: int, days: int = 30, today: date | None = None
) -> list[dict[str, Any]]:
    """Total daily job volume, for the trend chart."""
    today = today or local_today()
    start = today - timedelta(days=days - 1)
    rows = db.execute(
        select(DemandRecord.record_date, func.sum(DemandRecord.bookings_count))
        .where(
            DemandRecord.cooperative_id == cooperative_id,
            DemandRecord.record_date >= start,
            DemandRecord.record_date <= today,
        )
        .group_by(DemandRecord.record_date)
        .order_by(DemandRecord.record_date)
    ).all()
    by_day = {row[0]: int(row[1] or 0) for row in rows}
    return [
        {
            "date": (start + timedelta(days=offset)).isoformat(),
            "jobs": by_day.get(start + timedelta(days=offset), 0),
        }
        for offset in range(days)
    ]
