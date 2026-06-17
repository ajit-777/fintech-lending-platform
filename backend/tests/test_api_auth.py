"""Integration tests for /auth/register and /auth/login."""
from tests.conftest import auth_headers, register


def test_register_success(client):
    r = client.post("/auth/register", json={
        "email": "new@test.com", "phone": "+919111111111", "password": "Test@1234",
    })
    assert r.status_code == 201
    assert "access_token" in r.json()
    assert r.json()["is_admin"] is False


def test_register_duplicate_email(client):
    register(client)
    r = client.post("/auth/register", json={
        "email": "user@test.com", "phone": "+919222222222", "password": "Test@1234",
    })
    assert r.status_code == 409


def test_register_duplicate_phone(client):
    register(client)
    r = client.post("/auth/register", json={
        "email": "other@test.com", "phone": "+919000000001", "password": "Test@1234",
    })
    assert r.status_code == 409


def test_register_weak_password(client):
    r = client.post("/auth/register", json={
        "email": "weak@test.com", "phone": "+919333333333", "password": "password",
    })
    assert r.status_code == 422


def test_login_with_email(client):
    register(client)
    r = client.post("/auth/login", json={"identifier": "user@test.com", "password": "Test@1234"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_with_phone(client):
    register(client)
    r = client.post("/auth/login", json={"identifier": "+919000000001", "password": "Test@1234"})
    assert r.status_code == 200


def test_login_wrong_password(client):
    register(client)
    r = client.post("/auth/login", json={"identifier": "user@test.com", "password": "Wrong@1234"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", json={"identifier": "ghost@test.com", "password": "Test@1234"})
    assert r.status_code == 401


def test_account_lockout_after_five_failures(client):
    register(client)
    for _ in range(5):
        client.post("/auth/login", json={"identifier": "user@test.com", "password": "Wrong@1234"})
    r = client.post("/auth/login", json={"identifier": "user@test.com", "password": "Test@1234"})
    assert r.status_code == 423
    assert "locked" in r.json()["detail"].lower()


def test_protected_endpoint_requires_token(client):
    r = client.get("/loans")
    assert r.status_code == 401


def test_protected_endpoint_with_valid_token(client):
    token = register(client)
    r = client.get("/loans", headers=auth_headers(token))
    assert r.status_code == 200
