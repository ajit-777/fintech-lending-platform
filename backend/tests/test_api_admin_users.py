"""Tests for admin user management endpoints."""
from tests.conftest import auth_headers, register_admin

_counter = 0


def _admin(client):
    global _counter
    _counter += 1
    return register_admin(client, email=f"adm{_counter}@mgmt.com", phone=f"+9198{_counter:08d}")


def _support_payload(n):
    return {"email": f"support{n}@test.com", "phone": f"+9197{n:08d}", "password": "Support@1234", "role": "superuser"}


def test_list_staff_requires_admin(client):
    from tests.conftest import register
    token = register(client, email="borrower_x@test.com", phone="+919300000001")
    r = client.get("/admin/users", headers=auth_headers(token))
    assert r.status_code == 403


def test_create_and_list_staff_user(client):
    token = _admin(client)
    payload = _support_payload(1)
    r = client.post("/admin/users", json=payload, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["role"] == "superuser"
    assert data["email"] == payload["email"]

    users = client.get("/admin/users", headers=auth_headers(token)).json()
    emails = [u["email"] for u in users]
    assert payload["email"] in emails


def test_create_duplicate_email_rejected(client):
    token = _admin(client)
    payload = _support_payload(2)
    client.post("/admin/users", json=payload, headers=auth_headers(token))
    r = client.post("/admin/users", json=payload, headers=auth_headers(token))
    assert r.status_code == 409


def test_change_role(client):
    token = _admin(client)
    payload = _support_payload(3)
    user_id = client.post("/admin/users", json=payload, headers=auth_headers(token)).json()["id"]

    r = client.patch(f"/admin/users/{user_id}/role", json={"role": "admin"}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["role"] == "admin"

    r = client.patch(f"/admin/users/{user_id}/role", json={"role": "superuser"}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["role"] == "superuser"


def test_delete_staff_user(client):
    token = _admin(client)
    payload = _support_payload(4)
    user_id = client.post("/admin/users", json=payload, headers=auth_headers(token)).json()["id"]

    r = client.delete(f"/admin/users/{user_id}", headers=auth_headers(token))
    assert r.status_code == 204

    users = client.get("/admin/users", headers=auth_headers(token)).json()
    assert all(u["id"] != user_id for u in users)


def test_superuser_can_read_loans(client):
    from tests.conftest import register, LOAN_PAYLOAD
    # Create a loan as a borrower
    borrower_token = register(client, email="borrow_su@test.com", phone="+919400000001")
    loan_id = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(borrower_token)).json()["id"]

    # Create superuser and verify they can read the loan
    admin_token = _admin(client)
    payload = _support_payload(5)
    client.post("/admin/users", json=payload, headers=auth_headers(admin_token))
    su_r = client.post("/auth/login", json={"identifier": payload["email"], "password": payload["password"]})
    su_token = su_r.json()["access_token"]

    r = client.get(f"/admin/loans/{loan_id}", headers=auth_headers(su_token))
    assert r.status_code == 200

    r = client.get("/admin/loans", headers=auth_headers(su_token))
    assert r.status_code == 200


def test_superuser_cannot_approve_loans(client):
    from tests.conftest import register, LOAN_PAYLOAD
    borrower_token = register(client, email="borrow_su2@test.com", phone="+919400000002")
    loan_id = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(borrower_token)).json()["id"]

    admin_token = _admin(client)
    payload = _support_payload(6)
    client.post("/admin/users", json=payload, headers=auth_headers(admin_token))
    su_r = client.post("/auth/login", json={"identifier": payload["email"], "password": payload["password"]})
    su_token = su_r.json()["access_token"]

    r = client.patch(f"/admin/loans/{loan_id}/approve", headers=auth_headers(su_token))
    assert r.status_code == 403


def test_superuser_cannot_manage_staff(client):
    admin_token = _admin(client)
    payload = _support_payload(7)
    client.post("/admin/users", json=payload, headers=auth_headers(admin_token))
    su_r = client.post("/auth/login", json={"identifier": payload["email"], "password": payload["password"]})
    su_token = su_r.json()["access_token"]

    r = client.get("/admin/users", headers=auth_headers(su_token))
    assert r.status_code == 403
