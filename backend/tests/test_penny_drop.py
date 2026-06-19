"""Tests for penny drop verification and name matching."""
import pytest
from tests.conftest import LOAN_PAYLOAD, accept_agreement, auth_headers, register, register_admin

from app.services.penny_drop import MockPennyDropProvider, name_match_score


# ── Unit tests: name matching ──────────────────────────────────────────────────

def test_exact_name_match():
    assert name_match_score("AJIT BANTIA", "AJIT BANTIA") == 1.0


def test_partial_name_match_above_threshold():
    score = name_match_score("AJIT KUMAR BANTIA", "AJIT BANTIA")
    assert score >= 0.5


def test_completely_different_names():
    score = name_match_score("AJIT BANTIA", "DIFFERENT NAME")
    assert score == 0.0


def test_single_token_match():
    score = name_match_score("AJIT BANTIA", "AJIT SHARMA")
    assert 0.0 < score < 1.0


def test_empty_name_returns_zero():
    assert name_match_score("", "AJIT BANTIA") == 0.0
    assert name_match_score("AJIT BANTIA", "") == 0.0


# ── Unit tests: mock provider ──────────────────────────────────────────────────

def test_mock_provider_success():
    p = MockPennyDropProvider()
    result = p.verify("1234567890", "SBIN0001234")
    assert result.success is True
    assert result.account_holder_name == "MOCK ACCOUNT HOLDER"
    assert result.account_active is True


def test_mock_provider_inactive_account():
    p = MockPennyDropProvider()
    result = p.verify("0000000000", "SBIN0001234")
    assert result.success is False
    assert result.account_active is False


def test_mock_provider_name_mismatch():
    p = MockPennyDropProvider()
    result = p.verify("9000000001", "SBIN0001234")
    assert result.success is True
    assert result.account_holder_name == "DIFFERENT NAME"


# ── Integration tests ──────────────────────────────────────────────────────────

def test_loan_application_stores_penny_drop_result(client):
    token = register(client)
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["bank_account_verified"] is True
    assert data["bank_account_holder_name"] == "MOCK ACCOUNT HOLDER"
    assert data["penny_drop_name_match_score"] is not None
    assert data["penny_drop_name_match_score"] >= 0.5


def test_inactive_account_blocks_loan_application(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "bank_account_number": "0123456789"}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 422
    assert "verification failed" in r.json()["detail"].lower()


def test_name_mismatch_marks_unverified(client):
    """Account starting with 9 returns 'DIFFERENT NAME' → score 0 → unverified."""
    token = register(client)
    payload = {**LOAN_PAYLOAD, "bank_account_number": "9123456789"}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["bank_account_verified"] is False
    assert data["bank_account_holder_name"] == "DIFFERENT NAME"


def test_disbursal_blocked_if_penny_drop_failed(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    # Apply with mismatched name account
    payload = {**LOAN_PAYLOAD, "bank_account_number": "9123456789"}
    loan = client.post("/loans", json=payload, headers=auth_headers(user_token)).json()
    assert loan["bank_account_verified"] is False

    # Try to disburse — should be blocked
    r = client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR123"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 400
    assert "penny drop" in r.json()["detail"].lower()


def test_admin_override_unblocks_disbursal(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    payload = {**LOAN_PAYLOAD, "bank_account_number": "9123456789"}
    loan = client.post("/loans", json=payload, headers=auth_headers(user_token)).json()
    assert loan["bank_account_verified"] is False

    # Admin overrides bank account
    r = client.patch(f"/admin/loans/{loan['id']}/bank-account/override", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["bank_account_override"] is True

    # Borrower accepts agreement
    accept_agreement(client, user_token, loan["id"])

    # Now disbursal should succeed
    r = client.post(
        f"/admin/loans/{loan['id']}/disburse",
        json={"reference_number": "UTR123"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201


def test_admin_can_see_penny_drop_fields(client):
    user_token = register(client, email="u@test.com", phone="+919000000011")
    admin_token = register_admin(client)

    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(user_token)).json()
    r = client.get(f"/admin/loans/{loan['id']}", headers=auth_headers(admin_token))
    data = r.json()
    assert data["bank_account_verified"] is True
    assert data["bank_account_holder_name"] == "MOCK ACCOUNT HOLDER"
