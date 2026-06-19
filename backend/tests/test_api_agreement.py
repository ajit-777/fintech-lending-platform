"""Integration tests for loan agreement PDF download and OTP-based acceptance."""
from tests.conftest import LOAN_PAYLOAD, accept_agreement, auth_headers, register, register_admin


def _apply_approved(client, user_token):
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(user_token))
    assert r.status_code == 201
    loan = r.json()
    assert loan["status"] == "approved"
    return loan


# ── PDF download ───────────────────────────────────────────────────────────────

def test_download_agreement_pdf_returns_pdf(client):
    token = register(client)
    loan = _apply_approved(client, token)
    r = client.get(f"/loans/{loan['id']}/agreement", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 1000  # non-trivial PDF
    assert r.content[:4] == b"%PDF"


def test_agreement_pdf_unavailable_for_pending_loan(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    loan = r.json()
    assert loan["status"] == "pending"

    r = client.get(f"/loans/{loan['id']}/agreement", headers=auth_headers(token))
    assert r.status_code == 400


def test_agreement_pdf_unavailable_for_rejected_loan(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "cibil_score": 600}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    loan = r.json()
    assert loan["status"] == "rejected"

    r = client.get(f"/loans/{loan['id']}/agreement", headers=auth_headers(token))
    assert r.status_code == 400


# ── OTP acceptance flow ────────────────────────────────────────────────────────

def test_send_otp_returns_ref_id(client):
    token = register(client)
    loan = _apply_approved(client, token)
    r = client.post(f"/loans/{loan['id']}/agreement/send-otp", headers=auth_headers(token))
    assert r.status_code == 200
    assert "ref_id" in r.json()
    assert "_dev_otp" in r.json()


def test_accept_agreement_with_valid_otp(client):
    token = register(client)
    loan = _apply_approved(client, token)
    r = client.post(f"/loans/{loan['id']}/agreement/send-otp", headers=auth_headers(token))
    ref_id = r.json()["ref_id"]

    r = client.post(
        f"/loans/{loan['id']}/agreement/accept",
        json={"otp": "123456", "ref_id": ref_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    assert "accepted_at" in r.json()


def test_accept_agreement_reflected_in_loan(client):
    token = register(client)
    loan = _apply_approved(client, token)
    accept_agreement(client, token, loan["id"])

    r = client.get(f"/loans/{loan['id']}", headers=auth_headers(token))
    assert r.json()["agreement_accepted"] is True
    assert r.json()["agreement_accepted_at"] is not None


def test_wrong_otp_rejected(client):
    token = register(client)
    loan = _apply_approved(client, token)
    r = client.post(f"/loans/{loan['id']}/agreement/send-otp", headers=auth_headers(token))
    ref_id = r.json()["ref_id"]

    r = client.post(
        f"/loans/{loan['id']}/agreement/accept",
        json={"otp": "000000", "ref_id": ref_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_wrong_ref_id_rejected(client):
    token = register(client)
    loan = _apply_approved(client, token)
    client.post(f"/loans/{loan['id']}/agreement/send-otp", headers=auth_headers(token))

    r = client.post(
        f"/loans/{loan['id']}/agreement/accept",
        json={"otp": "123456", "ref_id": "wrong-ref"},
        headers=auth_headers(token),
    )
    assert r.status_code == 400


def test_cannot_accept_without_sending_otp_first(client):
    token = register(client)
    loan = _apply_approved(client, token)
    r = client.post(
        f"/loans/{loan['id']}/agreement/accept",
        json={"otp": "123456", "ref_id": "some-ref"},
        headers=auth_headers(token),
    )
    assert r.status_code == 400


def test_cannot_accept_agreement_twice(client):
    token = register(client)
    loan = _apply_approved(client, token)
    accept_agreement(client, token, loan["id"])

    # Second send-otp should fail
    r = client.post(f"/loans/{loan['id']}/agreement/send-otp", headers=auth_headers(token))
    assert r.status_code == 409


# ── Disbursal gate ─────────────────────────────────────────────────────────────

def test_disbursal_blocked_without_agreement(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(user_token)).json()
    r = client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR1"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 400
    assert "agreement" in r.json()["detail"].lower()


def test_disbursal_succeeds_after_agreement_accepted(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(user_token)).json()
    accept_agreement(client, user_token, loan["id"])

    r = client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR1"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201
