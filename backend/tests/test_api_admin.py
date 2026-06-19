"""Integration tests for admin loan lifecycle and access control."""
import pytest
from tests.conftest import LOAN_PAYLOAD, accept_agreement, auth_headers, register, register_admin


def _apply_loan(client, token, payload=None):
    r = client.post("/loans", json=payload or LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 201
    return r.json()


# ── Access control ─────────────────────────────────────────────────────────────

def test_regular_user_cannot_access_admin_endpoints(client):
    token = register(client)
    r = client.get("/admin/loans", headers=auth_headers(token))
    assert r.status_code == 403


def test_unauthenticated_cannot_access_admin_endpoints(client):
    r = client.get("/admin/loans")
    assert r.status_code == 401


def test_admin_can_list_all_loans(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    _apply_loan(client, user_token)
    _apply_loan(client, user_token)

    r = client.get("/admin/loans", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert len(r.json()) >= 2


# ── Approve / reject ───────────────────────────────────────────────────────────

def test_admin_approve_pending_loan(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    # Force pending: mid-CIBIL, high DTI
    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    loan = _apply_loan(client, user_token, payload)
    assert loan["status"] == "pending"

    r = client.patch(f"/admin/loans/{loan['id']}/approve", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_approve_generates_repayment_schedule(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    loan = _apply_loan(client, user_token, payload)

    client.patch(f"/admin/loans/{loan['id']}/approve", headers=auth_headers(admin_token))

    r = client.get(f"/admin/loans/{loan['id']}/repayments", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == loan["tenure_months"]


def test_admin_reject_pending_loan(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    loan = _apply_loan(client, user_token, payload)

    r = client.patch(
        f"/admin/loans/{loan['id']}/reject",
        json={"reason": "Insufficient income documentation"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Insufficient income documentation"


def test_cannot_approve_already_approved_loan(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)  # auto-approved (CIBIL 780)
    assert loan["status"] == "approved"

    r = client.patch(f"/admin/loans/{loan['id']}/approve", headers=auth_headers(admin_token))
    assert r.status_code == 409


def test_cannot_reject_already_approved_loan(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)
    r = client.patch(
        f"/admin/loans/{loan['id']}/reject",
        json={"reason": "Changed mind"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 409


# ── Disburse ───────────────────────────────────────────────────────────────────

def test_admin_disburse_approved_loan(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)
    accept_agreement(client, user_token, loan["id"])
    r = client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR123456789"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["gross_amount"] == 100000.0
    assert data["net_amount"] == 98500.0   # 100000 - 1500 processing fee
    assert "XXXXXX" in data["bank_account_number"]  # masked


def test_loan_status_becomes_disbursed_after_disbursal(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)
    accept_agreement(client, user_token, loan["id"])
    client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR123456789"},
        headers=auth_headers(admin_token),
    )
    r = client.get(f"/admin/loans/{loan['id']}", headers=auth_headers(admin_token))
    assert r.json()["status"] == "disbursed"


def test_cannot_disburse_twice(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)
    accept_agreement(client, user_token, loan["id"])
    client.post(f"/admin/loans/{loan['id']}/disburse", json={"reference_number": "UTR1"}, headers=auth_headers(admin_token))
    r = client.post(f"/admin/loans/{loan['id']}/disburse", json={"reference_number": "UTR2"}, headers=auth_headers(admin_token))
    assert r.status_code == 409


def test_cannot_disburse_pending_loan(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    loan = _apply_loan(client, user_token, payload)
    assert loan["status"] == "pending"

    r = client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR1"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 400


# ── Repayment ──────────────────────────────────────────────────────────────────

def test_admin_mark_installment_paid(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)
    installments = client.get(f"/admin/loans/{loan['id']}/repayments", headers=auth_headers(admin_token)).json()
    first = installments[0]

    r = client.patch(
        f"/admin/loans/{loan['id']}/repayments/{first['id']}/pay",
        json={},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"
    assert r.json()["paid_amount"] == first["emi_amount"]


def test_cannot_mark_installment_paid_twice(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = _apply_loan(client, user_token)
    installments = client.get(f"/admin/loans/{loan['id']}/repayments", headers=auth_headers(admin_token)).json()
    first_id = installments[0]["id"]

    client.patch(f"/admin/loans/{loan['id']}/repayments/{first_id}/pay", json={}, headers=auth_headers(admin_token))
    r = client.patch(f"/admin/loans/{loan['id']}/repayments/{first_id}/pay", json={}, headers=auth_headers(admin_token))
    assert r.status_code == 409


# ── Filter / search ────────────────────────────────────────────────────────────

def test_admin_filter_by_status(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    _apply_loan(client, user_token)  # approved
    payload = {**LOAN_PAYLOAD, "cibil_score": 600}
    _apply_loan(client, user_token, payload)  # rejected

    approved = client.get("/admin/loans?status=approved", headers=auth_headers(admin_token)).json()
    rejected = client.get("/admin/loans?status=rejected", headers=auth_headers(admin_token)).json()
    assert all(l["status"] == "approved" for l in approved)
    assert all(l["status"] == "rejected" for l in rejected)


def test_admin_search_by_email(client):
    user_token = register(client, email="findme@test.com", phone="+919000000011")
    admin_token = register_admin(client)
    _apply_loan(client, user_token)

    r = client.get("/admin/loans?identifier=findme@test.com", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["user_email"] == "findme@test.com"


def test_admin_search_by_phone(client):
    user_token = register(client, email="findme@test.com", phone="+919000000011")
    admin_token = register_admin(client)
    _apply_loan(client, user_token)

    r = client.get("/admin/loans", params={"identifier": "+919000000011"}, headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 1
