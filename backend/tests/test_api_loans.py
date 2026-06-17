"""Integration tests for the borrower loan lifecycle."""
from tests.conftest import LOAN_PAYLOAD, auth_headers, register


def test_apply_loan_auto_approved(client):
    token = register(client)
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "approved"
    assert data["annual_interest_rate"] == 10.0   # Prime tier
    assert data["processing_fee"] == 1500.0        # 1.5% of 100000


def test_apply_loan_auto_rejected_low_cibil(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "cibil_score": 600}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] is not None


def test_apply_loan_pending_edge_case(client):
    token = register(client)
    # CIBIL in 650-750 range with high DTI → pending
    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


def test_repayment_schedule_generated_on_approval(client):
    token = register(client)
    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()
    assert loan["status"] == "approved"

    r = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token))
    assert r.status_code == 200
    installments = r.json()
    assert len(installments) == 12
    assert installments[0]["installment_number"] == 1
    assert installments[0]["status"] == "pending"


def test_repayment_schedule_not_available_for_rejected(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "cibil_score": 600}
    loan = client.post("/loans", json=payload, headers=auth_headers(token)).json()
    r = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token))
    assert r.status_code == 400


def test_list_loans_returns_only_own(client):
    token1 = register(client, email="a@test.com", phone="+919000000011")
    token2 = register(client, email="b@test.com", phone="+919000000022")

    client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token1))
    client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token1))
    client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token2))

    r1 = client.get("/loans", headers=auth_headers(token1)).json()
    r2 = client.get("/loans", headers=auth_headers(token2)).json()
    assert len(r1) == 2
    assert len(r2) == 1


def test_get_single_loan(client):
    token = register(client)
    loan_id = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()["id"]
    r = client.get(f"/loans/{loan_id}", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["id"] == loan_id


def test_cannot_view_another_users_loan(client):
    token1 = register(client, email="a@test.com", phone="+919000000011")
    token2 = register(client, email="b@test.com", phone="+919000000022")
    loan_id = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token1)).json()["id"]
    r = client.get(f"/loans/{loan_id}", headers=auth_headers(token2))
    assert r.status_code == 404


def test_apply_loan_invalid_ifsc(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "ifsc_code": "INVALID"}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 422
