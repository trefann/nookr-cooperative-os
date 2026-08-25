"""Booking rules: state machine, permissions, validation and duplicates."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _new_booking(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/bookings",
        headers=headers,
        json={"raw_request": "The bathroom tap is dripping constantly."},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_booking_needs_a_description_or_a_service(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    response = client.post("/api/bookings", headers=customer_headers, json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_explicit_service_overrides_the_model(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    services = client.get("/api/services").json()
    carpentry = next(s for s in services if s["slug"] == "carpentry")
    booking = client.post(
        "/api/bookings",
        headers=customer_headers,
        json={
            "raw_request": "My kitchen sink is leaking.",
            "service_id": carpentry["id"],
        },
    ).json()
    # The customer's correction wins over the inferred service.
    assert booking["service_slug"] == "carpentry"
    # ...but what the model thought is still recorded, for transparency.
    assert booking["ai_interpretation"]["service_slug"] == "plumbing"

    client.patch(
        f"/api/bookings/{booking['id']}/status",
        headers=customer_headers,
        json={"status": "CANCELLED"},
    )


def test_unknown_service_is_a_404(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/bookings",
        headers=customer_headers,
        json={"raw_request": "Something is broken", "service_id": 999_999},
    )
    assert response.status_code == 404


def test_workers_cannot_raise_requests(
    client: TestClient, worker_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/bookings", headers=worker_headers, json={"raw_request": "Tap leaking"}
    )
    assert response.status_code == 403


def test_illegal_transitions_are_rejected_with_guidance(
    client: TestClient,
    customer_headers: dict[str, str],
    worker_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    booking = _new_booking(client, customer_headers)
    booking_id = booking["id"]

    # A worker who is not allocated the job is refused on permission grounds,
    # which is checked before the state machine.
    assert (
        client.patch(
            f"/api/bookings/{booking_id}/status",
            headers=worker_headers,
            json={"status": "IN_PROGRESS"},
        ).status_code
        == 403
    )

    # An administrator may make the transition, so this reaches the state
    # machine: a brand new, unallocated job still cannot be started.
    response = client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=admin_headers,
        json={"status": "IN_PROGRESS"},
    )
    assert response.status_code == 409
    message = response.json()["error"]["message"]
    assert "cannot become" in message
    assert "Allowed next" in message

    # Payment before the work is done is refused.
    unpaid = client.post(
        "/api/payments", headers=customer_headers, json={"booking_id": booking_id}
    )
    assert unpaid.status_code == 409

    # Rating before payment is refused.
    unrated = client.post(
        "/api/ratings",
        headers=customer_headers,
        json={"booking_id": booking_id, "stars": 5},
    )
    assert unrated.status_code == 409

    client.patch(
        f"/api/bookings/{booking_id}/status",
        headers=customer_headers,
        json={"status": "CANCELLED"},
    )


def test_status_endpoint_refuses_paid_and_rated(
    client: TestClient, customer_headers: dict[str, str], worker_headers: dict[str, str]
) -> None:
    booking = _new_booking(client, customer_headers)
    for target in ("PAID", "RATED", "ASSIGNED"):
        response = client.patch(
            f"/api/bookings/{booking['id']}/status",
            headers=worker_headers,
            json={"status": target},
        )
        assert response.status_code == 422, target

    client.patch(
        f"/api/bookings/{booking['id']}/status",
        headers=customer_headers,
        json={"status": "CANCELLED"},
    )


def test_double_payment_and_double_rating_are_blocked(
    client: TestClient, customer_headers: dict[str, str], worker_headers: dict[str, str]
) -> None:
    booking = _new_booking(client, customer_headers)
    booking_id = booking["id"]

    matches = client.post(
        "/api/matching", headers=customer_headers, json={"booking_id": booking_id}
    ).json()
    kumar = next(c for c in matches["candidates"] if c["worker_name"] == "Kumar Selvan")
    client.post(
        "/api/matching/assign",
        headers=customer_headers,
        json={"booking_id": booking_id, "worker_id": kumar["worker_id"]},
    )
    for target in ("ACCEPTED", "IN_PROGRESS", "COMPLETED"):
        assert (
            client.patch(
                f"/api/bookings/{booking_id}/status",
                headers=worker_headers,
                json={"status": target},
            ).status_code
            == 200
        )

    first = client.post(
        "/api/payments", headers=customer_headers, json={"booking_id": booking_id}
    )
    assert first.status_code == 201
    second = client.post(
        "/api/payments", headers=customer_headers, json={"booking_id": booking_id}
    )
    assert second.status_code == 409
    assert "already been paid" in second.json()["error"]["message"]

    rated = client.post(
        "/api/ratings",
        headers=customer_headers,
        json={"booking_id": booking_id, "stars": 4, "comment": "Good"},
    )
    assert rated.status_code == 201
    again = client.post(
        "/api/ratings",
        headers=customer_headers,
        json={"booking_id": booking_id, "stars": 5},
    )
    assert again.status_code == 409


def test_rating_bounds_are_enforced(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    for stars in (0, 6, -1):
        response = client.post(
            "/api/ratings",
            headers=customer_headers,
            json={"booking_id": 1, "stars": stars},
        )
        assert response.status_code == 422


def test_customers_cannot_read_other_customers_bookings(
    client: TestClient, customer_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    all_bookings = client.get("/api/bookings?limit=200", headers=admin_headers).json()
    mine = client.get("/api/bookings?limit=200", headers=customer_headers).json()
    my_ids = {b["id"] for b in mine}
    other = next(b for b in all_bookings if b["id"] not in my_ids)

    response = client.get(f"/api/bookings/{other['id']}", headers=customer_headers)
    assert response.status_code == 403


def test_missing_booking_is_a_404(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    assert client.get("/api/bookings/999999", headers=customer_headers).status_code == 404
    assert (
        client.get("/api/workers/999999", headers=customer_headers).status_code == 404
    )


def test_assigning_an_ineligible_worker_is_refused(
    client: TestClient, customer_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    booking = _new_booking(client, customer_headers)
    workers = client.get("/api/workers?limit=200", headers=admin_headers).json()
    gardener = next(w for w in workers if w["service_name"] == "Gardening")

    response = client.post(
        "/api/matching/assign",
        headers=customer_headers,
        json={"booking_id": booking["id"], "worker_id": gardener["id"]},
    )
    assert response.status_code == 409
    assert "cannot take this job" in response.json()["error"]["message"]

    client.patch(
        f"/api/bookings/{booking['id']}/status",
        headers=customer_headers,
        json={"status": "CANCELLED"},
    )


def test_worker_can_toggle_availability(
    client: TestClient, worker_headers: dict[str, str]
) -> None:
    original = client.get("/api/workers/me", headers=worker_headers).json()[
        "availability_status"
    ]
    updated = client.patch(
        "/api/workers/me/availability",
        headers=worker_headers,
        json={"availability_status": "OFF_DUTY"},
    )
    assert updated.status_code == 200
    assert updated.json()["availability_status"] == "OFF_DUTY"

    restored = client.patch(
        "/api/workers/me/availability",
        headers=worker_headers,
        json={"availability_status": original},
    )
    assert restored.json()["availability_status"] == original


def test_worker_summary_has_everything_the_portal_needs(
    client: TestClient, worker_headers: dict[str, str]
) -> None:
    body = client.get("/api/workers/me/summary", headers=worker_headers).json()
    assert body["profile"]["name"] == "Kumar Selvan"
    assert body["profile"]["skills"]
    assert body["profile"]["certifications"]
    assert body["workload"]["weekly_capacity"] > 0
    assert body["earnings"]["total"] > 0
    assert body["welfare"]["total_contribution"] > 0
    assert "entries" in body["welfare"]


def test_customer_summary_is_complete(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    body = client.get("/api/customer/summary", headers=customer_headers).json()
    assert body["customer"]["name"] == "Priya Sharma"
    assert "counts" in body and "spend" in body and "ratings" in body
    assert isinstance(body["payments"], list)


def test_demo_state_and_scenario_reset(client: TestClient) -> None:
    state = client.get("/api/demo/state").json()
    assert state["seeded"] is True
    assert len(state["steps"]) == 10
    assert "kitchen sink" in state["scenario_request"].lower()

    started = client.post("/api/demo/scenario/start").json()
    assert started["ready"] is True
    assert started["customer"]["name"] == "Priya Sharma"
