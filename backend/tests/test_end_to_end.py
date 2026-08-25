"""The full SIH demo journey, driven through the public API.

Customer request -> AI understanding -> matching -> fair allocation ->
worker accepts -> starts -> completes -> customer pays -> customer rates ->
dashboard updates.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _scenario_booking(client: TestClient, customer_headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/bookings",
        headers=customer_headers,
        json={
            "raw_request": "My kitchen sink is leaking. I need a plumber tomorrow morning.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_service_journey(
    client: TestClient,
    customer_headers: dict[str, str],
    worker_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    # Run against the deterministic demo state: this is precisely what a judge
    # gets after pressing Reset Demo, so the scripted outcome is guaranteed.
    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200, reset.text
    assert reset.json()["counts"]["workers"] == 26
    client.post("/api/demo/scenario/start")
    before = client.get("/api/dashboard", headers=admin_headers).json()["summary"]

    # 1. Customer describes the problem; the AI structures it.
    booking = _scenario_booking(client, customer_headers)
    booking_id = booking["id"]
    assert booking["status"] == "REQUESTED"
    assert booking["service_name"] == "Plumbing"
    assert booking["problem_summary"] == "Kitchen Sink Leakage"
    assert booking["ai_interpretation"]["method"] == "rule_based"
    assert set(booking["required_skills"]) == {"Plumbing", "Pipe Repair"}
    assert booking["estimated_price"] == 650.0
    assert booking["payment_split_preview"] == {
        "amount": 650.0,
        "worker_amount": 560.0,
        "cooperative_amount": 40.0,
        "welfare_amount": 20.0,
        "technology_amount": 30.0,
    }

    # 2. Eligible workers, ranked with an explanation.
    matches = client.post(
        "/api/matching", headers=customer_headers, json={"booking_id": booking_id}
    ).json()
    assert matches["candidates"]
    recommended = matches["recommended"]
    assert recommended["recommended"] is True
    assert recommended["worker_name"] == "Kumar Selvan"
    assert recommended["score_percent"] >= 80

    # Fairness, not proximity or rating, is what puts him first: the nearest
    # plumber and the best-rated plumber both carry more work.
    nearest = min(matches["candidates"], key=lambda c: c["distance_km"])
    best_rated = max(matches["candidates"], key=lambda c: c["rating_avg"])
    assert nearest["worker_id"] != recommended["worker_id"]
    assert nearest["workload_pct"] > recommended["workload_pct"]
    assert best_rated["workload_pct"] > recommended["workload_pct"]

    # 3. Fair allocation: the pick is justified, and stored on the booking.
    assigned = client.post(
        "/api/matching/assign",
        headers=customer_headers,
        json={"booking_id": booking_id, "worker_id": recommended["worker_id"]},
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["booking"]["status"] == "ASSIGNED"
    assert body["booking"]["worker"]["name"] == "Kumar Selvan"
    assert body["allocation"]["components"]
    assert body["booking"]["match_breakdown"]["final_score"] > 0

    # The worker is notified.
    notifications = client.get("/api/notifications", headers=worker_headers).json()
    assert any(n["booking_id"] == booking_id for n in notifications)

    # 4. Worker accepts.
    accepted = client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=worker_headers,
        json={"status": "ACCEPTED"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"
    assert accepted.json()["accepted_at"] is not None

    # 5. Worker starts.
    started = client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=worker_headers,
        json={"status": "IN_PROGRESS"},
    ).json()
    assert started["status"] == "IN_PROGRESS"
    assert started["distance_km"] is not None
    timeline = {step["status"]: step["state"] for step in started["timeline"]}
    assert timeline["ASSIGNED"] == "done"
    assert timeline["IN_PROGRESS"] == "current"
    assert timeline["PAID"] == "pending"

    # The worker's availability follows the job.
    profile = client.get("/api/workers/me", headers=worker_headers).json()
    assert profile["availability_status"] == "BUSY"

    # 6. Worker completes.
    completed = client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=worker_headers,
        json={"status": "COMPLETED"},
    ).json()
    assert completed["status"] == "COMPLETED"
    assert completed["final_price"] == 650.0
    assert (
        client.get("/api/workers/me", headers=worker_headers).json()["availability_status"]
        == "AVAILABLE"
    )

    # 7. Customer pays. The split adds back to exactly what was charged.
    payment = client.post(
        "/api/payments", headers=customer_headers, json={"booking_id": booking_id}
    )
    assert payment.status_code == 201, payment.text
    paid = payment.json()
    assert paid["simulated"] is True
    assert paid["payment"]["invoice_number"].startswith("SAH-")
    assert paid["payment"]["worker_amount"] == 560.0
    assert paid["payment"]["cooperative_amount"] == 40.0
    assert paid["payment"]["welfare_amount"] == 20.0
    assert paid["payment"]["technology_amount"] == 30.0
    assert sum(part["amount"] for part in paid["split"]) == paid["payment"]["amount"]
    assert paid["booking"]["status"] == "PAID"

    invoice = client.get(
        f"/api/payments/{booking_id}/invoice", headers=customer_headers
    ).json()
    assert invoice["invoice_number"] == paid["payment"]["invoice_number"]
    assert invoice["simulated"] is True
    assert invoice["total"] == 650.0

    # 8. Customer rates; the worker's average moves.
    worker_before = client.get(
        f"/api/workers/{recommended['worker_id']}", headers=customer_headers
    ).json()
    rated = client.post(
        "/api/ratings",
        headers=customer_headers,
        json={"booking_id": booking_id, "stars": 5, "comment": "Fixed it in one visit."},
    )
    assert rated.status_code == 201, rated.text
    result = rated.json()
    assert result["booking"]["status"] == "RATED"
    assert result["worker"]["rating_count"] == worker_before["rating_count"] + 1
    assert "Worker performance updated" in result["effects"]

    # 9. The cooperative dashboard has moved.
    after = client.get("/api/dashboard", headers=admin_headers).json()["summary"]
    assert after["total_bookings"] == before["total_bookings"] + 1
    assert after["rating_count"] == before["rating_count"] + 1
    assert after["revenue"]["total"] == before["revenue"]["total"] + 650.0
    assert after["revenue"]["welfare_fund"] == before["revenue"]["welfare_fund"] + 20.0

    # 10. The forecast still produces an actionable workforce recommendation.
    forecast = client.get("/api/forecast", headers=admin_headers).json()
    assert forecast["insight"]["recommendation"]


def test_worker_can_decline_and_the_job_is_reallocated(
    client: TestClient, customer_headers: dict[str, str], worker_headers: dict[str, str]
) -> None:
    booking = _scenario_booking(client, customer_headers)
    booking_id = booking["id"]

    matches = client.post(
        "/api/matching", headers=customer_headers, json={"booking_id": booking_id}
    ).json()
    # Assign the demo worker explicitly so the decline is made by the account
    # whose token this test holds.
    kumar = next(
        c for c in matches["candidates"] if c["worker_name"] == "Kumar Selvan"
    )
    first = kumar["worker_id"]
    client.post(
        "/api/matching/assign",
        headers=customer_headers,
        json={"booking_id": booking_id, "worker_id": first},
    )

    declined = client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=worker_headers,
        json={"status": "DECLINED"},
    )
    assert declined.status_code == 200, declined.text
    body = declined.json()
    assert body["status"] == "DECLINED"
    assert body["worker"] is None
    assert first in body["declined_worker_ids"]

    # The declining worker is no longer offered, but someone else is.
    rematched = client.post(
        "/api/matching", headers=customer_headers, json={"booking_id": booking_id}
    ).json()
    assert first not in [c["worker_id"] for c in rematched["candidates"]]
    assert rematched["candidates"], "job should still be allocatable"

    second = rematched["recommended"]["worker_id"]
    reassigned = client.post(
        "/api/matching/assign",
        headers=customer_headers,
        json={"booking_id": booking_id, "worker_id": second},
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["booking"]["status"] == "ASSIGNED"

    client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=customer_headers,
        json={"status": "CANCELLED"},
    )


def test_emergency_request_is_prioritised(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/bookings",
        headers=customer_headers,
        json={
            "raw_request": "Water pipe burst in the kitchen, water everywhere!",
            "is_emergency": True,
        },
    )
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["urgency"] == "EMERGENCY"
    assert booking["is_emergency"] is True
    # Emergency call-outs carry the urgency multiplier.
    assert booking["estimated_price"] > 650.0

    matches = client.post(
        "/api/matching", headers=customer_headers, json={"booking_id": booking["id"]}
    ).json()
    assert matches["emergency"] is True
    assert matches["candidates"]
    # Ties break towards whoever can physically get there first.
    top_two = matches["candidates"][:2]
    if len(top_two) == 2 and top_two[0]["score_percent"] == top_two[1]["score_percent"]:
        assert top_two[0]["distance_km"] <= top_two[1]["distance_km"]

    client.patch(
        f"/api/bookings/{booking['id']}/status",
        headers=customer_headers,
        json={"status": "CANCELLED"},
    )
