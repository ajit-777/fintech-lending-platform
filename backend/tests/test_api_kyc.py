"""Integration tests for KYC submission, PAN/Aadhaar verification, and admin override."""
import pytest
from tests.conftest import auth_headers, register, register_admin

KYC_PAYLOAD = {
    "pan_number": "ABCDE1234F",
    "date_of_birth": "1990-06-15",
    "address_line1": "42 Marine Drive",
    "address_line2": "Flat 5B",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400001",
}


def _submit_kyc(client, token, payload=None):
    r = client.post("/kyc/submit", json=payload or KYC_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    return r.json()


# ── KYC submission ─────────────────────────────────────────────────────────────

def test_submit_kyc_returns_submitted_status(client):
    token = register(client, verified_kyc=False)
    profile = _submit_kyc(client, token)
    assert profile["kyc_status"] == "submitted"
    assert profile["pan_number"] == "ABCDE1234F"
    assert not profile["pan_verified"]


def test_get_my_kyc_before_submit_returns_404(client):
    token = register(client, verified_kyc=False)
    r = client.get("/kyc/me", headers=auth_headers(token))
    assert r.status_code == 404


def test_get_my_kyc_after_submit(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)
    r = client.get("/kyc/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["kyc_status"] == "submitted"


def test_invalid_pan_rejected(client):
    token = register(client, verified_kyc=False)
    bad = {**KYC_PAYLOAD, "pan_number": "INVALID"}
    r = client.post("/kyc/submit", json=bad, headers=auth_headers(token))
    assert r.status_code == 422


def test_underage_dob_rejected(client):
    token = register(client, verified_kyc=False)
    bad = {**KYC_PAYLOAD, "date_of_birth": "2015-01-01"}
    r = client.post("/kyc/submit", json=bad, headers=auth_headers(token))
    assert r.status_code == 422


def test_invalid_pincode_rejected(client):
    token = register(client, verified_kyc=False)
    bad = {**KYC_PAYLOAD, "pincode": "12345"}
    r = client.post("/kyc/submit", json=bad, headers=auth_headers(token))
    assert r.status_code == 422


def test_cannot_resubmit_after_verified(client):
    token = register(client)  # auto-verified KYC
    r = client.post("/kyc/submit", json=KYC_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 409


# ── PAN verification ───────────────────────────────────────────────────────────

def test_verify_pan_success(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)
    r = client.post("/kyc/verify-pan", headers=auth_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["pan_verified"] is True
    assert data["pan_name"] == "MOCK VERIFIED NAME"


def test_verify_pan_fails_for_invalid_pan(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token, {**KYC_PAYLOAD, "pan_number": "FABCD1234Z"})
    r = client.post("/kyc/verify-pan", headers=auth_headers(token))
    assert r.status_code == 422
    assert "PAN not found" in r.json()["detail"]


def test_verify_pan_without_submit_fails(client):
    token = register(client, verified_kyc=False)
    r = client.post("/kyc/verify-pan", headers=auth_headers(token))
    assert r.status_code == 400


def test_cannot_verify_pan_twice(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)
    client.post("/kyc/verify-pan", headers=auth_headers(token))
    r = client.post("/kyc/verify-pan", headers=auth_headers(token))
    assert r.status_code == 409


# ── Aadhaar OTP flow ───────────────────────────────────────────────────────────

def test_aadhaar_otp_flow_success(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)

    otp_r = client.post("/kyc/aadhaar/send-otp", json={"aadhaar_number": "123456781234"}, headers=auth_headers(token))
    assert otp_r.status_code == 200
    ref_id = otp_r.json()["ref_id"]

    confirm_r = client.post("/kyc/aadhaar/verify-otp", json={"otp": "123456", "ref_id": ref_id}, headers=auth_headers(token))
    assert confirm_r.status_code == 200
    assert confirm_r.json()["aadhaar_verified"] is True
    assert confirm_r.json()["aadhaar_last4"] == "1234"


def test_aadhaar_wrong_otp_fails(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)

    otp_r = client.post("/kyc/aadhaar/send-otp", json={"aadhaar_number": "123456781234"}, headers=auth_headers(token))
    ref_id = otp_r.json()["ref_id"]

    r = client.post("/kyc/aadhaar/verify-otp", json={"otp": "000000", "ref_id": ref_id}, headers=auth_headers(token))
    assert r.status_code == 422


def test_aadhaar_wrong_ref_id_fails(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)
    client.post("/kyc/aadhaar/send-otp", json={"aadhaar_number": "123456781234"}, headers=auth_headers(token))

    r = client.post("/kyc/aadhaar/verify-otp", json={"otp": "123456", "ref_id": "wrong-ref"}, headers=auth_headers(token))
    assert r.status_code == 400


def test_kyc_auto_verified_after_both_checks(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)

    client.post("/kyc/verify-pan", headers=auth_headers(token))

    otp_r = client.post("/kyc/aadhaar/send-otp", json={"aadhaar_number": "123456781234"}, headers=auth_headers(token))
    ref_id = otp_r.json()["ref_id"]
    confirm_r = client.post("/kyc/aadhaar/verify-otp", json={"otp": "123456", "ref_id": ref_id}, headers=auth_headers(token))

    assert confirm_r.json()["kyc_status"] == "verified"


# ── KYC gates loan application ─────────────────────────────────────────────────

def test_loan_blocked_without_kyc(client):
    token = register(client, verified_kyc=False)
    from tests.conftest import LOAN_PAYLOAD
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 403
    assert "KYC" in r.json()["detail"]


def test_loan_blocked_with_submitted_but_unverified_kyc(client):
    token = register(client, verified_kyc=False)
    _submit_kyc(client, token)
    from tests.conftest import LOAN_PAYLOAD
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 403


def test_loan_allowed_after_kyc_verified(client):
    token = register(client)  # verified_kyc=True by default
    from tests.conftest import LOAN_PAYLOAD
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 201


# ── Admin KYC endpoints ────────────────────────────────────────────────────────

def test_admin_can_view_user_kyc(client):
    user_token = register(client, email="u@test.com", phone="+919000000011", verified_kyc=False)
    admin_token = register_admin(client)
    _submit_kyc(client, user_token)

    r = client.get("/kyc/me", headers=auth_headers(user_token))
    user_kyc = r.json()
    user_id = user_kyc["user_id"]

    r = client.get(f"/admin/users/{user_id}/kyc", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["pan_number"] == "ABCDE1234F"


def test_admin_can_override_kyc_to_verified(client):
    user_token = register(client, email="u@test.com", phone="+919000000011", verified_kyc=False)
    admin_token = register_admin(client)
    _submit_kyc(client, user_token)

    r = client.get("/kyc/me", headers=auth_headers(user_token))
    user_id = r.json()["user_id"]

    r = client.patch(f"/admin/users/{user_id}/kyc/status", json={"kyc_status": "verified"}, headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["kyc_status"] == "verified"


def test_admin_can_reject_kyc(client):
    user_token = register(client, email="u@test.com", phone="+919000000011", verified_kyc=False)
    admin_token = register_admin(client)
    _submit_kyc(client, user_token)

    r = client.get("/kyc/me", headers=auth_headers(user_token))
    user_id = r.json()["user_id"]

    r = client.patch(
        f"/admin/users/{user_id}/kyc/status",
        json={"kyc_status": "rejected", "rejection_reason": "Document mismatch"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["kyc_status"] == "rejected"
    assert r.json()["rejection_reason"] == "Document mismatch"
