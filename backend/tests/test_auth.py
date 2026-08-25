"""Authentication and authorisation."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_health_reports_configuration(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True
    assert body["ai"]["service_understanding"] == "rule_based"


def test_demo_accounts_are_listed(client: TestClient) -> None:
    accounts = client.get("/api/auth/demo-accounts").json()
    emails = {account["email"] for account in accounts}
    assert emails == {"customer@demo.com", "worker@demo.com", "admin@demo.com"}


def test_demo_login_returns_a_usable_token(client: TestClient) -> None:
    body = client.post("/api/auth/demo-login", json={"role": "WORKER"}).json()
    assert body["user"]["email"] == "worker@demo.com"
    assert body["user"]["worker_id"] is not None

    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["role"] == "WORKER"


def test_password_login_works_and_bad_password_is_rejected(client: TestClient) -> None:
    good = client.post(
        "/api/auth/login", json={"email": "customer@demo.com", "password": "demo1234"}
    )
    assert good.status_code == 200

    bad = client.post(
        "/api/auth/login", json={"email": "customer@demo.com", "password": "wrong"}
    )
    assert bad.status_code == 401
    # The same message for unknown email and wrong password.
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert unknown.status_code == 401
    assert bad.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_registration_creates_a_customer(client: TestClient) -> None:
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "a-strong-password",
            "full_name": "Test Person",
            "role": "CUSTOMER",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["user"]["email"] == email

    duplicate = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "a-strong-password",
            "full_name": "Test Person",
        },
    )
    assert duplicate.status_code == 409


def test_registration_rejects_self_service_admin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"admin-{uuid.uuid4().hex[:6]}@example.com",
            "password": "a-strong-password",
            "full_name": "Would Be Admin",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_short_password_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "shorty@example.com", "password": "abc", "full_name": "Short Pass"},
    )
    assert response.status_code == 422


def test_protected_routes_require_a_token(client: TestClient) -> None:
    assert client.get("/api/workers").status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    assert (
        client.get("/api/workers", headers={"Authorization": "Bearer nonsense"}).status_code
        == 401
    )


def test_dashboard_is_admin_only(
    client: TestClient, customer_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    assert client.get("/api/dashboard", headers=customer_headers).status_code == 403
    assert client.get("/api/dashboard", headers=admin_headers).status_code == 200


def test_customers_cannot_read_welfare_or_analytics(
    client: TestClient, customer_headers: dict[str, str]
) -> None:
    assert client.get("/api/welfare", headers=customer_headers).status_code == 403
    assert client.get("/api/analytics", headers=customer_headers).status_code == 403
