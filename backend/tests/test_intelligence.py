"""AI understanding, matching, forecasting, workforce planning and welfare."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_understand_extracts_a_structured_requirement(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/ai/understand-request",
        headers=customer_headers,
        json={"text": "My kitchen sink is leaking and I need a plumber tomorrow morning."},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    understanding = body["understanding"]
    assert understanding["service_name"] == "Plumbing"
    assert understanding["problem"] == "Kitchen Sink Leakage"
    assert "Pipe Repair" in understanding["skill_names"]
    assert understanding["workers_required"] == 1
    assert understanding["urgency"] == "NORMAL"
    assert "Tomorrow" in understanding["preferred_time_label"]
    assert understanding["scheduled_for"] is not None

    # The engine says which path produced the answer rather than implying an LLM.
    assert body["engine"]["method"] == "rule_based"
    assert body["engine"]["llm_configured"] is False
    assert body["service"]["slug"] == "plumbing"
    assert body["estimated_price"] == 650.0


def test_understand_flags_an_emergency(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    body = client.post(
        "/api/ai/understand-request",
        headers=customer_headers,
        json={"text": "Water pipe burst in the bathroom, we need help immediately!"},
    ).json()
    understanding = body["understanding"]
    assert understanding["service_name"] == "Plumbing"
    assert understanding["problem"] == "Water Pipe Burst"
    assert understanding["urgency"] == "EMERGENCY"


def test_understand_admits_when_it_does_not_know(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    body = client.post(
        "/api/ai/understand-request",
        headers=customer_headers,
        json={"text": "qwerty zxcvb asdfg"},
    ).json()
    understanding = body["understanding"]
    assert understanding["confidence"] < 0.5
    assert "No service keywords were recognised" in understanding["notes"]


def test_understand_rejects_empty_input(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/ai/understand-request", headers=customer_headers, json={"text": "  "}
    )
    assert response.status_code == 422


def test_matching_prefers_fairness_over_pure_proximity(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    services = client.get("/api/services").json()
    plumbing = next(s for s in services if s["slug"] == "plumbing")
    skill_ids = [s["id"] for s in plumbing["skills"] if s["slug"] in ("plumbing", "pipe-repair")]

    response = client.post(
        "/api/matching",
        headers=customer_headers,
        json={"service_id": plumbing["id"], "skill_ids": skill_ids, "workers_required": 1},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["method"] == "weighted_explainable_scoring"
    assert body["weights"]["fairness"]["percent"] == 20
    assert body["weights"]["skill"]["percent"] == 30
    candidates = body["candidates"]
    assert candidates, "expected at least one eligible plumber"

    top = candidates[0]
    assert top["recommended"] is True
    assert {c["key"] for c in top["components"]} == {
        "skill", "availability", "location", "rating", "fairness"
    }
    # Every component carries a human-readable justification.
    assert all(component["reason"] for component in top["components"])
    assert top["explanation"]

    # The winner is not simply the nearest worker: someone closer scores lower
    # because they are carrying more work.
    nearest = min(candidates, key=lambda c: c["distance_km"])
    if nearest["worker_id"] != top["worker_id"]:
        assert nearest["workload_pct"] > top["workload_pct"]

    # The weighted components add up to the final score.
    total = sum(c["score"] * c["weight"] for c in top["components"])
    assert abs(total - top["final_score"]) < 0.01


def test_matching_excludes_uncertified_workers_for_certified_skills(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    services = client.get("/api/services").json()
    electrical = next(s for s in services if s["slug"] == "electrical")
    solar = next(s for s in electrical["skills"] if s["slug"] == "solar-installation")

    body = client.post(
        "/api/matching",
        headers=admin_headers,
        json={"service_id": electrical["id"], "skill_ids": [solar["id"]], "limit": 25},
    ).json()

    for candidate in body["candidates"]:
        assert candidate["certifications"], candidate["worker_name"]
    reasons = " ".join(entry["reason"] for entry in body["excluded"])
    assert "certification" in reasons.lower()


def test_matching_requires_a_service_or_booking(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    response = client.post("/api/matching", headers=customer_headers, json={"limit": 5})
    assert response.status_code == 422


def test_forecast_is_transparent_about_its_method(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    body = client.get("/api/forecast", headers=admin_headers).json()
    assert body["method"] == "weighted_moving_average_with_damped_trend"
    assert body["horizon_days"] == 7

    services = body["services"]
    assert len(services) == 7
    for entry in services:
        assert entry["predicted_demand"] >= 0
        assert 0 <= entry["confidence"] <= 1
        assert entry["change_basis"] == "four_week_weighted_average"

    insight = body["insight"]
    assert insight["kind"] in {"shortage", "balanced"}
    assert insight["recommendation"]


def test_workforce_plan_identifies_a_real_shortage(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    body = client.get("/api/workforce", headers=admin_headers).json()

    plans = {plan["service_slug"]: plan for plan in body["plans"]}
    assert len(plans) == 7
    for plan in plans.values():
        assert plan["gap"] == plan["available_workers"] - plan["required_workers"]

    # The seeded cooperative is genuinely short of electricians.
    assert plans["electrical"]["status"] == "shortage"
    assert plans["plumbing"]["status"] == "surplus"
    assert body["insight"]["service"] == "Electrical"

    # The workload projection must declare itself a simulation.
    projection = body["fair_distribution_projection"]
    assert projection["is_simulation"] is True
    assert projection["rows"]
    # Load is redistributed, not invented: the total is preserved.
    before = sum(row["before"] for row in projection["rows"])
    after = sum(row["after"] for row in projection["rows"])
    assert abs(before - after) <= len(projection["rows"])


def test_skill_gap_analysis_flags_solar_installation(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    body = client.get("/api/workforce", headers=admin_headers).json()
    gaps = {gap["skill_slug"]: gap for gap in body["skill_gaps"]}

    solar = gaps["solar-installation"]
    assert solar["is_emerging"] is True
    assert solar["requires_certification"] is True
    assert solar["is_specialist"] is True
    assert solar["gap"] > 0
    assert solar["required_workers"] > solar["certified_workers"]
    assert "Solar Installation" in solar["recommendation"]

    assert body["most_demanded_skills"]


def test_welfare_reports_fund_and_coverage(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    body = client.get("/api/welfare", headers=admin_headers).json()
    assert body["fund_total"] > 0
    assert body["workers_total"] == 26
    assert 0 <= body["coverage_pct"] <= 100

    kumar = next(row for row in body["workers"] if row["worker"] == "Kumar Selvan")
    assert kumar["jobs_completed"] > 0
    assert kumar["earnings"] > 0
    assert kumar["welfare_contribution"] > 0
    assert kumar["insurance_active"] is True
    assert kumar["certification_count"] >= 1


def test_worker_only_sees_their_own_welfare_row(
    client: TestClient, worker_headers: dict[str, str]
) -> None:
    body = client.get("/api/welfare", headers=worker_headers).json()
    assert len(body["workers"]) == 1
    assert body["workers"][0]["worker"] == "Kumar Selvan"


def test_dashboard_kpis_are_internally_consistent(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    body = client.get("/api/dashboard", headers=admin_headers).json()
    summary = body["summary"]

    assert summary["workers"] == 26
    assert summary["available_workers"] <= summary["workers"]
    assert 0 <= summary["worker_utilisation_pct"] <= 100
    assert 0 <= summary["fairness_score"] <= 100
    assert 0 < summary["average_rating"] <= 5
    assert summary["completed_bookings"] <= summary["total_bookings"]

    revenue = summary["revenue"]
    parts = (
        revenue["worker_earnings"]
        + revenue["cooperative_fund"]
        + revenue["welfare_fund"]
        + revenue["technology_fund"]
    )
    assert abs(parts - revenue["total"]) < 1.0
    assert body["insight"]["recommendation"]
    assert body["cooperative"]["name"]


def test_analytics_bundle_has_every_chart_series(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    body = client.get("/api/analytics?days=30", headers=admin_headers).json()
    for key in (
        "jobs_by_service", "jobs_by_zone", "worker_utilisation", "earnings",
        "rating_distribution", "rating_trend", "demand_trend", "completion_funnel",
    ):
        assert body[key], f"{key} series is empty"
    assert len(body["demand_trend"]) == 30
    assert sum(row["count"] for row in body["rating_distribution"]) > 0


def test_completed_today_uses_the_cooperative_day_not_utc(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """The cooperative closes its books at local midnight.

    Measuring "today" in UTC made this figure read zero every morning in India,
    because the local day starts 5.5 hours before the UTC one.
    """
    from datetime import datetime, timedelta, timezone

    from app.core.timeutils import local_day_start, local_today

    now = datetime.now(timezone.utc)
    start = local_day_start(now)

    assert start <= now
    assert now - start < timedelta(days=1)
    assert local_today(now) == start.astimezone(
        __import__("zoneinfo").ZoneInfo("Asia/Kolkata")
    ).date()

    summary = client.get("/api/dashboard", headers=admin_headers).json()["summary"]
    # The seed places finished work inside the cooperative's own day, so this
    # is non-zero no matter what hour the demo is run at.
    assert summary["completed_today"] > 0
